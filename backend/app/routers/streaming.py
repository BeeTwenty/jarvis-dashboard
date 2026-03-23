from fastapi import APIRouter
from fastapi.responses import Response

import httpx

from app.services import allanime

router = APIRouter(prefix="/api/streaming", tags=["streaming"])


@router.get("/check")
def check(title: str = "", type: str = ""):
    """Check if a title is available for streaming on AllAnime."""
    if not title:
        return {"available": False}
    match = allanime.check_availability(title)
    if not match:
        return {"available": False}
    return {
        "available": True,
        "show_id": match["id"],
        "name": match["name"],
        "episodes_sub": match["episodes_sub"],
        "episodes_dub": match["episodes_dub"],
    }


@router.get("/search")
def search(q: str = "", mode: str = "sub"):
    """Search for anime titles."""
    if not q or len(q) < 2:
        return {"results": []}
    results = allanime.search(q, mode)
    return {"results": results}


@router.get("/episodes")
def episodes(show_id: str = "", mode: str = "sub"):
    """Get episode list for a show."""
    if not show_id:
        return {"episodes": []}
    eps = allanime.get_episodes(show_id, mode)
    return {"episodes": eps}


@router.get("/sources")
def sources(show_id: str = "", episode: str = "", mode: str = "sub"):
    """Get stream sources for an episode."""
    if not show_id or not episode:
        return {"sources": [], "subtitles": []}
    return allanime.get_episode_sources(show_id, episode, mode)


@router.get("/proxy")
async def proxy_stream(url: str = "", referer: str = ""):
    """Proxy m3u8 manifests or segments that require specific headers."""
    if not url:
        return Response(content="Missing url", status_code=400)
    try:
        headers = {"User-Agent": allanime.USER_AGENT}
        if referer:
            headers["Referer"] = referer
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            content_type = resp.headers.get("content-type", "application/octet-stream")
            return Response(
                content=resp.content,
                media_type=content_type,
                headers={"Access-Control-Allow-Origin": "*"},
            )
    except Exception as e:
        return Response(content=str(e), status_code=502)
