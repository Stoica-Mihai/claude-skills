#!/usr/bin/env python3
"""
find_hotspots.py — surface architectural hotspots in a codebase.

Strategy:
  1. Enumerate source files via `git ls-files` (fallback: os.walk with ignore list).
  2. Extract imports per file using language-aware regex patterns.
  3. Resolve each import to an internal repo file via:
        a. Relative path resolution (for `./`, `../`, same-package imports).
        b. Basename match across the repo (last path segment -> file stems).
     External/unresolved imports are dropped.
  4. Compute per-file metrics: fan_in, fan_out, loc, SCC membership.
  5. Emit a ranked markdown report grouped by dimension:
        - Hubs (high fan-in)
        - Tangles (high fan-out)
        - God modules (large LOC)
        - Cycles (SCCs of size > 1)

Composite scores are deliberately avoided — each section answers one question,
the human reader combines them.

Usage:
    python find_hotspots.py [repo_path] [--top N] [--god-loc N]
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration

# Directories we never descend into when falling back to os.walk.
DEFAULT_IGNORE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env",
    "target", "dist", "build", "out", "bin", "obj",
    "__pycache__", ".next", ".nuxt", ".cache",
    "vendor", "third_party", "deps", ".gradle", ".idea",
    "coverage", ".pytest_cache", ".mypy_cache", ".tox",
}

# Extensions parsed with language-specific patterns. Precise, lower false-positive.
PRECISE_EXTENSIONS = {
    ".py": "python",
    ".js": "js", ".mjs": "js", ".cjs": "js", ".jsx": "js",
    ".ts": "js", ".tsx": "js",
    ".vue": "js", ".svelte": "js",
    ".rs": "rust",
    ".go": "go",
    ".java": "java", ".kt": "java", ".kts": "java",
    ".c": "c", ".h": "c", ".cc": "c", ".cpp": "c", ".cxx": "c", ".hpp": "c", ".hh": "c",
    ".rb": "ruby",
    ".cs": "csharp",
    ".php": "php",
    ".swift": "swift",
    ".scala": "scala",
    ".qml": "qml",
    ".nix": "nix",
}

# Extensions parsed with the generic best-effort regex set. Covers languages
# we don't have dedicated patterns for. Lossier — false positives possible —
# but means the analyzer degrades gracefully instead of returning zero edges
# on whole language families.
GENERIC_EXTENSIONS = {
    ".dart", ".ex", ".exs", ".erl", ".hrl", ".hs", ".lhs",
    ".ml", ".mli", ".lua", ".r", ".jl", ".nim", ".zig",
    ".cr", ".pl", ".pm", ".sh", ".bash", ".zsh", ".ksh", ".fish",
    ".clj", ".cljs", ".cljc", ".edn", ".lisp", ".lsp", ".scm", ".rkt",
    ".fs", ".fsx", ".fsi", ".ada", ".adb", ".ads", ".pas", ".pp",
    ".d", ".groovy", ".gd", ".gradle", ".gleam", ".v",
    ".sol", ".move", ".pkl", ".elm",
    # Extra long-tail languages — generic patterns may catch their import
    # syntax; if not, they at least show up in LOC/god-module tables.
    ".tcl", ".tk", ".lean", ".idr", ".idr2", ".agda", ".coq",
    ".raku", ".rakumod", ".p6", ".pm6",
    ".f", ".for", ".f90", ".f95", ".f03", ".f08",
    ".cob", ".cbl", ".cpy", ".ahk", ".au3",
    ".vala", ".vapi", ".reb", ".red", ".scala3",
    ".sml", ".sig", ".fun", ".m", ".mm",
    ".ps1", ".psm1", ".bat", ".cmd",
    ".hx", ".hxml", ".purs", ".re", ".rei",
    ".coffee", ".litcoffee", ".moon", ".rkt", ".scrbl",
    ".kt", ".odin", ".jakt", ".vlang",
    ".bal", ".carbon", ".jq",
}

SOURCE_EXTENSIONS: dict[str, str] = {
    **PRECISE_EXTENSIONS,
    **{ext: "generic" for ext in GENERIC_EXTENSIONS},
}

# Import regex per language family. Each regex captures the imported module path.
IMPORT_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    # Python handled separately by extract_imports — see _PY_* patterns below.
    "js": [
        re.compile(r"""(?:^|\s)import\s+(?:[^'"`]+?\s+from\s+)?['"]([^'"]+)['"]""", re.MULTILINE),
        re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)"""),
        re.compile(r"""import\(\s*['"]([^'"]+)['"]\s*\)"""),
        re.compile(r"""(?:^|\s)export\s+(?:[^'"`]+\s+from\s+)['"]([^'"]+)['"]""", re.MULTILINE),
    ],
    "rust": [
        # Plain path: `use crate::foo::Bar`, `pub use foo::bar`. Optional
        # `pub` prefix supported. Captures up to first whitespace, `{`, or `;`.
        re.compile(r"^\s*(?:pub\s+)?use\s+([A-Za-z_][\w:]*)", re.MULTILINE),
        # Grouped: `use crate::foo::{Bar, Baz}` or multi-line block.
        # Captures the prefix and the braced body separately; extract_imports
        # handles distribution.
        re.compile(
            r"^\s*(?:pub\s+)?use\s+([A-Za-z_][\w:]*)\s*::\s*\{([^}]*)\}",
            re.MULTILINE | re.DOTALL,
        ),
        re.compile(r"^\s*mod\s+([A-Za-z_]\w*)\s*;", re.MULTILINE),
    ],
    "go": [
        re.compile(r"""^\s*import\s+"([^"]+)"\s*$""", re.MULTILINE),
        re.compile(r"""import\s*\(([^)]*)\)""", re.DOTALL),
    ],
    "java": [
        re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)\s*;", re.MULTILINE),
    ],
    "c": [
        re.compile(r"""^\s*#\s*include\s*[<"]([^">]+)[">]""", re.MULTILINE),
    ],
    "ruby": [
        re.compile(r"""^\s*require(?:_relative)?\s+['"]([^'"]+)['"]""", re.MULTILINE),
    ],
    "csharp": [
        re.compile(r"^\s*using\s+([A-Za-z_][\w.]*)\s*;", re.MULTILINE),
    ],
    "php": [
        re.compile(r"""^\s*(?:require|include|require_once|include_once)\s*\(?\s*['"]([^'"]+)['"]""", re.MULTILINE),
        re.compile(r"^\s*use\s+([\w\\]+)\s*;", re.MULTILINE),
    ],
    "swift": [
        re.compile(r"^\s*import\s+(\w+)", re.MULTILINE),
    ],
    "scala": [
        re.compile(r"^\s*import\s+([\w.]+)", re.MULTILINE),
    ],
    "qml": [
        # `import qs.Bar.StatusBar` or `import qs.Config 1.0`
        re.compile(r"""^\s*import\s+([\w.]+)""", re.MULTILINE),
        # `import "../Widgets"` / `import "./Foo.qml"`
        re.compile(r"""^\s*import\s+["']([^"']+)["']""", re.MULTILINE),
    ],
    "nix": [
        # `imports = [ ./foo.nix ./bar.nix ];` — NixOS module list. The
        # bracketed content is captured whole; extract_imports splits it.
        re.compile(r"""imports\s*=\s*\[([^\]]+)\]""", re.DOTALL),
        # `import ./foo.nix` — function-style import.
        re.compile(r"""\bimport\s+(\.{0,2}/[\w./-]+|\w[\w./-]*)""", re.MULTILINE),
    ],
    # Best-effort patterns applied to files in GENERIC_EXTENSIONS. Catches
    # the union of common import keywords across languages we don't have a
    # dedicated parser for. Order matters — more specific shapes first so
    # the broader bare-keyword pattern at the end doesn't shadow them.
    "generic": [
        # Quoted-target imports: `require "foo"`, `include "foo"`, `import "foo"`,
        # `#include <foo>`, `use "foo"`, etc. Quoted form is high-confidence.
        re.compile(
            r"""(?ix)
            ^\s*\#?\s*
            (?:import|require_relative|require|use|include|open|with|load)
            \s+ ["'<] ([^"'>]+) [">']
            """,
            re.MULTILINE | re.VERBOSE,
        ),
        # `from foo.bar import baz` — Python/Elm/F# style.
        re.compile(r"^\s*from\s+([\w.:/-]+)\s+import\b", re.MULTILINE),
        # Bare-keyword + dotted/slashed identifier: `import foo.bar`,
        # `use foo::bar`, `open Foo.Bar`, `mod foo`, `extern crate foo`,
        # `import ./foo.nix`. Leading `.` and `/` allowed so Nix-style and
        # path-prefixed imports resolve.
        re.compile(
            r"""(?ix)
            ^\s*
            (?:import|use|open|with|mod|extern\s+crate)
            \s+ ([./][\w./:-]*|[A-Za-z_][\w.:/-]*)
            """,
            re.MULTILINE | re.VERBOSE,
        ),
    ],
}


# ---------------------------------------------------------------------------
# File discovery


def list_files(root: Path) -> list[Path]:
    """Prefer `git ls-files` (free .gitignore handling); fall back to os.walk."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files"],
            check=True, capture_output=True, text=True, timeout=30,
        )
        files = [root / line for line in result.stdout.splitlines() if line]
        if files:
            return [f for f in files if f.is_file()]
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in DEFAULT_IGNORE_DIRS and not d.startswith(".")]
        for name in filenames:
            out.append(Path(dirpath) / name)
    return out


# Map shebang interpreter to language. Strip version digits / suffixes when
# matching (`python3.11` -> `python`).
SHEBANG_INTERPRETER_TO_LANG = {
    "python": "python", "python2": "python", "python3": "python",
    "node": "js", "nodejs": "js", "deno": "js", "bun": "js",
    "ruby": "ruby", "rake": "ruby",
    "php": "php",
    "perl": "generic", "perl5": "generic",
    "bash": "generic", "sh": "generic", "zsh": "generic", "ksh": "generic",
    "dash": "generic", "fish": "generic",
    "lua": "generic", "luajit": "generic",
    "tclsh": "generic", "wish": "generic", "expect": "generic",
    "awk": "generic", "gawk": "generic", "mawk": "generic",
    "ocaml": "generic", "ocamlrun": "generic",
    "scala": "scala",
    "swift": "swift",
    "raku": "generic", "perl6": "generic",
    "Rscript": "generic", "littler": "generic",
    "julia": "generic",
    "groovy": "generic",
    "pwsh": "generic", "powershell": "generic",
    "racket": "generic", "guile": "generic", "scheme": "generic",
    "elixir": "generic", "iex": "generic",
    "crystal": "generic",
    "dart": "generic",
    "nim": "generic",
    "zig": "generic",
}

# Editor modelines and language-marker first-line comments.
# Vim:   `vim: filetype=lua` or `vim: ft=lua`
# Emacs: `-*- mode: scheme -*-`
_MODELINE = re.compile(
    r"""(?ix)
    (?:vim|vi|ex)? : \s* (?:set\s+)?
    (?:filetype|ft|syntax) \s*=\s* (\w+)
    |
    -\*- .* (?:mode \s*:\s*) (\w+) .* -\*-
    """,
    re.VERBOSE,
)

# Map vim filetype / emacs mode to our lang tag. Conservative — only map
# things that will give us an existing parser.
MODELINE_LANG_MAP = {
    "python": "python", "py": "python",
    "javascript": "js", "js": "js", "typescript": "js", "ts": "js",
    "jsx": "js", "tsx": "js",
    "go": "go",
    "rust": "rust", "rs": "rust",
    "ruby": "ruby", "rb": "ruby",
    "java": "java", "kotlin": "java",
    "c": "c", "cpp": "c", "cxx": "c",
    "php": "php",
    "swift": "swift",
    "scala": "scala",
    "qml": "qml",
    "nix": "nix",
    "shell": "generic", "sh": "generic", "bash": "generic", "zsh": "generic",
    "lua": "generic", "tcl": "generic", "perl": "generic",
    "lisp": "generic", "scheme": "generic", "racket": "generic",
    "haskell": "generic", "ocaml": "generic", "fsharp": "generic",
    "elixir": "generic", "erlang": "generic",
    "r": "generic", "julia": "generic", "nim": "generic",
}


def detect_lang_from_header(path: Path) -> str | None:
    """Read first ~2KB and try shebang + modeline detection.

    Returns a lang tag if a confident match is found, else None.
    """
    try:
        with open(path, "rb") as fh:
            head = fh.read(2048)
    except OSError:
        return None
    try:
        text = head.decode("utf-8", errors="replace")
    except UnicodeDecodeError:
        return None

    lines = text.splitlines()
    # Shebang must be the very first line.
    if lines and lines[0].startswith("#!"):
        # `#!/usr/bin/env python3` or `#!/usr/bin/python3`
        tokens = lines[0][2:].split()
        for tok in tokens:
            base = os.path.basename(tok).lower()
            # Strip trailing version digits (`python3.11` -> `python`).
            stem = re.sub(r"[0-9.]+$", "", base)
            stem = stem or base
            if base in SHEBANG_INTERPRETER_TO_LANG:
                return SHEBANG_INTERPRETER_TO_LANG[base]
            if stem in SHEBANG_INTERPRETER_TO_LANG:
                return SHEBANG_INTERPRETER_TO_LANG[stem]

    # Modeline: typically first or last few lines of the file.
    for line in lines[:5] + lines[-5:]:
        m = _MODELINE.search(line)
        if m:
            tag = (m.group(1) or m.group(2) or "").lower()
            if tag in MODELINE_LANG_MAP:
                return MODELINE_LANG_MAP[tag]

    return None


def looks_like_text(path: Path, max_bytes: int = 4096) -> bool:
    """Heuristic: file is probably text (and thus worth running generic
    patterns on) when it contains no NUL bytes in the first chunk and is
    >80% printable ASCII / UTF-8 decodable."""
    try:
        with open(path, "rb") as fh:
            chunk = fh.read(max_bytes)
    except OSError:
        return False
    if not chunk:
        return False
    if b"\x00" in chunk:
        return False
    try:
        decoded = chunk.decode("utf-8")
    except UnicodeDecodeError:
        return False
    printable = sum(1 for c in decoded if c.isprintable() or c in "\n\r\t")
    return printable / max(1, len(decoded)) > 0.8


def source_files(
    files: list[Path],
    sniff: bool = False,
    extra_exts: dict[str, str] | None = None,
) -> list[tuple[Path, str]]:
    """Return [(path, language)] for files we will parse.

    Detection order, first hit wins:
      1. CLI-supplied `extra_exts` (`--ext .foo=python`).
      2. Static SOURCE_EXTENSIONS lookup on the file's extension.
      3. Shebang interpreter (`#!/usr/bin/env tclsh` → generic).
      4. Vim / Emacs modeline (`# vim: ft=lua`).
      5. If `sniff=True` and the file has no extension or an unknown one,
         test whether the file looks like text and try generic patterns.
    """
    extras = {k.lower(): v for k, v in (extra_exts or {}).items()}
    out: list[tuple[Path, str]] = []
    for f in files:
        ext = f.suffix.lower()
        lang = extras.get(ext) or SOURCE_EXTENSIONS.get(ext)
        if not lang:
            lang = detect_lang_from_header(f)
        if not lang and sniff and not ext or (sniff and ext not in SOURCE_EXTENSIONS):
            # Avoid sniffing huge binaries or known-prose files.
            if f.suffix.lower() in {".md", ".rst", ".txt", ".csv", ".json", ".xml", ".yaml", ".yml", ".toml", ".lock", ".log", ".min.js", ".map"}:
                continue
            if looks_like_text(f):
                lang = "generic"
        if lang:
            out.append((f, lang))
    return out


# ---------------------------------------------------------------------------
# Path-alias resolution (TypeScript / JavaScript projects)


_TS_PATH_ALIAS_FILE_RE = re.compile(r"^[jt]sconfig\.json$")


def load_path_aliases(repo_root: Path) -> dict[str, list[Path]]:
    """Read tsconfig.json / jsconfig.json and return an alias -> [dir] map.

    Aliases look like:
        "paths": { "@/*": ["src/*"], "@lib/*": ["src/lib/*"] }

    We strip the trailing `/*` for matching purposes; the resolver expands
    by replacing the alias prefix with each base directory.
    """
    import json
    aliases: dict[str, list[Path]] = {}
    for cfg in repo_root.rglob("*sconfig.json"):
        if not _TS_PATH_ALIAS_FILE_RE.match(cfg.name):
            continue
        if any(part in DEFAULT_IGNORE_DIRS for part in cfg.parts):
            continue
        try:
            text = cfg.read_text(encoding="utf-8", errors="replace")
            # tsconfig allows comments and trailing commas — light cleanup.
            text = re.sub(r"//[^\n]*", "", text)
            text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
            text = re.sub(r",(\s*[}\]])", r"\1", text)
            data = json.loads(text)
        except (OSError, json.JSONDecodeError):
            continue
        opts = data.get("compilerOptions", {})
        base_url = opts.get("baseUrl", ".")
        anchor = (cfg.parent / base_url).resolve()
        paths = opts.get("paths", {})
        if not isinstance(paths, dict):
            continue
        for key, vals in paths.items():
            if not isinstance(vals, list):
                continue
            key_clean = key.rstrip("*").rstrip("/")
            if not key_clean:
                continue
            resolved_dirs: list[Path] = []
            for v in vals:
                if not isinstance(v, str):
                    continue
                v_clean = v.rstrip("*").rstrip("/")
                target = (anchor / v_clean).resolve()
                if _within(target, repo_root) or target == repo_root:
                    resolved_dirs.append(target)
            if resolved_dirs:
                aliases.setdefault(key_clean, []).extend(resolved_dirs)
    return aliases


def expand_alias(raw: str, aliases: dict[str, list[Path]]) -> list[Path]:
    """Return candidate base directories the alias-prefixed import maps to,
    or [] if the raw import doesn't start with any known alias."""
    for prefix, dirs in aliases.items():
        if raw == prefix or raw.startswith(prefix + "/"):
            tail = raw[len(prefix):].lstrip("/")
            return [d / tail if tail else d for d in dirs]
    return []


# ---------------------------------------------------------------------------
# Import extraction


_PY_FROM_IMPORT = re.compile(
    r"^\s*from\s+([.\w]+)\s+import\s+([^\n#]+)", re.MULTILINE
)
_PY_IMPORT = re.compile(r"^\s*import\s+([.\w]+(?:\s*,\s*[.\w]+)*)", re.MULTILINE)


def extract_imports(text: str, lang: str) -> list[str]:
    """Pull raw import targets out of source text.

    For Python `from X import Y, Z` we emit `X.Y` and `X.Z` so that the resolver
    can try to land on the *imported submodule* file (e.g. `models/order.py`)
    rather than always pointing at `models/__init__.py`. If `Y` is just a name
    re-exported from `X`, the basename matcher will still find `X` as a fallback
    via the bare module name.
    """
    raw: list[str] = []
    if lang == "python":
        for m in _PY_FROM_IMPORT.finditer(text):
            module = m.group(1).strip()
            names_part = m.group(2)
            # Strip parens (multi-line imports) and `as` aliases.
            names_part = names_part.replace("(", " ").replace(")", " ")
            emitted_any = False
            for name_token in names_part.split(","):
                name = name_token.strip().split()[0] if name_token.strip() else ""
                if not name or name == "*":
                    continue
                # Emit dotted form. The resolver tries last-segment first, then
                # falls back up to the package, so `from utils import helpers`
                # lands on `utils/helpers.py` while `from utils import some_fn`
                # falls back to `utils/__init__.py`.
                if module.endswith("."):
                    raw.append(module + name)
                else:
                    raw.append(f"{module}.{name}")
                emitted_any = True
            if not emitted_any:
                raw.append(module)
        for m in _PY_IMPORT.finditer(text):
            for part in m.group(1).split(","):
                raw.append(part.strip())
        return raw

    for pat in IMPORT_PATTERNS.get(lang, []):
        for m in pat.finditer(text):
            target = m.group(1)
            if lang == "rust" and m.lastindex and m.lastindex >= 2:
                # Grouped use: prefix in group(1), braced body in group(2).
                # Emit `prefix::name` for each name in body, handling nested
                # paths like `foo::{bar, baz::qux}` and `self`/`super` shortcuts.
                prefix = m.group(1).strip()
                body = m.group(2)
                # Strip comments and split on top-level commas. Nested braces
                # are rare in real code but handled by depth tracking.
                body = re.sub(r"//[^\n]*", "", body)
                body = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)
                tokens: list[str] = []
                depth = 0
                buf = ""
                for ch in body:
                    if ch == "{":
                        depth += 1
                        buf += ch
                    elif ch == "}":
                        depth -= 1
                        buf += ch
                    elif ch == "," and depth == 0:
                        if buf.strip():
                            tokens.append(buf.strip())
                        buf = ""
                    else:
                        buf += ch
                if buf.strip():
                    tokens.append(buf.strip())
                for tok in tokens:
                    name = re.split(r"\s+as\s+", tok, maxsplit=1)[0].strip()
                    if not name or name == "self":
                        # `use foo::{self, Bar}` — `self` means the module itself.
                        raw.append(prefix)
                    elif name == "*":
                        raw.append(prefix)
                    elif "{" in name:
                        # Nested group — emit prefix::name verbatim; the
                        # resolver's segment splitter will walk it.
                        nested_prefix, _, nested_body = name.partition("{")
                        nested_prefix = nested_prefix.rstrip(":").strip()
                        full_prefix = f"{prefix}::{nested_prefix}" if nested_prefix else prefix
                        for inner in nested_body.rstrip("}").split(","):
                            inner = inner.strip()
                            if inner and inner != "*":
                                raw.append(f"{full_prefix}::{inner}")
                    else:
                        raw.append(f"{prefix}::{name}")
                continue
            if lang == "go" and "\n" in target:
                for line in target.splitlines():
                    line = line.strip().strip(",")
                    m2 = re.match(r'^(?:\w+\s+)?"([^"]+)"', line)
                    if m2:
                        raw.append(m2.group(1))
            elif lang == "nix":
                # The list-form `imports = [ ./a.nix ./b.nix ]` captures the
                # entire bracket body. Function-form `import ./foo.nix` is
                # already a single token. Splitting on whitespace handles both.
                for token in re.split(r"\s+", target.strip()):
                    token = token.strip().strip(",").strip(";")
                    if token and not token.startswith("#"):
                        raw.append(token)
            elif lang == "qml":
                t = target.strip()
                # Skip Qt's own modules (QtQuick, Quickshell, etc.) — they are
                # not part of the project repo.
                if t.startswith(("QtQuick", "QtQml", "Qt5", "Qt6", "Quickshell")):
                    continue
                # Strip the project's QML namespace prefix. By convention most
                # Quickshell projects expose their tree under `qs.`. Without
                # stripping it the path-segment constraint can never match
                # because `qs` is a virtual namespace, not a directory.
                if t.startswith("qs."):
                    t = t[3:]
                raw.append(t)
            else:
                raw.append(target.strip())
    return raw


def count_loc(text: str) -> int:
    """Approximate LOC: non-blank lines. Comments not stripped — keeps it cheap and lang-agnostic."""
    return sum(1 for line in text.splitlines() if line.strip())


# ---------------------------------------------------------------------------
# Import resolution to internal files


@dataclass
class FileInfo:
    path: Path
    lang: str
    loc: int = 0
    imports_raw: list[str] = field(default_factory=list)


def build_basename_index(
    files: list[Path], root: Path
) -> tuple[dict[str, list[Path]], dict[str, list[Path]]]:
    """Two indices: stem-match (high confidence) and parent-dir-match (fallback).

    Stem index maps a file's own basename (without extension) to that file.
    Parent index maps a directory name to every file inside it.

    Resolution always tries the stem index first. The parent index is consulted
    only if the stem yielded nothing, because directory matches are noisier —
    they pull in *every* file in a package, not the one specifically named.
    """
    stem_idx: dict[str, list[Path]] = defaultdict(list)
    parent_idx: dict[str, list[Path]] = defaultdict(list)
    for f in files:
        stem = f.stem.lower()
        stem_idx[stem].append(f)
        # Also index the snake_case form so `amux_proto`-style Rust crate
        # names resolve to files in a `amux-proto/` directory.
        snake_stem = stem.replace("-", "_")
        if snake_stem != stem:
            stem_idx[snake_stem].append(f)
        parent = f.parent.name.lower()
        if parent:
            parent_idx[parent].append(f)
            snake_parent = parent.replace("-", "_")
            if snake_parent != parent:
                parent_idx[snake_parent].append(f)
    return stem_idx, parent_idx


def resolve_import(
    raw: str,
    source_file: Path,
    lang: str,
    stem_idx: dict[str, list[Path]],
    parent_idx: dict[str, list[Path]],
    repo_root: Path,
    aliases: dict[str, list[Path]] | None = None,
) -> Path | None:
    """Map a raw import target to an internal file. None = external/unresolvable."""
    raw = raw.strip().strip(";").strip("'\"")
    if not raw:
        return None

    # Path-alias expansion (tsconfig/jsconfig `paths` entries). Try each
    # alias-expanded candidate base via the JS-style resolver — extension
    # matching covers .ts/.tsx/.js/.jsx/index file conventions.
    if aliases and lang == "js":
        for base in expand_alias(raw, aliases):
            hit = _resolve_js_path(base, repo_root)
            if hit:
                return hit

    # Strip leading dots from python relative imports for fallback matching.
    last_segment_source = raw

    # Try relative path resolution first.
    if lang == "js" and (raw.startswith("./") or raw.startswith("../") or raw.startswith("/")):
        base = (source_file.parent / raw).resolve()
        return _resolve_js_path(base, repo_root)

    if lang == "python" and raw.startswith("."):
        # Count leading dots: each . = up one package level.
        dots = len(raw) - len(raw.lstrip("."))
        rest = raw[dots:]
        anchor = source_file.parent
        for _ in range(dots - 1):
            anchor = anchor.parent
        if rest:
            candidate = anchor / Path(*rest.split("."))
            return _resolve_python_path(candidate, repo_root)
        return _resolve_python_path(anchor, repo_root)

    if lang == "c":
        # Relative include: try sibling first.
        sibling = (source_file.parent / raw).resolve()
        if sibling.exists() and sibling.is_file() and _within(sibling, repo_root):
            return sibling
        last_segment_source = Path(raw).stem

    if lang == "ruby" and "/" in raw:
        candidate = source_file.parent / (raw + ".rb")
        if candidate.exists() and _within(candidate, repo_root):
            return candidate
        last_segment_source = Path(raw).stem

    # Split into segments using language-appropriate separators. We try each
    # segment from most specific (rightmost) to least specific (leftmost),
    # taking the first one that resolves. This handles cases like
    # `from utils import some_function` — "some_function" doesn't match a file
    # but "utils" does, so the edge is attributed to the utils package.
    raw_clean = last_segment_source.replace("\\", "/")

    # If the import ends in a known source-file extension (e.g. `lib_b.dart`,
    # `helpers.lua`, `./foo.ts`) strip it first so the splitter treats the
    # extension as a marker, not as a real path segment.
    for ext in SOURCE_EXTENSIONS:
        if raw_clean.lower().endswith(ext):
            raw_clean = raw_clean[: -len(ext)]
            break

    segments: list[str]
    # Order matters: a Go import path like `github.com/x/y/pkg` contains both
    # "/" (path separator) and "." (domain TLD). Split by "/" first when
    # present so the dotted domain doesn't get torn into bogus segments.
    if "/" in raw_clean:
        segments = raw_clean.strip("/").split("/")
    elif "::" in raw_clean:
        segments = raw_clean.split("::")
    elif "." in raw_clean:
        segments = raw_clean.strip(".").split(".")
    else:
        segments = [raw_clean]

    # Strip extension from the rightmost segment (e.g. C #include "foo.h").
    if segments:
        segments[-1] = segments[-1].rsplit(".", 1)[0]

    src_parts = source_file.parts

    def proximity(p: Path) -> tuple[int, int]:
        common = 0
        for a, b in zip(src_parts, p.parts):
            if a == b:
                common += 1
            else:
                break
        return (-common, len(p.parts))

    # Path-segment constraint: a candidate is only accepted if at least one
    # *other* segment of the import path also appears in the candidate's repo
    # path. Kills basename-only false positives where two unrelated files
    # share a stem (e.g. `pkg/plugin/errors.go` vs `plugins/twitch/errors.go`
    # being tied together because both end in `errors.go`).
    #
    # For single-segment imports (e.g. Go `import "errors"`, Python
    # `import json`, Java `import Singleton`) there is no other segment to
    # corroborate with, so we instead require the candidate to live on the
    # source file's directory chain (same dir or an ancestor). This drops
    # stdlib look-alikes that happen to share a name with a project file.
    other_segments_lower = {s.lower() for s in segments[:-1] if s}
    source_dir_chain = {part.lower() for part in source_file.parent.parts}

    def candidate_on_source_chain(p: Path) -> bool:
        # True if p's directory equals source's or is an ancestor within the repo.
        src_parent = source_file.parent
        cand_parent = p.parent
        try:
            src_parent.relative_to(cand_parent)
            return True
        except ValueError:
            pass
        try:
            cand_parent.relative_to(src_parent)
            return True
        except ValueError:
            return False

    def has_corroborating_segment(p: Path) -> bool:
        if not other_segments_lower:
            # Single-segment import — require candidate on source's dir chain.
            return candidate_on_source_chain(p)
        # Use the path relative to the repo root, so the workspace prefix
        # (e.g. `/home/user/projects/ghyll/...`) doesn't accidentally
        # corroborate a Go import like `github.com/user/ghyll/...`.
        try:
            rel = p.relative_to(repo_root)
        except ValueError:
            rel = p
        # Only directory parts corroborate, not the filename itself. The
        # last segment is the leaf file (e.g. `http.go`); using its stem as
        # corroboration would let any import path that happens to contain
        # "http" elsewhere (e.g. `net/http/httptest`) bind to this file.
        # That self-corroboration is exactly the false-positive the
        # path-segment constraint is supposed to kill. Use kebab↔snake
        # normalisation on directory names so Rust crate-name conventions
        # still match.
        parts_lower: set[str] = set()
        for part in rel.parts[:-1]:
            p_lower = part.lower()
            parts_lower.add(p_lower)
            parts_lower.add(p_lower.replace("-", "_"))
        normalized_other = {s.replace("-", "_") for s in other_segments_lower}
        return bool((other_segments_lower | normalized_other) & parts_lower)

    def try_index(idx: dict[str, list[Path]]) -> Path | None:
        for seg in reversed(segments):
            key = seg.lower()
            if not key:
                continue
            candidates = idx.get(key)
            if not candidates:
                continue
            filtered = [c for c in candidates if has_corroborating_segment(c)]
            if not filtered:
                continue
            candidates_sorted = sorted(filtered, key=proximity)
            chosen = candidates_sorted[0]
            if chosen == source_file:
                chosen = candidates_sorted[1] if len(candidates_sorted) > 1 else None
            if chosen is not None:
                return chosen
        return None

    # Stem match is high confidence (a file literally named like the import).
    # Only fall back to parent-dir matches when no stem hits — package-style
    # imports like Go `"./pkg/twitch"` legitimately point at a directory, but
    # without a file named after it the best we can do is pick *some* file
    # inside, which is noisy.
    hit = try_index(stem_idx)
    if hit is not None:
        return hit
    return try_index(parent_idx)


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _resolve_js_path(base: Path, repo_root: Path) -> Path | None:
    if not _within(base, repo_root):
        return None
    candidates = [
        base,
        base.with_suffix(".ts"), base.with_suffix(".tsx"),
        base.with_suffix(".js"), base.with_suffix(".jsx"),
        base.with_suffix(".mjs"), base.with_suffix(".cjs"),
        base / "index.ts", base / "index.tsx",
        base / "index.js", base / "index.jsx",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


def _resolve_python_path(base: Path, repo_root: Path) -> Path | None:
    if not _within(base, repo_root):
        return None
    candidates = [base.with_suffix(".py"), base / "__init__.py"]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


# ---------------------------------------------------------------------------
# Tarjan SCC


def strongly_connected(graph: dict[Path, set[Path]]) -> list[list[Path]]:
    """Tarjan's algorithm. Returns list of SCCs (each a list of nodes)."""
    index_of: dict[Path, int] = {}
    lowlink: dict[Path, int] = {}
    on_stack: set[Path] = set()
    stack: list[Path] = []
    sccs: list[list[Path]] = []
    counter = [0]

    def strongconnect(v: Path) -> None:
        index_of[v] = counter[0]
        lowlink[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in graph.get(v, ()):
            if w not in index_of:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], index_of[w])
        if lowlink[v] == index_of[v]:
            comp: list[Path] = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                comp.append(w)
                if w == v:
                    break
            sccs.append(comp)

    sys.setrecursionlimit(max(10000, sys.getrecursionlimit()))
    for node in list(graph.keys()):
        if node not in index_of:
            strongconnect(node)
    return sccs


# ---------------------------------------------------------------------------
# Report rendering


def render_report(
    repo_root: Path,
    files: dict[Path, FileInfo],
    edges: dict[Path, set[Path]],
    fan_in: dict[Path, int],
    cycles: list[list[Path]],
    top_n: int,
    god_loc: int,
) -> str:
    total_files = len(files)
    total_edges = sum(len(v) for v in edges.values())

    def rel(p: Path) -> str:
        try:
            return str(p.relative_to(repo_root))
        except ValueError:
            return str(p)

    # Empty pass-through files (e.g. blank __init__.py) get high fan-in without holding real
    # code. Exclude them from hubs and god-modules so the report points at real targets.
    def has_body(f: FileInfo) -> bool:
        return f.loc > 0

    by_fan_in = sorted(
        (f for f in files.values() if has_body(f)),
        key=lambda f: (-fan_in.get(f.path, 0), -f.loc),
    )
    by_fan_out = sorted(files.values(), key=lambda f: (-len(edges.get(f.path, ())), -f.loc))
    god_modules = sorted(
        (f for f in files.values() if f.loc >= god_loc),
        key=lambda f: (-f.loc, -fan_in.get(f.path, 0)),
    )

    lines: list[str] = []
    lines.append(f"# Architectural Hotspots — `{repo_root}`")
    lines.append("")
    lines.append(
        f"Analyzed **{total_files}** source files, **{total_edges}** internal import edges. "
        "Edges count file-to-file imports inside the repo only; external/unresolved imports are dropped."
    )
    lines.append("")

    # Hubs
    lines.append("## Hubs — high fan-in")
    lines.append(
        "Many files depend on these. Hubs are often legitimate (core libraries, shared types). "
        "They become interesting when paired with god-size, grab-bag naming (`utils`, `helpers`, `common`), "
        "or high churn in git history."
    )
    lines.append("")
    lines.append("| File | Fan-in | LOC |")
    lines.append("|------|-------:|----:|")
    for f in by_fan_in[:top_n]:
        if fan_in.get(f.path, 0) == 0:
            break
        lines.append(f"| `{rel(f.path)}` | {fan_in.get(f.path, 0)} | {f.loc} |")
    lines.append("")

    # Tangles
    lines.append("## Tangles — high fan-out")
    lines.append(
        "These files reach into many corners of the repo. Often a sign of weak single-responsibility — "
        "the file is doing too many things, or is a coordination layer that should be split."
    )
    lines.append("")
    lines.append("| File | Fan-out | LOC |")
    lines.append("|------|--------:|----:|")
    for f in by_fan_out[:top_n]:
        if len(edges.get(f.path, ())) == 0:
            break
        lines.append(f"| `{rel(f.path)}` | {len(edges.get(f.path, ()))} | {f.loc} |")
    lines.append("")

    # God modules
    lines.append(f"## God modules — LOC ≥ {god_loc}")
    lines.append(
        "Large files concentrate too much responsibility in one place. "
        "Cross-reference with the Hubs table — a file that is both god-sized *and* a hub is a refactor priority."
    )
    lines.append("")
    if god_modules:
        lines.append("| File | LOC | Fan-in | Fan-out |")
        lines.append("|------|----:|-------:|--------:|")
        for f in god_modules[:top_n]:
            lines.append(
                f"| `{rel(f.path)}` | {f.loc} | {fan_in.get(f.path, 0)} | {len(edges.get(f.path, ()))} |"
            )
    else:
        lines.append("_None above threshold._")
    lines.append("")

    # Cycles
    real_cycles = [c for c in cycles if len(c) > 1]
    lines.append("## Cycles — strongly-connected components")
    lines.append(
        "Files inside a cycle cannot be understood, tested, or deployed independently. "
        "Cycles of size 2 often mean a missing seam (extract a third module both depend on); "
        "larger cycles usually signal a layering violation."
    )
    lines.append("")
    if real_cycles:
        for i, comp in enumerate(sorted(real_cycles, key=len, reverse=True), 1):
            lines.append(f"### Cycle {i} — {len(comp)} files")
            for p in sorted(comp):
                lines.append(f"- `{rel(p)}`")
            lines.append("")
    else:
        lines.append("_No cycles detected._")
        lines.append("")

    # Limitations
    lines.append("## Limitations")
    lines.append(
        "- Imports resolved by relative path (where possible) and basename match across the repo. "
        "Path aliases, dynamic imports, re-exports, and codegen are likely missed."
    )
    lines.append("- LOC counts non-blank lines; comments are not stripped.")
    lines.append("- External / third-party imports are not counted — only intra-repo coupling.")
    lines.append("- Treats each file as a node. Class- or function-level coupling is invisible here.")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main


def analyze(
    repo: Path,
    top_n: int,
    god_loc: int,
    sniff: bool = False,
    extra_exts: dict[str, str] | None = None,
) -> str:
    repo = repo.resolve()
    all_files = list_files(repo)
    src = source_files(all_files, sniff=sniff, extra_exts=extra_exts)
    aliases = load_path_aliases(repo)

    files: dict[Path, FileInfo] = {}
    for path, lang in src:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        files[path] = FileInfo(
            path=path,
            lang=lang,
            loc=count_loc(text),
            imports_raw=extract_imports(text, lang),
        )

    stem_idx, parent_idx = build_basename_index(
        [f.path for f in files.values()], repo
    )

    edges: dict[Path, set[Path]] = defaultdict(set)
    fan_in: dict[Path, int] = defaultdict(int)
    for info in files.values():
        for raw in info.imports_raw:
            target = resolve_import(
                raw, info.path, info.lang, stem_idx, parent_idx, repo, aliases=aliases
            )
            if target and target != info.path and target in files:
                if target not in edges[info.path]:
                    edges[info.path].add(target)
                    fan_in[target] += 1

    cycles = strongly_connected({p: edges.get(p, set()) for p in files})

    return render_report(repo, files, edges, fan_in, cycles, top_n=top_n, god_loc=god_loc)


def _parse_ext_arg(values: list[str] | None) -> dict[str, str]:
    """Parse repeated `--ext .foo=lang` arguments into a dict."""
    out: dict[str, str] = {}
    for raw in values or []:
        if "=" not in raw:
            print(f"error: --ext must look like '.foo=lang' (got: {raw})", file=sys.stderr)
            continue
        ext, lang = raw.split("=", 1)
        ext = ext.strip().lower()
        if not ext.startswith("."):
            ext = "." + ext
        out[ext] = lang.strip() or "generic"
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Surface architectural hotspots in a codebase.")
    parser.add_argument("repo", nargs="?", default=".", help="Path to repository root (default: cwd).")
    parser.add_argument("--top", type=int, default=15, help="Max rows per section (default: 15).")
    parser.add_argument("--god-loc", type=int, default=400, help="LOC threshold for god modules (default: 400).")
    parser.add_argument("--output", "-o", help="Write report to file instead of stdout.")
    parser.add_argument(
        "--ext", action="append", metavar=".EXT=LANG",
        help=(
            "Force a file extension to be parsed as a given language. "
            "Repeatable. LANG can be any of the precise tags (python, js, go, "
            "rust, java, c, ruby, csharp, php, swift, scala, qml, nix) or "
            "'generic' for the best-effort regex set. Example: --ext .foo=generic"
        ),
    )
    parser.add_argument(
        "--sniff", action="store_true",
        help=(
            "Aggressively try to parse files with unknown extensions if they "
            "look like text. Catches obscure languages at the cost of some "
            "false positives. Default off."
        ),
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo)
    if not repo.exists():
        print(f"error: path does not exist: {repo}", file=sys.stderr)
        return 2

    extra_exts = _parse_ext_arg(args.ext)
    report = analyze(
        repo, top_n=args.top, god_loc=args.god_loc,
        sniff=args.sniff, extra_exts=extra_exts,
    )
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
