"""Common helpers used across the app."""


def format_currency(value):
    return f"${value:,.2f}"

def format_percent(value):
    return f"{value * 100:.1f}%"

def parse_iso_date(s):
    from datetime import datetime
    return datetime.fromisoformat(s)

def slugify(s):
    return s.lower().replace(" ", "-")

def chunk(iterable, size):
    buf = []
    for item in iterable:
        buf.append(item)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf

def safe_get(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default)
    return d

def retry(fn, attempts=3):
    last = None
    for _ in range(attempts):
        try:
            return fn()
        except Exception as e:
            last = e
    raise last

def deep_merge(a, b):
    out = dict(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def truncate(s, n=80):
    return s if len(s) <= n else s[:n] + "..."

def normalize_phone(s):
    return "".join(c for c in s if c.isdigit())

def is_valid_email(s):
    return "@" in s and "." in s.split("@")[-1]

def days_between(a, b):
    return (b - a).days

def hours_between(a, b):
    return (b - a).total_seconds() / 3600

def humanize_bytes(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"

def flatten(items):
    out = []
    for i in items:
        if isinstance(i, list):
            out.extend(flatten(i))
        else:
            out.append(i)
    return out

def group_by(items, key):
    out = {}
    for i in items:
        out.setdefault(key(i), []).append(i)
    return out

def pick(d, keys):
    return {k: d[k] for k in keys if k in d}

def omit(d, keys):
    return {k: v for k, v in d.items() if k not in keys}

def first(iterable, predicate=lambda x: True, default=None):
    for x in iterable:
        if predicate(x):
            return x
    return default

def coalesce(*values):
    for v in values:
        if v is not None:
            return v
    return None

def is_blank(s):
    return s is None or not s.strip()

def title_case(s):
    return " ".join(w.capitalize() for w in s.split())

def camel_case(s):
    parts = s.replace("-", "_").split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])

def snake_case(s):
    import re
    return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower()

def env_bool(name, default=False):
    import os
    v = os.environ.get(name)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "on")

def hash_dict(d):
    import hashlib, json
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()

def csv_escape(s):
    if "," in s or '"' in s or "\n" in s:
        return '"' + s.replace('"', '""') + '"'
    return s

def html_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))

def trim_lines(s):
    return "\n".join(line.rstrip() for line in s.splitlines())

def dedupe(items):
    seen = set()
    out = []
    for i in items:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out

def partition(items, predicate):
    yes, no = [], []
    for i in items:
        (yes if predicate(i) else no).append(i)
    return yes, no

def take(items, n):
    return items[:n]

def drop(items, n):
    return items[n:]

def window(items, n):
    for i in range(len(items) - n + 1):
        yield items[i:i + n]

def zip_longest_fill(a, b, fill=None):
    n = max(len(a), len(b))
    a = list(a) + [fill] * (n - len(a))
    b = list(b) + [fill] * (n - len(b))
    return list(zip(a, b))

def split_chunks(items, n):
    size = max(1, len(items) // n)
    return [items[i:i + size] for i in range(0, len(items), size)]

def find_index(items, predicate):
    for i, x in enumerate(items):
        if predicate(x):
            return i
    return -1

def count_if(items, predicate):
    return sum(1 for x in items if predicate(x))

def any_match(items, predicate):
    return any(predicate(x) for x in items)

def all_match(items, predicate):
    return all(predicate(x) for x in items)
