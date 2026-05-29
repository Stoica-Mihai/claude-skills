package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func doReq(t *testing.T, h http.Handler, method, path string, body string, headers map[string]string) *httptest.ResponseRecorder {
	t.Helper()
	var r *http.Request
	if body == "" {
		r = httptest.NewRequest(method, path, nil)
	} else {
		r = httptest.NewRequest(method, path, bytes.NewBufferString(body))
	}
	for k, v := range headers {
		r.Header.Set(k, v)
	}
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}

func TestHealth(t *testing.T) {
	w := doReq(t, newRouter(), "GET", "/health", "", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("health: want 200, got %d", w.Code)
	}
	var got map[string]string
	if err := json.Unmarshal(w.Body.Bytes(), &got); err != nil {
		t.Fatalf("health body not json: %v", err)
	}
	if got["status"] != "ok" {
		t.Fatalf("health: want status=ok, got %v", got)
	}
	if ct := w.Header().Get("content-type"); !strings.HasPrefix(ct, "application/json") {
		t.Fatalf("health: want json content-type, got %q", ct)
	}
}

func TestGetUser_Found(t *testing.T) {
	w := doReq(t, newRouter(), "GET", "/users/1", "", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("users/1: want 200, got %d body=%s", w.Code, w.Body.String())
	}
	var u user
	if err := json.Unmarshal(w.Body.Bytes(), &u); err != nil {
		t.Fatalf("users/1 body not json: %v", err)
	}
	if u.ID != 1 || u.Name != "alice" {
		t.Fatalf("users/1: want {1,alice}, got %+v", u)
	}
}

func TestGetUser_NotFound(t *testing.T) {
	w := doReq(t, newRouter(), "GET", "/users/9999", "", nil)
	if w.Code != http.StatusNotFound {
		t.Fatalf("users/9999: want 404, got %d", w.Code)
	}
}

func TestGetUser_BadID(t *testing.T) {
	w := doReq(t, newRouter(), "GET", "/users/notanint", "", nil)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("users/notanint: want 400, got %d", w.Code)
	}
}

func TestPostOrder_MissingAuth(t *testing.T) {
	body := `{"userId":1,"items":["a"]}`
	w := doReq(t, newRouter(), "POST", "/orders", body, map[string]string{"content-type": "application/json"})
	if w.Code != http.StatusUnauthorized {
		t.Fatalf("orders no auth: want 401, got %d", w.Code)
	}
}

func TestPostOrder_BadJSON(t *testing.T) {
	w := doReq(t, newRouter(), "POST", "/orders", "{not json", map[string]string{
		"authorization": "Bearer x",
		"content-type":  "application/json",
	})
	if w.Code != http.StatusBadRequest {
		t.Fatalf("orders bad json: want 400, got %d", w.Code)
	}
}

func TestPostOrder_UnknownUser(t *testing.T) {
	body := `{"userId":99999,"items":["a"]}`
	w := doReq(t, newRouter(), "POST", "/orders", body, map[string]string{
		"authorization": "Bearer x",
		"content-type":  "application/json",
	})
	if w.Code != http.StatusBadRequest {
		t.Fatalf("orders unknown user: want 400, got %d body=%s", w.Code, w.Body.String())
	}
}

func TestPostOrder_CreateThenGet(t *testing.T) {
	h := newRouter()
	body := `{"userId":1,"items":["apple","pear"]}`
	w := doReq(t, h, "POST", "/orders", body, map[string]string{
		"authorization": "Bearer x",
		"content-type":  "application/json",
	})
	if w.Code != http.StatusCreated {
		t.Fatalf("orders create: want 201, got %d body=%s", w.Code, w.Body.String())
	}
	var created order
	if err := json.Unmarshal(w.Body.Bytes(), &created); err != nil {
		t.Fatalf("orders create body not json: %v", err)
	}
	if created.ID == 0 || created.UserID != 1 || len(created.Items) != 2 {
		t.Fatalf("orders create: bad payload %+v", created)
	}

	path := "/orders/" + itoa(created.ID)
	w2 := doReq(t, h, "GET", path, "", nil)
	if w2.Code != http.StatusOK {
		t.Fatalf("orders get: want 200, got %d body=%s", w2.Code, w2.Body.String())
	}
	var got order
	if err := json.Unmarshal(w2.Body.Bytes(), &got); err != nil {
		t.Fatalf("orders get body not json: %v", err)
	}
	if got.ID != created.ID || got.UserID != 1 {
		t.Fatalf("orders get: mismatch %+v vs %+v", got, created)
	}
}

func TestGetOrder_NotFound(t *testing.T) {
	w := doReq(t, newRouter(), "GET", "/orders/424242", "", nil)
	if w.Code != http.StatusNotFound {
		t.Fatalf("orders/424242: want 404, got %d", w.Code)
	}
}

func TestGetOrder_BadID(t *testing.T) {
	w := doReq(t, newRouter(), "GET", "/orders/abc", "", nil)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("orders/abc: want 400, got %d", w.Code)
	}
}

func itoa(i int) string {
	if i == 0 {
		return "0"
	}
	neg := false
	if i < 0 {
		neg = true
		i = -i
	}
	var b [20]byte
	pos := len(b)
	for i > 0 {
		pos--
		b[pos] = byte('0' + i%10)
		i /= 10
	}
	if neg {
		pos--
		b[pos] = '-'
	}
	return string(b[pos:])
}
