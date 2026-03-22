import json
import urllib.parse

import httpx

from app.config import settings

_sid: str | None = None
_client = httpx.Client(timeout=10)


def _login() -> bool:
    global _sid
    try:
        resp = _client.post(
            f"{settings.qbit_base}/auth/login",
            data={"username": settings.qbit_user, "password": settings.qbit_pass},
        )
        for cookie in resp.headers.get_all("set-cookie"):
            if "SID=" in cookie:
                _sid = cookie.split("SID=")[1].split(";")[0]
                return True
    except Exception:
        pass
    return False


def request(path: str, method: str = "GET", body: str | None = None, retry: bool = True) -> dict | list:
    global _sid
    if not _sid:
        _login()
    url = f"{settings.qbit_base}{path}"
    try:
        headers = {}
        if _sid:
            headers["Cookie"] = f"SID={_sid}"
        if method == "GET":
            resp = _client.get(url, headers=headers)
        else:
            content_headers = {**headers, "Content-Type": "application/x-www-form-urlencoded"}
            resp = _client.post(url, headers=content_headers, content=body)
        if resp.status_code == 403 and retry:
            _login()
            return request(path, method, body, retry=False)
        raw = resp.text.strip()
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"ok": True, "message": raw}
        return {"ok": True}
    except Exception as e:
        return {"error": f"qBittorrent: {e}"}


def search_torrents(query: str) -> dict | list:
    try:
        async_client = httpx.Client(timeout=15)
        resp = async_client.get(
            f"https://apibay.org/q.php?q={urllib.parse.quote(query)}",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        results = resp.json()
        if not isinstance(results, list):
            return {"error": "Unexpected response"}
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
        filtered.sort(key=lambda x: x["seeders"], reverse=True)
        return filtered
    except Exception as e:
        return {"error": str(e)}


def add_torrent(magnet: str, category: str = "") -> dict:
    if not magnet.startswith("magnet:"):
        return {"error": "Invalid magnet link"}
    post_data = urllib.parse.urlencode({"urls": magnet, "category": category})
    return request("/torrents/add", method="POST", body=post_data)


def clean_completed() -> dict:
    try:
        torrents = request("/torrents/info")
        if isinstance(torrents, dict) and torrents.get("error"):
            return torrents
        cleaned = []
        for t in torrents:
            if t.get("progress", 0) >= 1.0 and t.get("state", "") in ("pausedUP", "stalledUP", "uploading"):
                h = t.get("hash", "")
                if h:
                    request(f"/torrents/delete?hashes={h}&deleteFiles=false", method="POST")
                    cleaned.append(t.get("name", h))
        if cleaned:
            return {"ok": True, "message": f"Removed {len(cleaned)} completed: {', '.join(cleaned[:3])}{'...' if len(cleaned) > 3 else ''}"}
        return {"ok": True, "message": "No completed torrents to clean"}
    except Exception as e:
        return {"error": str(e)}
