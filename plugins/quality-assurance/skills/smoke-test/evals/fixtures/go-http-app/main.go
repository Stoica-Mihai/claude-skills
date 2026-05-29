package main

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
	"sync"
)

type user struct {
	ID   int    `json:"id"`
	Name string `json:"name"`
}

type order struct {
	ID     int      `json:"id"`
	UserID int      `json:"userId"`
	Items  []string `json:"items"`
}

var (
	mu     sync.Mutex
	users  = map[int]user{1: {ID: 1, Name: "alice"}, 2: {ID: 2, Name: "bob"}}
	orders = map[int]order{}
	nextID = 1
)

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("content-type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func usersHandler(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.Atoi(strings.TrimPrefix(r.URL.Path, "/users/"))
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "bad id"})
		return
	}
	mu.Lock()
	u, ok := users[id]
	mu.Unlock()
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "user not found"})
		return
	}
	writeJSON(w, http.StatusOK, u)
}

func ordersPost(w http.ResponseWriter, r *http.Request) {
	if !strings.HasPrefix(r.Header.Get("authorization"), "Bearer ") {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "missing token"})
		return
	}
	var in struct {
		UserID int      `json:"userId"`
		Items  []string `json:"items"`
	}
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "bad json"})
		return
	}
	mu.Lock()
	if _, ok := users[in.UserID]; !ok {
		mu.Unlock()
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "unknown user"})
		return
	}
	id := nextID
	nextID++
	o := order{ID: id, UserID: in.UserID, Items: in.Items}
	orders[id] = o
	mu.Unlock()
	writeJSON(w, http.StatusCreated, o)
}

func ordersGet(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.Atoi(strings.TrimPrefix(r.URL.Path, "/orders/"))
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "bad id"})
		return
	}
	mu.Lock()
	o, ok := orders[id]
	mu.Unlock()
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "order not found"})
		return
	}
	writeJSON(w, http.StatusOK, o)
}

func newRouter() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", health)
	mux.HandleFunc("/users/", usersHandler)
	mux.HandleFunc("/orders", ordersPost)
	mux.HandleFunc("/orders/", ordersGet)
	return mux
}

func main() {
	_ = http.ListenAndServe(":8080", newRouter())
}
