#!/usr/bin/env python3
"""
detect_stack.py — infer the stack of a repository for smoke-test scaffolding.

Reads top-level manifests / config files and emits a JSON description of:
  - languages: which language(s) the project uses
  - frameworks: web/api frameworks identified (FastAPI, Express, Gin, ...)
  - test_runners: existing test runners (pytest, vitest, go test, ...)
  - entry_points: candidate executable entry files (main.py, index.ts, main.go)
  - http_routes: best-effort list of URL routes discovered in source
  - has_ci: whether GitHub Actions / GitLab CI files exist
  - notes: caveats and detection hints

The output is consumed by the smoke-test skill to pick a template + tailor
generated tests to the user's actual stack.

This is intentionally a *fast, shallow* scanner. It reads manifest files
and greps a few common shapes; it does not parse ASTs or run language
servers. The skill should treat the output as a starting point and ask
the user to confirm before generating any tests.

Usage:
    python detect_stack.py [repo_path]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

IGNORE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env",
    "target", "dist", "build", "out", "bin", "obj",
    "__pycache__", ".next", ".nuxt", ".cache",
    "vendor", "third_party", ".gradle", ".idea",
    "coverage", ".pytest_cache", ".mypy_cache", ".tox",
}


# ---------------------------------------------------------------------------
# Manifest readers


def read_text_safe(path: Path, max_bytes: int = 200_000) -> str:
    try:
        with open(path, "rb") as fh:
            return fh.read(max_bytes).decode("utf-8", errors="replace")
    except OSError:
        return ""


def read_json_safe(path: Path) -> dict:
    text = read_text_safe(path)
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def read_toml_safe(path: Path) -> dict:
    """Tiny best-effort TOML reader for the [section] key = "value" subset we
    actually need (pyproject.toml deps, Cargo.toml [dependencies]). Falls
    back to returning the raw text under key "_raw" for grep-style probing.
    """
    text = read_text_safe(path)
    return {"_raw": text}


# ---------------------------------------------------------------------------
# Detection helpers


def list_source_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".")]
        for name in filenames:
            out.append(Path(dirpath) / name)
            if len(out) > 5000:
                return out
    return out


def detect_languages(root: Path, files: list[Path]) -> list[str]:
    """Lightweight extension census. Languages used in 3+ files (or having a
    manifest) are returned."""
    counts: dict[str, int] = {}
    ext_lang = {
        ".py": "python", ".rb": "ruby", ".go": "go",
        ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
        ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript",
        ".rs": "rust", ".java": "java", ".kt": "kotlin",
        ".php": "php", ".cs": "csharp", ".swift": "swift",
        ".ex": "elixir", ".exs": "elixir",
    }
    for f in files:
        lang = ext_lang.get(f.suffix.lower())
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    chosen = [l for l, c in counts.items() if c >= 3]
    # Also include languages with a manifest even if few files exist yet.
    manifest_lang = {
        "package.json": ("javascript", "typescript"),
        "pyproject.toml": ("python",),
        "requirements.txt": ("python",),
        "Cargo.toml": ("rust",),
        "go.mod": ("go",),
        "Gemfile": ("ruby",),
        "composer.json": ("php",),
        "pom.xml": ("java",),
        "build.gradle": ("java", "kotlin"),
        "mix.exs": ("elixir",),
    }
    for manifest, langs in manifest_lang.items():
        if (root / manifest).exists():
            for lang in langs:
                if lang not in chosen and counts.get(lang, 0) > 0:
                    chosen.append(lang)
                elif lang not in chosen:
                    chosen.append(lang)
    return sorted(set(chosen))


def detect_node_frameworks(root: Path) -> tuple[list[str], list[str]]:
    pkg = read_json_safe(root / "package.json")
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    fw: list[str] = []
    runners: list[str] = []
    framework_keys = {
        "express": "express", "fastify": "fastify", "koa": "koa",
        "hapi": "hapi", "@hapi/hapi": "hapi",
        "@nestjs/core": "nestjs", "next": "nextjs", "remix": "remix",
        "@hono/node-server": "hono", "hono": "hono",
        "react": "react", "vue": "vue", "@angular/core": "angular",
    }
    for k, name in framework_keys.items():
        if k in deps and name not in fw:
            fw.append(name)
    runner_keys = {
        "vitest": "vitest", "jest": "jest", "mocha": "mocha",
        "@playwright/test": "playwright", "cypress": "cypress",
        "supertest": "supertest", "ava": "ava",
    }
    for k, name in runner_keys.items():
        if k in deps and name not in runners:
            runners.append(name)
    return fw, runners


def detect_python_frameworks(root: Path) -> tuple[list[str], list[str]]:
    candidates: list[Path] = [
        root / "pyproject.toml", root / "requirements.txt",
        root / "Pipfile", root / "setup.cfg", root / "setup.py",
    ]
    haystack = ""
    for c in candidates:
        if c.exists():
            haystack += "\n" + read_text_safe(c)
    fw: list[str] = []
    runners: list[str] = []
    fw_map = {
        "fastapi": "fastapi", "starlette": "starlette",
        "flask": "flask", "django": "django",
        "aiohttp": "aiohttp", "sanic": "sanic", "tornado": "tornado",
        "litestar": "litestar", "quart": "quart",
    }
    for key, name in fw_map.items():
        if re.search(rf"\b{re.escape(key)}\b", haystack, re.IGNORECASE):
            fw.append(name)
    runner_map = {
        "pytest": "pytest", "unittest": "unittest",
        "nose2": "nose2", "tox": "tox", "httpx": "httpx", "requests": "requests",
        "playwright": "playwright", "selenium": "selenium",
    }
    for key, name in runner_map.items():
        if re.search(rf"\b{re.escape(key)}\b", haystack, re.IGNORECASE):
            runners.append(name)
    return fw, runners


def detect_go_frameworks(root: Path) -> tuple[list[str], list[str]]:
    fw: list[str] = []
    runners: list[str] = []
    go_mod = root / "go.mod"
    if not go_mod.exists():
        return fw, runners
    text = read_text_safe(go_mod)
    fw_map = {
        "github.com/gin-gonic/gin": "gin",
        "github.com/labstack/echo": "echo",
        "github.com/gofiber/fiber": "fiber",
        "github.com/go-chi/chi": "chi",
        "github.com/gorilla/mux": "gorilla-mux",
        "github.com/julienschmidt/httprouter": "httprouter",
    }
    for key, name in fw_map.items():
        if key in text:
            fw.append(name)
    # Plain net/http is always available; mark only if no external framework found
    # but routes exist in source.
    runners.append("go-test")
    if "github.com/stretchr/testify" in text:
        runners.append("testify")
    return fw, runners


def detect_rust_frameworks(root: Path) -> tuple[list[str], list[str]]:
    fw: list[str] = []
    runners: list[str] = []
    cargo = root / "Cargo.toml"
    if not cargo.exists():
        return fw, runners
    text = read_text_safe(cargo)
    fw_map = {"axum": "axum", "actix-web": "actix-web", "rocket": "rocket",
              "warp": "warp", "tide": "tide", "poem": "poem"}
    for key, name in fw_map.items():
        if re.search(rf"^\s*{re.escape(key)}\s*=", text, re.MULTILINE):
            fw.append(name)
    runners.append("cargo-test")
    return fw, runners


def detect_ruby_frameworks(root: Path) -> tuple[list[str], list[str]]:
    fw: list[str] = []
    runners: list[str] = []
    gemfile = root / "Gemfile"
    if not gemfile.exists():
        return fw, runners
    text = read_text_safe(gemfile)
    fw_map = {"rails": "rails", "sinatra": "sinatra", "hanami": "hanami",
              "rack": "rack", "grape": "grape"}
    for key, name in fw_map.items():
        if re.search(rf"\b{re.escape(key)}\b", text):
            fw.append(name)
    runner_map = {"rspec": "rspec", "minitest": "minitest", "capybara": "capybara"}
    for key, name in runner_map.items():
        if re.search(rf"\b{re.escape(key)}\b", text):
            runners.append(name)
    return fw, runners


# ---------------------------------------------------------------------------
# Entry-point and route discovery


ENTRY_PATTERNS = {
    "python": ["main.py", "app.py", "server.py", "wsgi.py", "asgi.py", "manage.py"],
    "javascript": ["index.js", "server.js", "app.js", "main.js", "src/index.js", "src/server.js"],
    "typescript": ["index.ts", "server.ts", "app.ts", "main.ts", "src/index.ts", "src/server.ts"],
    "go": ["main.go", "cmd/server/main.go", "cmd/api/main.go"],
    "rust": ["src/main.rs", "src/bin/server.rs"],
    "ruby": ["config.ru", "app.rb", "config/application.rb"],
}


def find_entry_points(root: Path, languages: list[str]) -> list[str]:
    out: list[str] = []
    for lang in languages:
        for rel in ENTRY_PATTERNS.get(lang, []):
            p = root / rel
            if p.exists() and p.is_file():
                out.append(str(p.relative_to(root)))
    return out


ROUTE_PATTERNS = [
    # FastAPI / Flask / Starlette decorators
    re.compile(r"""@\w*\.?(?:get|post|put|patch|delete|head|options)\(\s*["']([^"']+)["']""", re.IGNORECASE),
    # Express / Fastify / Koa method calls
    re.compile(r"""\.(?:get|post|put|patch|delete|use|head|options)\(\s*["']([^"']+)["']""", re.IGNORECASE),
    # Django urls.py — path() / re_path()
    re.compile(r"""(?:path|re_path)\(\s*["']([^"']+)["']"""),
    # Django DRF routers — router.register('path', ViewSet)
    re.compile(r"""router\.register\(\s*["']([^"']+)["']"""),
    # Gin / Echo / Chi / gorilla mux — uppercase HTTP method literals
    re.compile(r"""\.(?:GET|POST|PUT|PATCH|DELETE|HandleFunc|Handle)\(\s*["']([^"']+)["']"""),
    # axum / warp — `.route("/path", get(handler))` / `.route("/path", post(handler))`
    re.compile(r"""\.route\(\s*["'](/[^"']*)["']\s*,\s*(?:get|post|put|patch|delete|head|options)"""),
    # axum — `.nest("/prefix", ...)`
    re.compile(r"""\.nest\(\s*["'](/[^"']*)["']"""),
    # actix-web — `.service(web::resource("/path"))` and `.route("/path", web::get())`
    re.compile(r"""web::(?:resource|scope)\(\s*["'](/[^"']*)["']"""),
    re.compile(r"""\.route\(\s*["'](/[^"']*)["']\s*,\s*web::"""),
    # Rocket — `#[get("/path")]`
    re.compile(r"""#\[\s*(?:get|post|put|patch|delete|head|options)\(\s*["']([^"']+)["']""", re.IGNORECASE),
    # Spring — `@GetMapping("/path")`, `@RequestMapping("/path")`
    re.compile(r"""@(?:Get|Post|Put|Patch|Delete|Request)Mapping\(\s*["']([^"']+)["']"""),
    # Rails routes.rb — `get '/path', to: ...` etc.
    re.compile(r"""^\s*(?:get|post|put|patch|delete)\s+["']([^"']+)["']\s*,""", re.MULTILINE),
    # Fallback: bare `.route("/path", ...)` / `.with("/path", ...)`
    re.compile(r"""\.(?:route|nest|with)\(\s*["'](/[^"']*)["']"""),
]


# Suspected false-positive routes — strings that often appear inside
# `headers.get("authorization")`, JSON keys, content-type tokens etc.
# Filter them so callers don't see "/authorization" in the route list.
NOISE_ROUTES = {
    "/authorization", "/content-type", "/content-length",
    "/accept", "/accept-encoding", "/user-agent",
    "/x-request-id", "/x-correlation-id", "/host",
    "/cache-control", "/set-cookie", "/cookie", "/origin", "/referer",
    "/connection", "/upgrade", "/from", "/to",
}


def find_routes(root: Path, files: list[Path], limit: int = 50) -> list[str]:
    routes: list[str] = []
    seen: set[str] = set()
    for f in files:
        if f.suffix.lower() not in {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx",
                                     ".go", ".rs", ".rb", ".java", ".kt"}:
            continue
        text = read_text_safe(f)
        if not text:
            continue
        for pat in ROUTE_PATTERNS:
            for m in pat.finditer(text):
                r = m.group(1)
                if not r.startswith("/"):
                    r = "/" + r
                if r in seen:
                    continue
                if len(r) > 100:
                    continue
                if r.lower() in NOISE_ROUTES:
                    continue
                seen.add(r)
                routes.append(r)
                if len(routes) >= limit:
                    return routes
    return routes


def detect_ci(root: Path) -> list[str]:
    out: list[str] = []
    if (root / ".github" / "workflows").is_dir():
        out.append("github-actions")
    if (root / ".gitlab-ci.yml").exists():
        out.append("gitlab-ci")
    if (root / ".circleci" / "config.yml").exists():
        out.append("circleci")
    if (root / "azure-pipelines.yml").exists():
        out.append("azure-pipelines")
    if (root / "Jenkinsfile").exists():
        out.append("jenkins")
    return out


# ---------------------------------------------------------------------------
# Main


def detect(root: Path) -> dict:
    root = root.resolve()
    files = list_source_files(root)
    languages = detect_languages(root, files)

    frameworks: list[str] = []
    runners: list[str] = []

    detectors = {
        "javascript": detect_node_frameworks, "typescript": detect_node_frameworks,
        "python": detect_python_frameworks,
        "go": detect_go_frameworks,
        "rust": detect_rust_frameworks,
        "ruby": detect_ruby_frameworks,
    }
    seen_fn: set = set()
    for lang in languages:
        fn = detectors.get(lang)
        if fn and fn not in seen_fn:
            seen_fn.add(fn)
            f, r = fn(root)
            for x in f:
                if x not in frameworks:
                    frameworks.append(x)
            for x in r:
                if x not in runners:
                    runners.append(x)

    entry = find_entry_points(root, languages)
    routes = find_routes(root, files)
    ci = detect_ci(root)

    notes: list[str] = []
    if not languages:
        notes.append("No recognised language manifests; this may not be a software repo.")
    if languages and not frameworks:
        notes.append("Language detected but no web/API framework identified — generated smoke tests will be lower-level (process exit, CLI invocation) instead of HTTP checks.")
    if not routes and frameworks:
        notes.append("Framework detected but no routes parsed — the user may need to point the skill at the right source directory or supply route paths manually.")
    if not ci:
        notes.append("No CI config detected — skill can offer to scaffold one alongside the smoke tests.")

    return {
        "repo": str(root),
        "languages": languages,
        "frameworks": frameworks,
        "test_runners": runners,
        "entry_points": entry,
        "http_routes": routes,
        "has_ci": ci,
        "file_count": len(files),
        "notes": notes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detect stack for smoke-test scaffolding.")
    parser.add_argument("repo", nargs="?", default=".", help="Path to repository root (default: cwd).")
    parser.add_argument("--output", "-o", help="Write JSON to file instead of stdout.")
    args = parser.parse_args(argv)

    repo = Path(args.repo)
    if not repo.exists():
        print(f"error: path does not exist: {repo}", file=sys.stderr)
        return 2

    result = detect(repo)
    payload = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
