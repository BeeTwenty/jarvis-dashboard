#!/usr/bin/env python3
"""Jarvis Dashboard v2 — Backend server with API proxy, system stats, and power features."""

import concurrent.futures
import json
import html as html_module
import os
import random
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

HOST = "0.0.0.0"
PORT = 8002
STATIC_DIR = Path(__file__).parent
ENV_FILE = STATIC_DIR / ".env"

# --- Load .env file ---
def load_env(path):
    if not path.exists():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

load_env(ENV_FILE)

# --- Service configs ---
QBIT_BASE = "http://localhost:8080/api/v2"
QBIT_USER = os.environ.get("QBIT_USER", "")
QBIT_PASS = os.environ.get("QBIT_PASS", "")
JELLYFIN_BASE = "http://localhost:8096"
JELLYFIN_API_KEY = os.environ.get("JELLYFIN_API_KEY", "")
MEDIA_PATH = os.environ.get("MEDIA_PATH", "/data/media")
WEATHER_CITY = os.environ.get("WEATHER_CITY", "")

# ═══════════════════════════════════════
#  qBittorrent
# ═══════════════════════════════════════
qbit_sid = None

def qbit_login():
    global qbit_sid
    try:
        data = urllib.parse.urlencode({"username": QBIT_USER, "password": QBIT_PASS}).encode()
        req = urllib.request.Request(f"{QBIT_BASE}/auth/login", data=data, method="POST")
        resp = urllib.request.urlopen(req, timeout=5)
        for header in resp.headers.get_all("Set-Cookie") or []:
            if "SID=" in header:
                qbit_sid = header.split("SID=")[1].split(";")[0]
                return True
    except Exception:
        pass
    return False

def qbit_request(path, method="GET", body=None, retry=True):
    global qbit_sid
    if not qbit_sid:
        qbit_login()
    url = f"{QBIT_BASE}{path}"
    try:
        req = urllib.request.Request(url, method=method)
        if qbit_sid:
            req.add_header("Cookie", f"SID={qbit_sid}")
        if body:
            req.data = body.encode() if isinstance(body, str) else body
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
        resp = urllib.request.urlopen(req, timeout=10)
        raw = resp.read().decode()
        if raw.strip():
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                # Some endpoints return plain text (e.g. "Ok.")
                return {"ok": True, "message": raw.strip()}
        return {"ok": True}
    except urllib.error.HTTPError as e:
        if e.code == 403 and retry:
            qbit_login()
            return qbit_request(path, method, body, retry=False)
        return {"error": f"qBittorrent returned {e.code}"}
    except Exception as e:
        return {"error": f"qBittorrent: {e}"}

# ═══════════════════════════════════════
#  Jellyfin
# ═══════════════════════════════════════
def jellyfin_request(path):
    sep = "&" if "?" in path else "?"
    url = f"{JELLYFIN_BASE}{path}{sep}api_key={JELLYFIN_API_KEY}"
    try:
        req = urllib.request.Request(url, method="GET")
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"Jellyfin returned {e.code}"}
    except Exception as e:
        return {"error": f"Jellyfin: {e}"}

# ═══════════════════════════════════════
#  System stats
# ═══════════════════════════════════════
def get_system_stats():
    result = {}
    try:
        with open("/proc/loadavg") as f:
            parts = f.read().split()
            result["cpu_load"] = [float(parts[0]), float(parts[1]), float(parts[2])]
        result["cpu_count"] = os.cpu_count() or 1
    except Exception:
        result["cpu_load"] = [0, 0, 0]
        result["cpu_count"] = 1
    try:
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith(("MemTotal:", "MemAvailable:")):
                    key, val = line.split(":")
                    info[key.strip()] = int(val.strip().split()[0])
        total = info.get("MemTotal", 1)
        avail = info.get("MemAvailable", 0)
        result["memory"] = {"total_kb": total, "available_kb": avail,
                            "used_percent": round((total - avail) / total * 100, 1)}
    except Exception:
        result["memory"] = {"total_kb": 0, "available_kb": 0, "used_percent": 0}
    try:
        usage = shutil.disk_usage("/")
        result["disk"] = {"total_gb": round(usage.total / 1073741824, 1),
                          "used_gb": round(usage.used / 1073741824, 1),
                          "free_gb": round(usage.free / 1073741824, 1),
                          "used_percent": round(usage.used / usage.total * 100, 1)}
    except Exception:
        result["disk"] = {"total_gb": 0, "used_gb": 0, "free_gb": 0, "used_percent": 0}
    try:
        with open("/proc/uptime") as f:
            secs = int(float(f.read().split()[0]))
            days, rem = divmod(secs, 86400)
            hours, rem = divmod(rem, 3600)
            mins = rem // 60
            parts = []
            if days: parts.append(f"{days}d")
            if hours: parts.append(f"{hours}h")
            parts.append(f"{mins}m")
            result["uptime_seconds"] = secs
            result["uptime_human"] = " ".join(parts)
    except Exception:
        result["uptime_seconds"] = 0
        result["uptime_human"] = "unknown"
    return result

# ═══════════════════════════════════════
#  Docker
# ═══════════════════════════════════════
def get_docker_containers():
    try:
        r = subprocess.run(["docker", "ps", "-a", "--format", "{{json .}}"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return {"error": f"docker ps failed: {r.stderr.strip()}"}
        return [json.loads(l) for l in r.stdout.strip().split("\n") if l.strip()]
    except subprocess.TimeoutExpired:
        return {"error": "docker ps timed out"}
    except Exception as e:
        return {"error": str(e)}

def get_docker_stats():
    try:
        r = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{json .}}"],
                           capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return {"error": f"docker stats failed: {r.stderr.strip()}"}
        return [json.loads(l) for l in r.stdout.strip().split("\n") if l.strip()]
    except subprocess.TimeoutExpired:
        return {"error": "docker stats timed out"}
    except Exception as e:
        return {"error": str(e)}

SAFE_CONTAINER_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.\-]+$')
ALLOWED_DOCKER_ACTIONS = {"start", "stop", "restart"}

def docker_action(container, action):
    if action not in ALLOWED_DOCKER_ACTIONS:
        return {"error": f"Invalid action: {action}"}
    if not SAFE_CONTAINER_RE.match(container):
        return {"error": f"Invalid container name: {container}"}
    try:
        r = subprocess.run(["docker", action, container],
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return {"error": r.stderr.strip() or f"docker {action} failed"}
        return {"ok": True, "message": f"{container}: {action} successful"}
    except subprocess.TimeoutExpired:
        return {"error": f"docker {action} timed out"}
    except Exception as e:
        return {"error": str(e)}

def get_docker_logs(container, lines=100):
    if not SAFE_CONTAINER_RE.match(container):
        return {"error": "Invalid container name"}
    lines = max(1, min(int(lines), 500))
    try:
        r = subprocess.run(["docker", "logs", "--tail", str(lines), "--timestamps", container],
                           capture_output=True, text=True, timeout=10)
        combined = r.stdout + r.stderr
        return {"container": container, "logs": combined}
    except subprocess.TimeoutExpired:
        return {"error": "docker logs timed out"}
    except Exception as e:
        return {"error": str(e)}

# ═══════════════════════════════════════
#  Bandwidth history (background thread)
# ═══════════════════════════════════════
bw_history = []
bw_lock = threading.Lock()
BW_MAX = 360  # 30 min at 5s intervals

def _bw_collector():
    while True:
        try:
            data = qbit_request("/transfer/info")
            if data and not data.get("error"):
                entry = {"ts": time.time(),
                         "dl": data.get("dl_info_speed", 0),
                         "ul": data.get("up_info_speed", 0)}
                with bw_lock:
                    bw_history.append(entry)
                    if len(bw_history) > BW_MAX:
                        del bw_history[:len(bw_history) - BW_MAX]
        except Exception:
            pass
        time.sleep(5)

# ═══════════════════════════════════════
#  Process monitor
# ═══════════════════════════════════════
def get_processes():
    try:
        r = subprocess.run(["ps", "aux", "--sort=-%cpu"],
                           capture_output=True, text=True, timeout=5)
        lines = r.stdout.strip().split("\n")[1:11]  # top 10 by CPU
        by_cpu = []
        for line in lines:
            parts = line.split(None, 10)
            if len(parts) >= 11:
                by_cpu.append({"user": parts[0], "pid": int(parts[1]),
                               "cpu": float(parts[2]), "mem": float(parts[3]),
                               "command": parts[10][:80]})

        r2 = subprocess.run(["ps", "aux", "--sort=-%mem"],
                            capture_output=True, text=True, timeout=5)
        lines2 = r2.stdout.strip().split("\n")[1:11]
        by_mem = []
        for line in lines2:
            parts = line.split(None, 10)
            if len(parts) >= 11:
                by_mem.append({"user": parts[0], "pid": int(parts[1]),
                               "cpu": float(parts[2]), "mem": float(parts[3]),
                               "command": parts[10][:80]})
        return {"by_cpu": by_cpu, "by_mem": by_mem}
    except Exception as e:
        return {"error": str(e)}

# ═══════════════════════════════════════
#  Storage breakdown (cached)
# ═══════════════════════════════════════
storage_cache = {"data": None, "ts": 0}
STORAGE_TTL = 300  # 5 min

def get_storage():
    now = time.time()
    if storage_cache["data"] and (now - storage_cache["ts"]) < STORAGE_TTL:
        return storage_cache["data"]

    result = {"dirs": []}
    try:
        usage = shutil.disk_usage("/")
        result["total_gb"] = round(usage.total / 1073741824, 1)
        result["used_gb"] = round(usage.used / 1073741824, 1)
        result["free_gb"] = round(usage.free / 1073741824, 1)
    except Exception:
        result["total_gb"] = result["used_gb"] = result["free_gb"] = 0

    media = Path(MEDIA_PATH)
    if media.exists():
        for d in sorted(media.iterdir()):
            if d.is_dir():
                try:
                    r = subprocess.run(["du", "-sb", str(d)],
                                       capture_output=True, text=True, timeout=60)
                    if r.returncode == 0:
                        size = int(r.stdout.split()[0])
                        result["dirs"].append({"name": d.name, "size_bytes": size})
                except Exception:
                    pass

    # Also check /data/downloads if it exists
    dl = Path("/data/downloads")
    if dl.exists():
        try:
            r = subprocess.run(["du", "-sb", str(dl)],
                               capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                size = int(r.stdout.split()[0])
                result["dirs"].append({"name": "downloads", "size_bytes": size})
        except Exception:
            pass

    storage_cache["data"] = result
    storage_cache["ts"] = now
    return result

# ═══════════════════════════════════════
#  Weather (cached)
# ═══════════════════════════════════════
weather_cache = {"data": None, "ts": 0}
WEATHER_TTL = 900  # 15 min

def get_weather():
    now = time.time()
    if weather_cache["data"] and (now - weather_cache["ts"]) < WEATHER_TTL:
        return weather_cache["data"]
    try:
        url = f"https://wttr.in/{urllib.parse.quote(WEATHER_CITY)}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        raw = json.loads(resp.read().decode())
        cur = raw.get("current_condition", [{}])[0]
        result = {
            "temp_c": cur.get("temp_C", "?"),
            "feels_like": cur.get("FeelsLikeC", "?"),
            "condition": cur.get("weatherDesc", [{"value": "?"}])[0].get("value", "?"),
            "humidity": cur.get("humidity", "?"),
            "wind_kph": cur.get("windspeedKmph", "?"),
            "wind_dir": cur.get("winddir16Point", ""),
            "uv": cur.get("uvIndex", "?"),
            "visibility": cur.get("visibility", "?"),
            "city": WEATHER_CITY,
        }
        weather_cache["data"] = result
        weather_cache["ts"] = now
        return result
    except Exception as e:
        return {"error": str(e)}

# ═══════════════════════════════════════
#  Torrent search (apibay)
# ═══════════════════════════════════════
def search_torrents(query):
    try:
        url = f"https://apibay.org/q.php?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        results = json.loads(resp.read().decode())
        if not isinstance(results, list):
            return {"error": "Unexpected response"}
        # Filter out "No results" placeholder
        filtered = []
        for r in results[:20]:
            if r.get("id") == "0" or r.get("name") == "No results returned":
                continue
            filtered.append({
                "name": r.get("name", "Unknown"),
                "size": int(r.get("size", 0)),
                "seeders": int(r.get("seeders", 0)),
                "leechers": int(r.get("leechers", 0)),
                "info_hash": r.get("info_hash", ""),
                "added": r.get("added", ""),
                "category": r.get("category", ""),
            })
        # Sort by seeders
        filtered.sort(key=lambda x: x["seeders"], reverse=True)
        return filtered
    except Exception as e:
        return {"error": str(e)}

# ═══════════════════════════════════════
#  File Explorer
# ═══════════════════════════════════════
import mimetypes
import stat as stat_module

FILE_HOME = os.environ.get("FILE_HOME", os.path.expanduser("~"))

def _resolve_path(requested):
    """Resolve a path. Accepts absolute paths or relative-to-home paths."""
    requested = requested.strip()
    if not requested or requested == "~":
        return os.path.realpath(FILE_HOME)
    if requested.startswith("~"):
        requested = os.path.join(FILE_HOME, requested[1:].lstrip("/"))
    if not os.path.isabs(requested):
        requested = os.path.join(FILE_HOME, requested)
    return os.path.realpath(requested)

def file_list(rel_path):
    full = _resolve_path(rel_path)
    if not os.path.exists(full):
        return {"error": "Path not found"}
    if not os.path.isdir(full):
        return {"error": "Not a directory"}
    items = []
    try:
        for name in sorted(os.listdir(full), key=lambda n: (not os.path.isdir(os.path.join(full, n)), n.lower())):
            fp = os.path.join(full, name)
            try:
                st = os.stat(fp)
                items.append({
                    "name": name,
                    "is_dir": os.path.isdir(fp),
                    "size": st.st_size if not os.path.isdir(fp) else 0,
                    "modified": st.st_mtime,
                    "permissions": stat_module.filemode(st.st_mode),
                })
            except OSError:
                items.append({"name": name, "is_dir": False, "size": 0, "modified": 0, "permissions": "?"})
    except PermissionError:
        return {"error": "Permission denied"}
    return {"path": full, "items": items, "home": FILE_HOME}

def file_delete(rel_path):
    full = _resolve_path(rel_path)
    if not os.path.exists(full):
        return {"error": "Not found"}
    try:
        if os.path.isdir(full):
            shutil.rmtree(full)
        else:
            os.remove(full)
        return {"ok": True, "message": f"Deleted {os.path.basename(full)}"}
    except Exception as e:
        return {"error": str(e)}

def file_move(src_rel, dst_rel):
    src = _resolve_path(src_rel)
    dst = _resolve_path(dst_rel)
    if not os.path.exists(src):
        return {"error": "Source not found"}
    try:
        shutil.move(src, dst)
        return {"ok": True, "message": f"Moved to {os.path.basename(dst)}"}
    except Exception as e:
        return {"error": str(e)}

def file_copy(src_rel, dst_rel):
    src = _resolve_path(src_rel)
    dst = _resolve_path(dst_rel)
    if not os.path.exists(src):
        return {"error": "Source not found"}
    try:
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        return {"ok": True, "message": f"Copied to {os.path.basename(dst)}"}
    except Exception as e:
        return {"error": str(e)}

def file_mkdir(rel_path):
    full = _resolve_path(rel_path)
    try:
        os.makedirs(full, exist_ok=True)
        return {"ok": True, "message": f"Created {os.path.basename(full)}"}
    except Exception as e:
        return {"error": str(e)}

def file_rename(rel_path, new_name):
    full = _resolve_path(rel_path)
    if not os.path.exists(full):
        return {"error": "Not found"}
    if "/" in new_name or "\\" in new_name:
        return {"error": "Invalid name"}
    new_full = os.path.join(os.path.dirname(full), new_name)
    try:
        os.rename(full, new_full)
        return {"ok": True, "message": f"Renamed to {new_name}"}
    except Exception as e:
        return {"error": str(e)}

def file_download_path(rel_path):
    """Return the real path for streaming download, or None if invalid."""
    full = _resolve_path(rel_path)
    if not os.path.isfile(full):
        return None
    return full

# ═══════════════════════════════════════
#  Quick actions
# ═══════════════════════════════════════
def action_jellyfin_scan():
    try:
        url = f"{JELLYFIN_BASE}/Library/Refresh?api_key={JELLYFIN_API_KEY}"
        req = urllib.request.Request(url, method="POST")
        urllib.request.urlopen(req, timeout=10)
        return {"ok": True, "message": "Library scan started"}
    except Exception as e:
        return {"error": str(e)}

def action_clean_torrents():
    try:
        torrents = qbit_request("/torrents/info")
        if isinstance(torrents, dict) and torrents.get("error"):
            return torrents
        cleaned = []
        for t in torrents:
            if t.get("progress", 0) >= 1.0 and t.get("state", "") in ("pausedUP", "stalledUP", "uploading"):
                h = t.get("hash", "")
                if h:
                    qbit_request(f"/torrents/delete?hashes={h}&deleteFiles=false", method="POST")
                    cleaned.append(t.get("name", h))
        if cleaned:
            return {"ok": True, "message": f"Removed {len(cleaned)} completed: {', '.join(cleaned[:3])}{'...' if len(cleaned) > 3 else ''}"}
        return {"ok": True, "message": "No completed torrents to clean"}
    except Exception as e:
        return {"error": str(e)}

def action_docker_prune():
    try:
        r = subprocess.run(["docker", "system", "prune", "-f"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return {"error": r.stderr.strip()}
        return {"ok": True, "message": r.stdout.strip()[:200]}
    except Exception as e:
        return {"error": str(e)}

def action_update_check():
    try:
        subprocess.run(["apt", "update", "-qq"], capture_output=True, timeout=30)
        r = subprocess.run(["apt", "list", "--upgradable"],
                           capture_output=True, text=True, timeout=15)
        lines = [l for l in r.stdout.strip().split("\n") if "/" in l]
        if lines:
            return {"ok": True, "message": f"{len(lines)} packages upgradable", "packages": lines[:20]}
        return {"ok": True, "message": "System is up to date"}
    except Exception as e:
        return {"error": str(e)}

# ═══════════════════════════════════════
#  Recommendations (Reddit wiki knowledge base)
# ═══════════════════════════════════════
reco_cache = {}
RECO_TTL = 86400  # 24 hours

# In-memory knowledge base: {"category_name": [{"title":..., "year":..., "tmdb_id":..., "tmdb_url":...}, ...]}
_wiki_kb = {"categories": {}, "top100": [], "ts": 0}
_wiki_kb_lock = threading.Lock()
_WIKI_KB_TTL = 86400  # 24 hours

def _reddit_wiki_json(page, timeout=20):
    """Fetch a Reddit wiki page via old.reddit.com JSON endpoint."""
    url = f"https://old.reddit.com/r/MovieSuggestions/wiki/{page}.json"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json,text/html,*/*",
        "Accept-Language": "en-US,en;q=0.5",
    })
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode("utf-8", errors="replace"))

def _parse_wiki_movies(content_md):
    """Parse wiki markdown content to extract movies organized by category.
    Wiki format has markdown tables with entries like:
    [Movie Name (Year)](https://www.themoviedb.org/movie/ID)|
    Returns dict of {category: [movie_dict, ...]}
    """
    categories = {}
    current_category = None

    # Regex for movie entries: [Title (Year)](tmdb_url)
    movie_re = re.compile(
        r'\[([^\]]+?)\s*\((\d{4})\)\]\((https?://(?:www\.)?themoviedb\.org/(?:movie|tv)/(\d+)[^)]*)\)'
    )
    # Regex for section headers (# or ## or ### etc)
    header_re = re.compile(r'^(#{1,4})\s*(.+)')

    current_top_category = None
    # Split by lines to track current category via headers
    for line in content_md.split('\n'):
        header_match = header_re.match(line.strip())
        if header_match:
            level = len(header_match.group(1))
            name = header_match.group(2).strip().rstrip('#').strip()
            # Clean up category name — remove markdown links/formatting
            name = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', name)
            name = re.sub(r'[*_`]', '', name).strip()
            if not name:
                continue
            if level == 1:
                current_top_category = name
                current_category = name
            else:
                current_category = f"{current_top_category} > {name}" if current_top_category else name
            if current_category not in categories:
                categories[current_category] = []
            continue

        # Find all movie entries in this line
        for match in movie_re.finditer(line):
            title = match.group(1).strip()
            year = match.group(2)
            tmdb_url = match.group(3)
            tmdb_id = match.group(4)

            # Clean title of any remaining markdown
            title = re.sub(r'[*_`]', '', title).strip()
            # Determine type from URL
            media_type = "series" if "/tv/" in tmdb_url else "movie"

            entry = {
                "title": title,
                "year": year,
                "type": media_type,
                "tmdb_id": tmdb_id,
                "tmdb_url": tmdb_url,
                "category": current_category or "Uncategorized",
                "torrent_query": f"{title} {year}".strip(),
            }

            if current_category and current_category in categories:
                categories[current_category].append(entry)
            else:
                categories.setdefault("Uncategorized", []).append(entry)

    return categories

def _parse_top100_movies(content_md):
    """Parse a top100 monthly wiki page. Returns list of movie dicts.
    Format: | 1 | Parasite (2019) | -- |  OR  [Title (Year)](tmdb_url)
    """
    movies = []
    seen = set()

    # Pattern 1: TMDB links [Title (Year)](tmdb_url)
    tmdb_re = re.compile(
        r'\[([^\]]+?)\s*\((\d{4})\)\]\((https?://(?:www\.)?themoviedb\.org/(?:movie|tv)/(\d+)[^)]*)\)'
    )
    # Pattern 2: Table rows like | 1 | Title (Year) | ... |
    table_re = re.compile(
        r'\|\s*\d+\s*\|\s*(.+?)\s*\((\d{4})\)\s*\|'
    )

    for line in content_md.split('\n'):
        # Try TMDB link pattern first
        for match in tmdb_re.finditer(line):
            title = re.sub(r'[*_`]', '', match.group(1)).strip()
            year = match.group(2)
            tmdb_url = match.group(3)
            tmdb_id = match.group(4)
            media_type = "series" if "/tv/" in tmdb_url else "movie"
            key = title.lower()
            if key not in seen:
                seen.add(key)
                movies.append({
                    "title": title, "year": year, "type": media_type,
                    "tmdb_id": tmdb_id, "tmdb_url": tmdb_url,
                    "category": "Trending",
                    "torrent_query": f"{title} {year}".strip(),
                })

        # Try table row pattern (no TMDB links)
        for match in table_re.finditer(line):
            title = re.sub(r'[*_`]', '', match.group(1)).strip()
            year = match.group(2)
            key = title.lower()
            if key not in seen:
                seen.add(key)
                movies.append({
                    "title": title, "year": year, "type": "movie",
                    "tmdb_id": "", "tmdb_url": "",
                    "category": "Trending",
                    "torrent_query": f"{title} {year}".strip(),
                })
    return movies

def _get_top100_page_names():
    """Generate the latest 3 monthly top100 page names to fetch."""
    import datetime
    now = datetime.datetime.now()
    months = []
    for offset in range(3):
        dt = now - datetime.timedelta(days=30 * offset)
        month_name = dt.strftime("%B").lower()
        year = dt.year
        months.append(f"meta/top100/{month_name}{year}")
    return months

def _load_wiki_knowledge_base():
    """Fetch and cache the Reddit wiki knowledge base. Thread-safe."""
    now = time.time()
    with _wiki_kb_lock:
        if _wiki_kb["ts"] and (now - _wiki_kb["ts"]) < _WIKI_KB_TTL and _wiki_kb["categories"]:
            return  # Still fresh

    categories = {}
    top100 = []

    # Fetch frequently_requested wiki page
    try:
        data = _reddit_wiki_json("frequently_requested")
        content = data.get("data", {}).get("content_md", "") or data.get("data", {}).get("content_html", "")
        if not content:
            # Try alternate key
            content = data.get("data", {}).get("body", "") or data.get("data", {}).get("body_md", "")
        if content:
            categories = _parse_wiki_movies(content)
    except Exception as e:
        print(f"[Reco] Failed to fetch frequently_requested wiki: {e}")

    # Fetch horror FAQ
    try:
        data = _reddit_wiki_json("faq/horror")
        content = data.get("data", {}).get("content_md", "") or data.get("data", {}).get("content_html", "")
        if not content:
            content = data.get("data", {}).get("body", "") or data.get("data", {}).get("body_md", "")
        if content:
            horror_cats = _parse_wiki_movies(content)
            for cat, movies in horror_cats.items():
                cat_key = f"Horror - {cat}" if cat != "Uncategorized" else "Horror (FAQ)"
                categories[cat_key] = movies
    except Exception:
        pass

    # Fetch latest top100 lists
    for page_name in _get_top100_page_names():
        try:
            data = _reddit_wiki_json(page_name)
            content = data.get("data", {}).get("content_md", "") or data.get("data", {}).get("content_html", "")
            if not content:
                content = data.get("data", {}).get("body", "") or data.get("data", {}).get("body_md", "")
            if content:
                movies = _parse_top100_movies(content)
                top100.extend(movies)
        except Exception:
            pass  # Monthly page might not exist yet

    # Deduplicate top100
    seen = set()
    deduped_top100 = []
    for m in top100:
        key = m["title"].lower()
        if key not in seen:
            seen.add(key)
            deduped_top100.append(m)

    with _wiki_kb_lock:
        _wiki_kb["categories"] = categories
        _wiki_kb["top100"] = deduped_top100
        _wiki_kb["ts"] = time.time()

    total_movies = sum(len(v) for v in categories.values())
    print(f"[Reco] Wiki KB loaded: {len(categories)} categories, {total_movies} movies, {len(deduped_top100)} top100 entries")

def _get_wiki_kb():
    """Get the wiki knowledge base, loading it if needed. Returns (categories_dict, top100_list)."""
    _load_wiki_knowledge_base()
    with _wiki_kb_lock:
        return _wiki_kb["categories"], _wiki_kb["top100"]

def _enrich_with_tmdb(results, max_items=20):
    """Enrich recommendation results with TMDB posters and ratings using parallel fetches."""
    def _fetch_poster(movie):
        m = dict(movie)
        if m.get("tmdb_id") and not m.get("poster"):
            try:
                t = "tv" if m.get("type") == "series" else "movie"
                data = _tmdb_fetch(f"/{t}/{m['tmdb_id']}")
                if data:
                    if data.get("poster_path"):
                        m["poster"] = f"https://image.tmdb.org/t/p/w300{data['poster_path']}"
                    if data.get("vote_average"):
                        m["rating"] = round(data["vote_average"], 1)
                    if data.get("overview") and not m.get("description"):
                        m["description"] = data["overview"][:150]
            except Exception:
                pass
        return m

    items = results[:max_items]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        enriched = list(pool.map(_fetch_poster, items))
    return enriched

def _google_search_titles(query, num=10, timeout=15):
    """Search Google for movie/series recommendations and extract titles (fallback)."""
    results = []
    seen = set()
    try:
        search_url = f"https://www.google.com/search?q={urllib.parse.quote(query + ' site:reddit.com')}&num={num}"
        req = urllib.request.Request(search_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.5",
        })
        resp = urllib.request.urlopen(req, timeout=timeout)
        html_text = resp.read().decode("utf-8", errors="replace")

        title_year_re = re.findall(r'([A-Z][A-Za-z0-9\s\':&,!.\-]{2,40})\s*\((\d{4})\)', html_text)
        for name, year in title_year_re:
            name = name.strip().rstrip(" -\u2013,.")
            if len(name) < 2 or name.lower() in seen:
                continue
            if any(skip in name.lower() for skip in ["reddit", "imdb", "http", "edit", "update", "thread", "spoiler", "anyone", "looking for", "suggest", "recommend", "google", "search"]):
                continue
            seen.add(name.lower())
            results.append({"title": name, "year": year, "type": "movie", "category": "", "tmdb_id": "", "tmdb_url": "", "torrent_query": f"{name} {year}".strip()})
    except Exception:
        pass
    return results

# Mood-to-wiki-category mapping
MOOD_CATEGORY_MAP = {
    "feel-good": ["Comedy", "Romance", "Animation", "Adventure", "Family", "Musical"],
    "thriller": ["Thriller", "Crime", "Suspense", "Psychological Thriller", "Crime Thriller"],
    "mind-bending": ["Mystery", "Sci-Fi", "Psychological", "Puzzle", "Science Fiction", "Surreal"],
    "comfort": ["Comedy", "Romance", "Animation", "Family", "Adventure", "Feel-Good"],
    "dark": ["Crime", "Thriller", "Drama", "Noir", "Psychological", "Dark Comedy"],
    "funny": ["Comedy", "Dark Comedy", "Parody", "Satire", "Slapstick"],
    "romantic": ["Romance", "Romantic Comedy", "Rom-Com", "Drama", "Love"],
    "action-packed": ["Action", "Military", "Martial Arts", "Heist", "Spy", "War"],
    "sci-fi": ["Sci-Fi", "Science Fiction", "Cyberpunk", "Space", "Dystopia", "Time Travel"],
    "horror": ["Horror", "Slasher", "Supernatural", "Zombie", "Gothic", "Psychological Horror"],
    "documentary": ["Documentary", "True Crime", "History", "Biography"],
    "animated": ["Animation", "Animated", "Anime", "Pixar", "Disney"],
}

def _match_categories(keywords, categories_dict):
    """Find wiki categories that match any of the given keywords (case-insensitive substring match).
    Returns list of matching category names."""
    matched = []
    for kw in keywords:
        kw_lower = kw.lower()
        for cat_name in categories_dict:
            if cat_name in matched:
                continue
            if kw_lower in cat_name.lower() or cat_name.lower() in kw_lower:
                matched.append(cat_name)
    return matched

def get_recommendations_mood(mood):
    """Get recommendations for a given mood using wiki knowledge base."""
    cache_key = f"mood:{mood}"
    now = time.time()
    if cache_key in reco_cache and (now - reco_cache[cache_key]["ts"]) < RECO_TTL:
        return reco_cache[cache_key]["data"]

    categories, _ = _get_wiki_kb()

    # Map mood to category keywords
    mood_lower = mood.lower().strip()
    cat_keywords = MOOD_CATEGORY_MAP.get(mood_lower, [mood_lower])

    # Find matching categories
    matched_cats = _match_categories(cat_keywords, categories)

    # If no exact match, try fuzzy: search all category names for any word in the mood
    if not matched_cats:
        mood_words = mood_lower.replace("-", " ").split()
        for word in mood_words:
            if len(word) < 3:
                continue
            for cat_name in categories:
                if word in cat_name.lower() and cat_name not in matched_cats:
                    matched_cats.append(cat_name)

    # Collect movies from matched categories
    all_movies = []
    seen = set()
    for cat_name in matched_cats:
        for movie in categories.get(cat_name, []):
            key = movie["title"].lower()
            if key not in seen:
                seen.add(key)
                all_movies.append(movie)

    # Shuffle and limit to 20
    random.shuffle(all_movies)
    results = all_movies[:20]

    # If we got nothing from the wiki, fall back to Google search
    if not results:
        fallback = _google_search_titles(f"{mood} movies recommendations reddit")
        results = fallback[:20]

    # Enrich with TMDB posters and ratings
    results = _enrich_with_tmdb(results, max_items=20)

    result = {"mood": mood, "matched_categories": matched_cats, "results": results}
    reco_cache[cache_key] = {"data": result, "ts": now}
    return result

def _tmdb_search_similar(title):
    """Search TMDB for a title and return similar movies/series from TMDB API."""
    tmdb_results = []
    seen_tmdb = set()

    # Try movie search
    movie_search = _tmdb_fetch(f"/search/movie?query={urllib.parse.quote(title)}")
    if movie_search.get("results"):
        movie_id = movie_search["results"][0].get("id")
        if movie_id:
            similar = _tmdb_fetch(f"/movie/{movie_id}/similar")
            for s in similar.get("results", [])[:15]:
                s_title = s.get("title", "")
                key = s_title.lower()
                if key and key not in seen_tmdb:
                    seen_tmdb.add(key)
                    year = (s.get("release_date") or "")[:4]
                    poster = f"https://image.tmdb.org/t/p/w500{s['poster_path']}" if s.get("poster_path") else ""
                    tmdb_results.append({
                        "title": s_title,
                        "year": year,
                        "type": "movie",
                        "description": (s.get("overview") or "")[:200],
                        "rating": str(round(s.get("vote_average", 0), 1)),
                        "poster": poster,
                        "tmdb_id": str(s.get("id", "")),
                        "torrent_query": f"{s_title} {year}".strip(),
                    })

    # Try TV search
    tv_search = _tmdb_fetch(f"/search/tv?query={urllib.parse.quote(title)}")
    if tv_search.get("results"):
        tv_id = tv_search["results"][0].get("id")
        if tv_id:
            similar = _tmdb_fetch(f"/tv/{tv_id}/similar")
            for s in similar.get("results", [])[:15]:
                s_title = s.get("name", "")
                key = s_title.lower()
                if key and key not in seen_tmdb:
                    seen_tmdb.add(key)
                    year = (s.get("first_air_date") or "")[:4]
                    poster = f"https://image.tmdb.org/t/p/w500{s['poster_path']}" if s.get("poster_path") else ""
                    tmdb_results.append({
                        "title": s_title,
                        "year": year,
                        "type": "series",
                        "description": (s.get("overview") or "")[:200],
                        "rating": str(round(s.get("vote_average", 0), 1)),
                        "poster": poster,
                        "tmdb_id": str(s.get("id", "")),
                        "torrent_query": f"{s_title} {year}".strip(),
                    })

    return tmdb_results, seen_tmdb


def get_recommendations_similar(title):
    """Find similar movies/series using TMDB API + wiki KB."""
    cache_key = f"similar:{title.lower().strip()}"
    now = time.time()
    if cache_key in reco_cache and (now - reco_cache[cache_key]["ts"]) < RECO_TTL:
        return reco_cache[cache_key]["data"]

    # 1. Get TMDB similar results
    tmdb_results, seen_tmdb = _tmdb_search_similar(title)

    # 2. Get wiki KB results
    categories, top100 = _get_wiki_kb()
    title_lower = title.lower().strip()

    found_categories = []
    for cat_name, movies in categories.items():
        for movie in movies:
            if movie["title"].lower() == title_lower or title_lower in movie["title"].lower():
                if cat_name not in found_categories:
                    found_categories.append(cat_name)

    for movie in top100:
        if movie["title"].lower() == title_lower or title_lower in movie["title"].lower():
            if "Trending" not in found_categories:
                found_categories.append("Trending")

    wiki_movies = []
    seen = {title_lower} | seen_tmdb

    for cat_name in found_categories:
        cat_movies = categories.get(cat_name, [])
        for movie in cat_movies:
            key = movie["title"].lower()
            if key not in seen:
                seen.add(key)
                wiki_movies.append(movie)

    random.shuffle(wiki_movies)

    # 3. Merge: TMDB first, then wiki KB
    results = tmdb_results + wiki_movies

    # Fallback to Google search if nothing found
    if not results:
        fallback = _google_search_titles(f"movies similar to {title} recommendations reddit")
        results = fallback[:20]

    results = results[:30]

    result = {"query": title, "matched_categories": found_categories, "results": results}
    reco_cache[cache_key] = {"data": result, "ts": now}
    return result

# TMDB genre name -> ID mapping for discover endpoint
_TMDB_GENRE_MAP = {
    "action": 28, "adventure": 12, "animation": 16, "comedy": 35, "crime": 80,
    "documentary": 99, "drama": 18, "family": 10751, "fantasy": 14, "history": 36,
    "horror": 27, "music": 10402, "mystery": 9648, "romance": 10749,
    "science fiction": 878, "sci-fi": 878, "thriller": 53, "war": 10752, "western": 37,
    "tv movie": 10770,
}


def _tmdb_get_recommendations_for_item(title, media_type="movie"):
    """Search TMDB for a library item and return its recommendations."""
    kind = "tv" if media_type in ("series", "tv") else "movie"
    search = _tmdb_fetch(f"/search/{kind}?query={urllib.parse.quote(title)}")
    if not search.get("results"):
        return []
    tmdb_id = search["results"][0].get("id")
    if not tmdb_id:
        return []
    recs = _tmdb_fetch(f"/{kind}/{tmdb_id}/recommendations")
    results = []
    for s in recs.get("results", [])[:10]:
        s_title = s.get("title") or s.get("name", "")
        year = (s.get("release_date") or s.get("first_air_date") or "")[:4]
        poster = f"https://image.tmdb.org/t/p/w300{s['poster_path']}" if s.get("poster_path") else ""
        s_type = "series" if kind == "tv" else "movie"
        genre_ids = s.get("genre_ids", [])
        results.append({
            "title": s_title, "year": year, "type": s_type,
            "description": (s.get("overview") or "")[:200],
            "rating": str(round(s.get("vote_average", 0), 1)),
            "poster": poster,
            "tmdb_id": str(s.get("id", "")),
            "torrent_query": f"{s_title} {year}".strip(),
            "genre_ids": genre_ids,
        })
    return results


def _tmdb_discover_by_genres(genre_ids, media_type="movie", page=1):
    """Use TMDB discover endpoint to find movies/TV by genre IDs."""
    kind = "tv" if media_type in ("series", "tv") else "movie"
    genres_str = ",".join(str(g) for g in genre_ids)
    data = _tmdb_fetch(f"/discover/{kind}?with_genres={genres_str}&sort_by=vote_average.desc&vote_count.gte=100&page={page}")
    results = []
    for s in data.get("results", [])[:20]:
        s_title = s.get("title") or s.get("name", "")
        year = (s.get("release_date") or s.get("first_air_date") or "")[:4]
        poster = f"https://image.tmdb.org/t/p/w300{s['poster_path']}" if s.get("poster_path") else ""
        s_type = "series" if kind == "tv" else "movie"
        results.append({
            "title": s_title, "year": year, "type": s_type,
            "description": (s.get("overview") or "")[:200],
            "rating": str(round(s.get("vote_average", 0), 1)),
            "poster": poster,
            "tmdb_id": str(s.get("id", "")),
            "torrent_query": f"{s_title} {year}".strip(),
            "genre_ids": s.get("genre_ids", []),
        })
    return results


def get_recommendations_library():
    """Analyze Jellyfin library and recommend using TMDB API."""
    cache_key = "library"
    now = time.time()
    if cache_key in reco_cache and (now - reco_cache[cache_key]["ts"]) < RECO_TTL:
        return reco_cache[cache_key]["data"]

    # Get Jellyfin library items
    genres = []
    library_titles = set()
    library_items_raw = []  # (title, type, genres)
    try:
        users_data = jellyfin_request("/Users")
        user_id = ""
        if isinstance(users_data, list) and users_data:
            user_id = users_data[0].get("Id", "")

        if user_id:
            movies = jellyfin_request(f"/Users/{user_id}/Items?IncludeItemTypes=Movie&Limit=50&SortBy=DatePlayed&SortOrder=Descending&Recursive=true")
            if isinstance(movies, dict) and "Items" in movies:
                for item in movies["Items"]:
                    name = item.get("Name", "")
                    library_titles.add(name.lower())
                    item_genres = item.get("Genres", [])
                    for g in item_genres:
                        genres.append(g)
                    library_items_raw.append({"title": name, "type": "movie", "genres": item_genres})

            series = jellyfin_request(f"/Users/{user_id}/Items?IncludeItemTypes=Series&Limit=30&SortBy=DatePlayed&SortOrder=Descending&Recursive=true")
            if isinstance(series, dict) and "Items" in series:
                for item in series["Items"]:
                    name = item.get("Name", "")
                    library_titles.add(name.lower())
                    item_genres = item.get("Genres", [])
                    for g in item_genres:
                        genres.append(g)
                    library_items_raw.append({"title": name, "type": "series", "genres": item_genres})
    except Exception:
        pass

    if not genres:
        genres = ["Action", "Drama", "Thriller", "Comedy", "Sci-Fi"]

    # Count top genres
    genre_count = {}
    for g in genres:
        genre_count[g] = genre_count.get(g, 0) + 1
    top_genres = sorted(genre_count.keys(), key=lambda g: genre_count[g], reverse=True)[:5]

    # Enrich library items with TMDB posters (parallel)
    def _enrich_library_item(item):
        kind = "tv" if item["type"] == "series" else "movie"
        search = _tmdb_fetch(f"/search/{kind}?query={urllib.parse.quote(item['title'])}")
        if search.get("results"):
            first = search["results"][0]
            poster = f"https://image.tmdb.org/t/p/w300{first['poster_path']}" if first.get("poster_path") else ""
            year = (first.get("release_date") or first.get("first_air_date") or "")[:4]
            return {
                "title": item["title"], "year": year, "type": item["type"],
                "poster": poster,
                "tmdb_id": str(first.get("id", "")),
                "rating": str(round(first.get("vote_average", 0), 1)),
                "description": (first.get("overview") or "")[:150],
                "genres": item["genres"],
                "torrent_query": f"{item['title']} {year}".strip(),
            }
        return {
            "title": item["title"], "year": "", "type": item["type"],
            "poster": "", "tmdb_id": "", "rating": "", "description": "",
            "genres": item["genres"], "torrent_query": item["title"],
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        library_items = list(pool.map(_enrich_library_item, library_items_raw[:40]))

    # Get TMDB recommendations based on random sample of library items
    sample_items = random.sample(library_items_raw, min(6, len(library_items_raw)))
    suggestions = []
    seen = set(library_titles)

    def _get_recs(item):
        return _tmdb_get_recommendations_for_item(item["title"], item["type"])

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        all_recs = list(pool.map(_get_recs, sample_items))

    for recs in all_recs:
        for rec in recs:
            key = rec["title"].lower()
            if key not in seen:
                seen.add(key)
                suggestions.append(rec)

    # Also use TMDB discover with top genre IDs as supplementary
    tmdb_genre_ids = []
    for g in top_genres[:3]:
        g_lower = g.lower()
        if g_lower in _TMDB_GENRE_MAP:
            tmdb_genre_ids.append(_TMDB_GENRE_MAP[g_lower])

    if tmdb_genre_ids:
        discover_results = _tmdb_discover_by_genres(tmdb_genre_ids, "movie")
        for rec in discover_results:
            key = rec["title"].lower()
            if key not in seen:
                seen.add(key)
                suggestions.append(rec)

    random.shuffle(suggestions)
    suggestions = suggestions[:30]

    result = {
        "genres": top_genres,
        "library_count": len(library_titles),
        "library_items": library_items,
        "suggestions": suggestions,
    }
    reco_cache[cache_key] = {"data": result, "ts": now}
    return result

def get_recommendations_trending(time_window="week"):
    """Get trending movies and TV from TMDB trending API."""
    cache_key = f"trending:{time_window}"
    now = time.time()
    if cache_key in reco_cache and (now - reco_cache[cache_key]["ts"]) < RECO_TTL:
        return reco_cache[cache_key]["data"]

    results = []
    seen = set()

    # Fetch trending movies and TV in parallel
    def _fetch_trending_movies():
        return _tmdb_fetch(f"/trending/movie/{time_window}")

    def _fetch_trending_tv():
        return _tmdb_fetch(f"/trending/tv/{time_window}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f_movies = pool.submit(_fetch_trending_movies)
        f_tv = pool.submit(_fetch_trending_tv)

    for item in f_movies.result().get("results", [])[:20]:
        title = item.get("title", "")
        key = title.lower()
        if key and key not in seen:
            seen.add(key)
            year = (item.get("release_date") or "")[:4]
            poster = f"https://image.tmdb.org/t/p/w300{item['poster_path']}" if item.get("poster_path") else ""
            results.append({
                "title": title, "year": year, "type": "movie",
                "description": (item.get("overview") or "")[:200],
                "rating": str(round(item.get("vote_average", 0), 1)),
                "poster": poster,
                "tmdb_id": str(item.get("id", "")),
                "torrent_query": f"{title} {year}".strip(),
                "genre_ids": item.get("genre_ids", []),
            })

    for item in f_tv.result().get("results", [])[:20]:
        title = item.get("name", "")
        key = title.lower()
        if key and key not in seen:
            seen.add(key)
            year = (item.get("first_air_date") or "")[:4]
            poster = f"https://image.tmdb.org/t/p/w300{item['poster_path']}" if item.get("poster_path") else ""
            results.append({
                "title": title, "year": year, "type": "series",
                "description": (item.get("overview") or "")[:200],
                "rating": str(round(item.get("vote_average", 0), 1)),
                "poster": poster,
                "tmdb_id": str(item.get("id", "")),
                "torrent_query": f"{title} {year}".strip(),
                "genre_ids": item.get("genre_ids", []),
            })

    result = {"results": results, "time_window": time_window}
    reco_cache[cache_key] = {"data": result, "ts": now}
    return result

def get_recommendations_categories():
    """Return list of available categories from the wiki knowledge base."""
    cache_key = "categories_list"
    now = time.time()
    if cache_key in reco_cache and (now - reco_cache[cache_key]["ts"]) < RECO_TTL:
        return reco_cache[cache_key]["data"]

    categories, _ = _get_wiki_kb()

    cat_list = []
    for cat_name, movies in sorted(categories.items()):
        cat_list.append({"name": cat_name, "count": len(movies)})

    result = {"categories": cat_list, "total_movies": sum(c["count"] for c in cat_list)}
    reco_cache[cache_key] = {"data": result, "ts": now}
    return result


def get_recommendations_autocomplete(query):
    """Search the in-memory wiki KB for titles containing the query string (case-insensitive)."""
    if not query or len(query) < 2:
        return {"results": []}

    categories, top100 = _get_wiki_kb()
    query_lower = query.lower().strip()

    results = []
    seen = set()

    # Search all categories
    for cat_name, movies in categories.items():
        for movie in movies:
            key = movie["title"].lower()
            if query_lower in key and key not in seen:
                seen.add(key)
                results.append({
                    "title": movie["title"],
                    "year": movie.get("year", ""),
                    "tmdb_id": movie.get("tmdb_id", ""),
                    "type": movie.get("type", "movie"),
                })
            if len(results) >= 10:
                break
        if len(results) >= 10:
            break

    # Also search top100 if we need more
    if len(results) < 10:
        for movie in top100:
            key = movie["title"].lower()
            if query_lower in key and key not in seen:
                seen.add(key)
                results.append({
                    "title": movie["title"],
                    "year": movie.get("year", ""),
                    "tmdb_id": movie.get("tmdb_id", ""),
                    "type": movie.get("type", "movie"),
                })
            if len(results) >= 10:
                break

    return {"results": results[:10]}


_search_cache = {}
_SEARCH_TTL = 3600  # 1 hour

def get_recommendations_search(query):
    """Search TMDB multi search for movies and TV series."""
    if not query or len(query) < 2:
        return {"results": []}

    cache_key = f"search:{query.lower().strip()}"
    now = time.time()
    if cache_key in _search_cache and (now - _search_cache[cache_key]["ts"]) < _SEARCH_TTL:
        return _search_cache[cache_key]["data"]

    data = _tmdb_fetch(f"/search/multi?query={urllib.parse.quote(query)}&include_adult=false")
    results = []
    for item in data.get("results", []):
        media_type = item.get("media_type", "")
        if media_type not in ("movie", "tv"):
            continue

        if media_type == "movie":
            title = item.get("title", "")
            year = (item.get("release_date") or "")[:4]
            rtype = "movie"
        else:
            title = item.get("name", "")
            year = (item.get("first_air_date") or "")[:4]
            rtype = "series"

        if not title:
            continue

        poster = f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get("poster_path") else ""
        overview = (item.get("overview") or "")[:150]

        results.append({
            "title": title,
            "year": year,
            "tmdb_id": str(item.get("id", "")),
            "type": rtype,
            "poster": poster,
            "rating": round(item.get("vote_average", 0), 1),
            "overview": overview,
        })

        if len(results) >= 20:
            break

    result = {"results": results}
    _search_cache[cache_key] = {"data": result, "ts": now}
    return result


TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
TMDB_BASE = "https://api.themoviedb.org/3"
_detail_cache = {}
_DETAIL_TTL = 86400  # 24 hours


def _tmdb_fetch(endpoint, timeout=10):
    """Fetch a TMDB API endpoint. Returns parsed JSON or empty dict on error."""
    sep = "&" if "?" in endpoint else "?"
    url = f"{TMDB_BASE}{endpoint}{sep}api_key={TMDB_API_KEY}"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "JarvisDashboard/1.0",
            "Accept": "application/json",
        })
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"[TMDB] Error fetching {endpoint}: {e}")
        return {}


def get_recommendations_detail(tmdb_id, media_type="movie"):
    """Fetch full movie/series details from TMDB API with parallel requests."""
    cache_key = f"detail:{media_type}:{tmdb_id}"
    now = time.time()
    if cache_key in _detail_cache and (now - _detail_cache[cache_key]["ts"]) < _DETAIL_TTL:
        return _detail_cache[cache_key]["data"]

    kind = "tv" if media_type == "tv" or media_type == "series" else "movie"

    # Fetch details, credits, and similar in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        f_details = pool.submit(_tmdb_fetch, f"/{kind}/{tmdb_id}")
        f_credits = pool.submit(_tmdb_fetch, f"/{kind}/{tmdb_id}/credits")
        f_similar = pool.submit(_tmdb_fetch, f"/{kind}/{tmdb_id}/recommendations")

    details = f_details.result()
    credits = f_credits.result()
    similar_data = f_similar.result()

    if not details or "id" not in details:
        return {"error": "Movie/series not found on TMDB"}

    # Extract title (movies use "title", TV uses "name")
    title = details.get("title") or details.get("name") or ""
    release_date = details.get("release_date") or details.get("first_air_date") or ""
    year = release_date[:4] if release_date else ""

    # Extract director from crew
    director = ""
    for crew_member in credits.get("crew", []):
        if crew_member.get("job") == "Director":
            director = crew_member.get("name", "")
            break
    # For TV, use "created_by" if no director found
    if not director and kind == "tv":
        creators = details.get("created_by", [])
        if creators:
            director = creators[0].get("name", "")

    # Build cast list (top 10)
    cast = []
    for member in credits.get("cast", [])[:10]:
        photo = ""
        if member.get("profile_path"):
            photo = f"https://image.tmdb.org/t/p/w185{member['profile_path']}"
        cast.append({
            "name": member.get("name", ""),
            "character": member.get("character", ""),
            "photo": photo,
        })

    # Poster and backdrop
    poster = ""
    if details.get("poster_path"):
        poster = f"https://image.tmdb.org/t/p/w500{details['poster_path']}"
    backdrop = ""
    if details.get("backdrop_path"):
        backdrop = f"https://image.tmdb.org/t/p/w1280{details['backdrop_path']}"

    # Genres
    genres = [g.get("name", "") for g in details.get("genres", [])]

    # Runtime (movies have runtime, TV has episode_run_time)
    runtime = details.get("runtime") or 0
    if not runtime and kind == "tv":
        ert = details.get("episode_run_time", [])
        runtime = ert[0] if ert else 0

    # Similar movies from TMDB
    similar_tmdb = []
    for s in similar_data.get("results", [])[:10]:
        s_title = s.get("title") or s.get("name") or ""
        s_date = s.get("release_date") or s.get("first_air_date") or ""
        s_year = s_date[:4] if s_date else ""
        s_poster = ""
        if s.get("poster_path"):
            s_poster = f"https://image.tmdb.org/t/p/w500{s['poster_path']}"
        s_type = "tv" if s.get("name") and not s.get("title") else "movie"
        similar_tmdb.append({
            "title": s_title,
            "year": s_year,
            "tmdb_id": str(s.get("id", "")),
            "poster": s_poster,
            "rating": round(s.get("vote_average", 0), 1),
            "type": s_type,
        })

    # Similar from wiki KB (same category)
    similar_kb_raw = []
    categories, _ = _get_wiki_kb()
    title_lower = title.lower()
    found_cats = []
    for cat_name, movies in categories.items():
        for movie in movies:
            if movie["title"].lower() == title_lower:
                found_cats.append(cat_name)
                break

    seen_kb = {title_lower}
    # Also exclude movies already in similar_tmdb
    for s in similar_tmdb:
        seen_kb.add(s["title"].lower())
    for cat_name in found_cats:
        for movie in categories.get(cat_name, []):
            key = movie["title"].lower()
            if key not in seen_kb:
                seen_kb.add(key)
                similar_kb_raw.append(movie)
            if len(similar_kb_raw) >= 10:
                break
        if len(similar_kb_raw) >= 10:
            break

    # Enrich wiki KB results with posters from TMDB
    similar_kb = []
    def _fetch_kb_poster(movie):
        m = dict(movie)
        if m.get("tmdb_id"):
            try:
                t = "tv" if m.get("type") == "series" else "movie"
                data = _tmdb_fetch(f"/{t}/{m['tmdb_id']}")
                if data and data.get("poster_path"):
                    m["poster"] = f"https://image.tmdb.org/t/p/w500{data['poster_path']}"
                if data and data.get("vote_average"):
                    m["rating"] = round(data["vote_average"], 1)
            except Exception:
                pass
        return m

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        similar_kb = list(pool.map(_fetch_kb_poster, similar_kb_raw))

    result = {
        "title": title,
        "year": year,
        "overview": details.get("overview", ""),
        "poster": poster,
        "backdrop": backdrop,
        "genres": genres,
        "runtime": runtime,
        "rating": round(details.get("vote_average", 0), 1),
        "vote_count": details.get("vote_count", 0),
        "cast": cast,
        "director": director,
        "tagline": details.get("tagline", ""),
        "status": details.get("status", ""),
        "tmdb_id": str(tmdb_id),
        "type": kind,
        "torrent_query": f"{title} {year}".strip(),
        "similar_tmdb": similar_tmdb,
        "similar_kb": similar_kb,
    }

    _detail_cache[cache_key] = {"data": result, "ts": now}
    return result


# ═══════════════════════════════════════
#  HTTP Handler
# ═══════════════════════════════════════
class JarvisHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, filepath, content_type):
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404)

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length).decode() if length else ""

    def do_GET(self):
        path = self.path.split("?")[0]
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if path in ("/", "/index.html"):
            self.serve_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")

        elif path == "/api/system":
            self.send_json(get_system_stats())
        elif path == "/api/docker/containers":
            self.send_json(get_docker_containers())
        elif path == "/api/docker/stats":
            self.send_json(get_docker_stats())
        elif path == "/api/docker/logs":
            c = params.get("container", [""])[0]
            n = params.get("lines", ["100"])[0]
            self.send_json(get_docker_logs(c, int(n) if n.isdigit() else 100))
        elif path == "/api/processes":
            self.send_json(get_processes())
        elif path == "/api/storage":
            self.send_json(get_storage())
        elif path == "/api/weather":
            self.send_json(get_weather())
        elif path == "/api/bandwidth/history":
            with bw_lock:
                self.send_json(list(bw_history))
        elif path == "/api/torrent-search":
            q = params.get("q", [""])[0]
            if not q:
                self.send_json({"error": "Missing query"}, 400)
            else:
                self.send_json(search_torrents(q))

        elif path == "/api/recommendations/mood":
            mood = params.get("mood", [""])[0]
            if not mood:
                self.send_json({"error": "Missing mood parameter"}, 400)
            else:
                self.send_json(get_recommendations_mood(mood))
        elif path == "/api/recommendations/similar":
            title = params.get("title", [""])[0]
            if not title:
                self.send_json({"error": "Missing title parameter"}, 400)
            else:
                self.send_json(get_recommendations_similar(title))
        elif path == "/api/recommendations/library":
            self.send_json(get_recommendations_library())
        elif path == "/api/recommendations/trending":
            tw = params.get("time_window", ["week"])[0]
            if tw not in ("day", "week"):
                tw = "week"
            self.send_json(get_recommendations_trending(tw))
        elif path == "/api/recommendations/categories":
            self.send_json(get_recommendations_categories())
        elif path == "/api/recommendations/autocomplete":
            q = params.get("q", [""])[0]
            if not q:
                self.send_json({"error": "Missing query parameter"}, 400)
            else:
                self.send_json(get_recommendations_autocomplete(q))
        elif path == "/api/recommendations/search":
            q = params.get("q", [""])[0]
            if not q:
                self.send_json({"error": "Missing query parameter"}, 400)
            else:
                self.send_json(get_recommendations_search(q))
        elif path == "/api/recommendations/detail":
            tmdb_id = params.get("tmdb_id", [""])[0]
            media_type = params.get("type", ["movie"])[0]
            if not tmdb_id:
                self.send_json({"error": "Missing tmdb_id parameter"}, 400)
            else:
                self.send_json(get_recommendations_detail(tmdb_id, media_type))

        elif path == "/api/files/list":
            p = params.get("path", [""])[0]
            self.send_json(file_list(p))
        elif path == "/api/files/download":
            p = params.get("path", [""])[0]
            real = file_download_path(p)
            if not real:
                self.send_json({"error": "File not found or is a directory"}, 404)
            else:
                try:
                    fsize = os.path.getsize(real)
                    mime, _ = mimetypes.guess_type(real)
                    self.send_response(200)
                    self.send_header("Content-Type", mime or "application/octet-stream")
                    self.send_header("Content-Length", fsize)
                    self.send_header("Content-Disposition", f'attachment; filename="{os.path.basename(real)}"')
                    self.end_headers()
                    with open(real, "rb") as f:
                        while True:
                            chunk = f.read(65536)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                except Exception as e:
                    self.send_json({"error": str(e)}, 500)

        elif path.startswith("/api/qbit/"):
            qbit_path = path.replace("/api/qbit", "")
            if query: qbit_path += f"?{query}"
            self.send_json(qbit_request(qbit_path))
        elif path.startswith("/api/jellyfin/"):
            route = path.replace("/api/jellyfin", "")
            mapping = {
                "/items/counts": "/Items/Counts",
                "/items/latest": "/Items/Latest?Limit=10",
                "/sessions": "/Sessions",
                "/system/info": "/System/Info",
            }
            jf_path = mapping.get(route)
            if jf_path:
                self.send_json(jellyfin_request(jf_path))
            else:
                self.send_json({"error": "Unknown endpoint"}, 404)
        else:
            self.send_error(404)

    def do_POST(self):
        path = self.path.split("?")[0]
        query = urllib.parse.urlparse(self.path).query

        if path == "/api/docker/action":
            try:
                body = json.loads(self.read_body())
                self.send_json(docker_action(body.get("container", ""), body.get("action", "")))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)

        elif path == "/api/torrent-add":
            try:
                body = json.loads(self.read_body())
                magnet = body.get("magnet", "")
                category = body.get("category", "")
                if not magnet.startswith("magnet:"):
                    self.send_json({"error": "Invalid magnet link"}, 400)
                    return
                post_data = urllib.parse.urlencode({"urls": magnet, "category": category})
                self.send_json(qbit_request("/torrents/add", method="POST", body=post_data))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)

        elif path == "/api/files/delete":
            try:
                body = json.loads(self.read_body())
                self.send_json(file_delete(body.get("path", "")))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
        elif path == "/api/files/move":
            try:
                body = json.loads(self.read_body())
                self.send_json(file_move(body.get("src", ""), body.get("dst", "")))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
        elif path == "/api/files/copy":
            try:
                body = json.loads(self.read_body())
                self.send_json(file_copy(body.get("src", ""), body.get("dst", "")))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
        elif path == "/api/files/mkdir":
            try:
                body = json.loads(self.read_body())
                self.send_json(file_mkdir(body.get("path", "")))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
        elif path == "/api/files/rename":
            try:
                body = json.loads(self.read_body())
                self.send_json(file_rename(body.get("path", ""), body.get("name", "")))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)

        elif path == "/api/actions/jellyfin-scan":
            self.send_json(action_jellyfin_scan())
        elif path == "/api/actions/clean-torrents":
            self.send_json(action_clean_torrents())
        elif path == "/api/actions/docker-prune":
            self.send_json(action_docker_prune())
        elif path == "/api/actions/update-check":
            self.send_json(action_update_check())

        elif path.startswith("/api/qbit/"):
            qbit_path = path.replace("/api/qbit", "")
            if query: qbit_path += f"?{query}"
            body = self.read_body()
            self.send_json(qbit_request(qbit_path, method="POST", body=body))
        else:
            self.send_error(404)


if __name__ == "__main__":
    # Start bandwidth collector thread
    t = threading.Thread(target=_bw_collector, daemon=True)
    t.start()
    # Prefetch storage in background
    threading.Thread(target=get_storage, daemon=True).start()

    server = ThreadingHTTPServer((HOST, PORT), JarvisHandler)
    print(f"Jarvis Dashboard v2 running on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
