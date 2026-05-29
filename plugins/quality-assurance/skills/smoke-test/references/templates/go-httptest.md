# Template: Go net/http + testing + httptest

Use for Go services using the standard library `net/http`, or
third-party routers (Gin, Chi, Echo, Gorilla mux) that expose an
`http.Handler`. Runs in-process via `httptest.NewServer`, or against a
deployed URL when `SMOKE_BASE_URL` is set.

## File location

`smoke_test.go` next to the package being smoked, **or** a dedicated
`cmd/smoke/smoke_test.go`. The `_test.go` suffix means `go test` picks
it up automatically. Use the `// +build smoke` tag (or `//go:build
smoke`) if you want it gated separately from unit tests.

## Imports + body

```go
//go:build smoke
// +build smoke

// Package smoke — build-verification suite.
// Runtime budget: < 2 s in-process, < 30 s against a deployed URL.
//
// Run locally (in-process):    go test -tags smoke ./...
// Run against an environment:  SMOKE_BASE_URL=https://api.example.com \
//                              SMOKE_TOKEN=eyJ... go test -tags smoke ./...
package smoke_test

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strconv"
	"strings"
	"testing"
	"time"

	// TODO: update the import to the package that exposes your router.
	myapp "github.com/example/go-http-app"
)

var (
	baseURL = os.Getenv("SMOKE_BASE_URL")
	token   = stringOr(os.Getenv("SMOKE_TOKEN"), "smoke-token-placeholder") // TODO
)

func stringOr(v, fallback string) string {
	if v == "" {
		return fallback
	}
	return v
}

// runServer starts the app in-process (or returns the deployed URL).
func runServer(t *testing.T) (string, func()) {
	if baseURL != "" {
		return baseURL, func() {}
	}
	srv := httptest.NewServer(myapp.NewRouter()) // TODO: name of your router constructor
	return srv.URL, srv.Close
}

// do issues an HTTP request with the smoke timeout.
func do(t *testing.T, method, url string, body string, headers map[string]string) *http.Response {
	t.Helper()
	req, err := http.NewRequest(method, url, strings.NewReader(body))
	if err != nil {
		t.Fatalf("build request: %v", err)
	}
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, url, err)
	}
	return resp
}

func TestHealth(t *testing.T) {
	url, stop := runServer(t)
	defer stop()
	resp := do(t, "GET", url+"/health", "", nil)
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		t.Fatalf("/health = %d, want 200", resp.StatusCode)
	}
	var body map[string]string
	_ = json.NewDecoder(resp.Body).Decode(&body)
	if body["status"] != "ok" {
		t.Fatalf("/health body = %v", body)
	}
}

func TestGetKnownUser(t *testing.T) {
	url, stop := runServer(t)
	defer stop()
	resp := do(t, "GET", url+"/users/1", "", nil)
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		t.Fatalf("/users/1 = %d, want 200", resp.StatusCode)
	}
}

func TestMissingUserReturns404(t *testing.T) {
	url, stop := runServer(t)
	defer stop()
	resp := do(t, "GET", url+"/users/99999", "", nil)
	defer resp.Body.Close()
	if resp.StatusCode != 404 {
		t.Fatalf("/users/99999 = %d, want 404", resp.StatusCode)
	}
}

func TestCreateOrderRequiresAuth(t *testing.T) {
	url, stop := runServer(t)
	defer stop()
	resp := do(t, "POST", url+"/orders", `{"userId":1,"items":["a"]}`,
		map[string]string{"content-type": "application/json"})
	defer resp.Body.Close()
	if resp.StatusCode != 401 {
		t.Fatalf("unauth POST /orders = %d, want 401", resp.StatusCode)
	}
}

func TestCreateOrderHappyPath(t *testing.T) {
	url, stop := runServer(t)
	defer stop()
	body, _ := json.Marshal(map[string]any{"userId": 1, "items": []string{"smoke-item"}})
	resp := do(t, "POST", url+"/orders", string(body),
		map[string]string{
			"content-type":  "application/json",
			"authorization": "Bearer " + token,
		})
	defer resp.Body.Close()
	if resp.StatusCode != 200 && resp.StatusCode != 201 {
		t.Fatalf("POST /orders = %d, want 200/201", resp.StatusCode)
	}
	var b map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&b); err != nil {
		t.Fatalf("decode order: %v", err)
	}
	id, _ := b["id"].(float64)
	if id == 0 {
		t.Fatalf("no order id returned: %v", b)
	}
	// Round-trip
	resp2 := do(t, "GET", url+"/orders/"+strconv.Itoa(int(id)), "", nil)
	defer resp2.Body.Close()
	if resp2.StatusCode != 200 {
		t.Fatalf("GET /orders/%d = %d, want 200", int(id), resp2.StatusCode)
	}
}

var _ = bytes.NewReader // keep unused import quiet if you remove a test
```

## Notes

- The `//go:build smoke` tag means `go test ./...` skips smoke by
  default — pass `-tags smoke` to run it. Drop the tag if you'd rather
  have smoke run unconditionally.
- `httptest.NewServer` runs on a random local port — no conflicts with
  the dev server.
- For routers behind a constructor (`func NewRouter() http.Handler`),
  reuse the same constructor for unit + smoke. Avoid duplicating route
  registration in tests.
