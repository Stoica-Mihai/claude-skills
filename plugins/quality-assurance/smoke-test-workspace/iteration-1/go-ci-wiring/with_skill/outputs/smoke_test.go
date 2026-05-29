//go:build smoke
// +build smoke

// Package main — smoke / build-verification suite.
//
// Purpose: prove the build is stable enough to bother regression-testing.
// NOT a regression suite — broad and shallow on purpose.
//
// Runtime budget: < 2 s in-process, < 30 s against a deployed URL.
// Suite size: 6 checks (cap at 10).
//
// Run locally (in-process httptest server):
//   go test -tags smoke -run TestSmoke -v ./...
//
// Run against a deployed environment:
//   SMOKE_BASE_URL=https://api.example.com \
//   SMOKE_TOKEN=eyJ... \
//   go test -tags smoke -run TestSmoke -v ./...
//
// On failure, the test logs method+URL+status+body so the on-call engineer
// has a diagnose-able artifact (not just "test 4 failed").
package main

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"strconv"
	"strings"
	"testing"
	"time"
)

var (
	smokeBaseURL = os.Getenv("SMOKE_BASE_URL")
	smokeToken   = stringOr(os.Getenv("SMOKE_TOKEN"), "smoke-token-placeholder") // TODO: real token for deployed runs
)

func stringOr(v, fallback string) string {
	if v == "" {
		return fallback
	}
	return v
}

// startSmokeServer either returns the deployed URL or boots an in-process
// httptest server backed by the real router.
func startSmokeServer(t *testing.T) (string, func()) {
	t.Helper()
	if smokeBaseURL != "" {
		return strings.TrimRight(smokeBaseURL, "/"), func() {}
	}
	srv := httptest.NewServer(newRouter())
	return srv.URL, srv.Close
}

// doSmoke issues an HTTP request with a tight smoke timeout and returns
// the response plus the already-read body so failure logs are useful.
func doSmoke(t *testing.T, method, url, body string, headers map[string]string) (*http.Response, []byte) {
	t.Helper()
	req, err := http.NewRequest(method, url, strings.NewReader(body))
	if err != nil {
		t.Fatalf("build request %s %s: %v", method, url, err)
	}
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("%s %s: transport error: %v", method, url, err)
	}
	raw, _ := io.ReadAll(resp.Body)
	_ = resp.Body.Close()
	return resp, raw
}

func failHTTP(t *testing.T, method, url string, resp *http.Response, raw []byte, want int) {
	t.Helper()
	t.Fatalf("%s %s = %d (want %d); body=%s", method, url, resp.StatusCode, want, string(raw))
}

// 1. Health endpoint returns 200 + {"status":"ok"}.
func TestSmoke_Health(t *testing.T) {
	base, stop := startSmokeServer(t)
	defer stop()
	resp, raw := doSmoke(t, "GET", base+"/health", "", nil)
	if resp.StatusCode != 200 {
		failHTTP(t, "GET", "/health", resp, raw, 200)
	}
	var body map[string]string
	if err := json.Unmarshal(raw, &body); err != nil {
		t.Fatalf("/health body not json: %v; raw=%s", err, string(raw))
	}
	if body["status"] != "ok" {
		t.Fatalf("/health status=%q want %q", body["status"], "ok")
	}
}

// 2. Primary read endpoint returns shape-correct data for a known fixture user.
func TestSmoke_GetKnownUser(t *testing.T) {
	base, stop := startSmokeServer(t)
	defer stop()
	resp, raw := doSmoke(t, "GET", base+"/users/1", "", nil)
	if resp.StatusCode != 200 {
		failHTTP(t, "GET", "/users/1", resp, raw, 200)
	}
	var u struct {
		ID   int    `json:"id"`
		Name string `json:"name"`
	}
	if err := json.Unmarshal(raw, &u); err != nil {
		t.Fatalf("/users/1 body not json: %v; raw=%s", err, string(raw))
	}
	if u.ID != 1 || u.Name == "" {
		t.Fatalf("/users/1 shape wrong: %+v", u)
	}
}

// 3. Missing resource returns 404 (negative path is part of smoke).
func TestSmoke_MissingUserReturns404(t *testing.T) {
	base, stop := startSmokeServer(t)
	defer stop()
	resp, raw := doSmoke(t, "GET", base+"/users/99999", "", nil)
	if resp.StatusCode != 404 {
		failHTTP(t, "GET", "/users/99999", resp, raw, 404)
	}
}

// 4. Auth-guarded write rejects unauthenticated callers (401).
func TestSmoke_CreateOrderRequiresAuth(t *testing.T) {
	base, stop := startSmokeServer(t)
	defer stop()
	resp, raw := doSmoke(t, "POST", base+"/orders",
		`{"userId":1,"items":["a"]}`,
		map[string]string{"content-type": "application/json"})
	if resp.StatusCode != 401 {
		failHTTP(t, "POST", "/orders (no auth)", resp, raw, 401)
	}
}

// 5. Happy-path create: authenticated POST /orders returns 201 + id.
//    Idempotent-safe: the test data is ephemeral and scoped to this run.
func TestSmoke_CreateOrderHappyPath(t *testing.T) {
	base, stop := startSmokeServer(t)
	defer stop()
	body, _ := json.Marshal(map[string]any{"userId": 1, "items": []string{"smoke-item"}})
	resp, raw := doSmoke(t, "POST", base+"/orders", string(body),
		map[string]string{
			"content-type":  "application/json",
			"authorization": "Bearer " + smokeToken,
		})
	if resp.StatusCode != 200 && resp.StatusCode != 201 {
		failHTTP(t, "POST", "/orders", resp, raw, 201)
	}
	var got struct {
		ID     int      `json:"id"`
		UserID int      `json:"userId"`
		Items  []string `json:"items"`
	}
	if err := json.Unmarshal(raw, &got); err != nil {
		t.Fatalf("POST /orders body not json: %v; raw=%s", err, string(raw))
	}
	if got.ID == 0 {
		t.Fatalf("POST /orders returned no id: %s", string(raw))
	}
	t.Setenv("SMOKE_LAST_ORDER_ID", strconv.Itoa(got.ID))

	// 6. Round-trip: the order we just created is readable by id.
	resp2, raw2 := doSmoke(t, "GET", base+"/orders/"+strconv.Itoa(got.ID), "", nil)
	if resp2.StatusCode != 200 {
		failHTTP(t, "GET", "/orders/{id}", resp2, raw2, 200)
	}
	var roundtrip struct {
		ID int `json:"id"`
	}
	if err := json.Unmarshal(raw2, &roundtrip); err != nil {
		t.Fatalf("GET /orders/%d body not json: %v; raw=%s", got.ID, err, string(raw2))
	}
	if roundtrip.ID != got.ID {
		t.Fatalf("round-trip id mismatch: got %d want %d", roundtrip.ID, got.ID)
	}
}
