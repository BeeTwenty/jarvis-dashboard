import httpx

from app.config import settings

_client = httpx.Client(timeout=10)


def request(path: str) -> dict | list:
    sep = "&" if "?" in path else "?"
    url = f"{settings.jellyfin_base}{path}{sep}api_key={settings.jellyfin_api_key}"
    try:
        resp = _client.get(url)
        return resp.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"Jellyfin returned {e.response.status_code}"}
    except Exception as e:
        return {"error": f"Jellyfin: {e}"}


def scan_library() -> dict:
    try:
        url = f"{settings.jellyfin_base}/Library/Refresh?api_key={settings.jellyfin_api_key}"
        _client.post(url)
        return {"ok": True, "message": "Library scan started"}
    except Exception as e:
        return {"error": str(e)}
