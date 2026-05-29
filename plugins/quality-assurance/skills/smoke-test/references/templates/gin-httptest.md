# Template: Go + Gin + httptest

Use for Go services using `github.com/gin-gonic/gin`. Runs in-process
via Gin's `*gin.Engine` directly (no real socket via
`httptest.NewServer`), or against a deployed URL when `SMOKE_BASE_URL`
is set.

## File location

`smoke_test.go` in the same package as the router constructor, or
`cmd/smoke/smoke_test.go` if you prefer a dedicated package. The
`//go:build smoke` tag (below) keeps it out of the default `go test`
run.

## Body

```go
//go:build smoke
// +build smoke

// Package <yourpkg> — smoke tests (build-verification suite).
// Runtime budget: < 2 s in-process, < 30 s against a deployed URL.
//
// Run locally (in-process):    go test -tags smoke ./...
// Run against an environment:  SMOKE_BASE_URL=https://api.example.com \
//                              SMOKE_TOKEN=eyJ... go test -tags smoke ./...
package main // TODO: change if the router constructor lives in another package

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

	"github.com/gin-gonic/gin"
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

// engine returns the production router. TODO: replace NewRouter() with the
// real constructor name in your codebase.
func engine() *gin.Engine {
	gin.SetMode(gin.TestMode)
	return NewRouter()
}

func request(t *testing.T, method, path, body string, headers map[string]string) (int, []byte) {
	t.Helper()
	if baseURL != "" {
		req, err := http.NewRequest(method, baseURL+path, strings.NewReader(body))
		if err != nil {
			t.Fatalf("build request: %v", err)
		}
		for k, v := range headers {
			req.Header.Set(k, v)
		}
		client := &http.Client{Timeout: 5 * time.Second}
		resp, err := client.Do(req)
		if err != nil {
			t.Fatalf("%s %s: %v", method, path, err)
		}
		defer resp.Body.Close()
		buf := new(bytes.Buffer)
		_, _ = buf.ReadFrom(resp.Body)
		return resp.StatusCode, buf.Bytes()
	}
	w := httptest.NewRecorder()
	req, err := http.NewRequest(method, path, strings.NewReader(body))
	if err != nil {
		t.Fatalf("build request: %v", err)
	}
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	engine().ServeHTTP(w, req)
	return w.Code, w.Body.Bytes()
}

func TestHealth(t *testing.T) {
	code, body := request(t, "GET", "/health", "", nil)
	if code != 200 {
		t.Fatalf("/health = %d", code)
	}
	var b map[string]string
	_ = json.Unmarshal(body, &b)
	if b["status"] != "ok" {
		t.Fatalf("/health body = %v", b)
	}
}

func TestKnownRecord(t *testing.T) {
	// TODO: replace /users/1 with a known seeded id.
	code, _ := request(t, "GET", "/users/1", "", nil)
	if code != 200 {
		t.Fatalf("/users/1 = %d", code)
	}
}

func TestMissingReturns404(t *testing.T) {
	code, _ := request(t, "GET", "/users/999999", "", nil)
	if code != 404 {
		t.Fatalf("/users/missing = %d", code)
	}
}

func TestProtectedRouteRequiresAuth(t *testing.T) {
	code, _ := request(t, "POST", "/orders", `{"userId":1,"items":["a"]}`,
		map[string]string{"content-type": "application/json"})
	if code != 401 {
		t.Fatalf("unauth POST /orders = %d", code)
	}
}

func TestCreateOrderHappyPath(t *testing.T) {
	body, _ := json.Marshal(map[string]any{"userId": 1, "items": []string{"smoke"}})
	code, raw := request(t, "POST", "/orders", string(body),
		map[string]string{
			"content-type":  "application/json",
			"authorization": "Bearer " + token,
		})
	if code != 200 && code != 201 {
		t.Fatalf("POST /orders = %d", code)
	}
	var b map[string]any
	if err := json.Unmarshal(raw, &b); err != nil {
		t.Fatalf("decode body: %v", err)
	}
	id, _ := b["id"].(float64)
	if id == 0 {
		t.Fatalf("no order id: %v", b)
	}
	// Round-trip read.
	code2, _ := request(t, "GET", "/orders/"+strconv.Itoa(int(id)), "", nil)
	if code2 != 200 {
		t.Fatalf("GET /orders/%d = %d", int(id), code2)
	}
}
```

## Notes

- `gin.SetMode(gin.TestMode)` silences Gin's request logging — keeps
  test output clean.
- Calling `engine().ServeHTTP(w, req)` is the canonical Gin in-process
  pattern; faster than spinning up `httptest.NewServer` and exercises
  the full middleware chain.
- The `//go:build smoke` tag means smoke is opt-in via `-tags smoke`.
  Drop the tag if you want every `go test` run to include smoke.
- For Echo, swap `*gin.Engine` for `*echo.Echo` and use
  `echo.NewContext`. For Chi, the same `httptest.NewRecorder` pattern
  works against `chi.Router` directly.
