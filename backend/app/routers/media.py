from fastapi import APIRouter
from fastapi.responses import Response

import httpx

from app.config import settings
from app.services import jellyfin as jellyfin_svc

router = APIRouter(prefix="/api/jellyfin", tags=["media"])

_ROUTE_MAP = {
    "/items/counts": "/Items/Counts",
    "/items/latest": "/Items/Latest?Limit=10",
    "/sessions": "/Sessions",
    "/system/info": "/System/Info",
}


def _get_user_id() -> str:
    users = jellyfin_svc.request("/Users")
    if isinstance(users, list) and users:
        return users[0].get("Id", "")
    return ""


def _poster_url(item_id: str, tag: str = "", max_height: int = 300) -> str:
    if not tag:
        return ""
    return f"/api/jellyfin-media/poster/{item_id}?maxHeight={max_height}&tag={tag}"


@router.get("-media/poster/{item_id}")
def poster_proxy(item_id: str, maxHeight: int = 300, tag: str = ""):
    """Proxy Jellyfin poster images to avoid localhost CORS issues."""
    url = f"{settings.jellyfin_base}/Items/{item_id}/Images/Primary?maxHeight={maxHeight}&tag={tag}&quality=90&api_key={settings.jellyfin_api_key}"
    try:
        resp = httpx.get(url, timeout=10)
        if resp.status_code == 200:
            return Response(
                content=resp.content,
                media_type=resp.headers.get("content-type", "image/jpeg"),
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except Exception:
        pass
    return Response(status_code=404)


@router.get("/{path:path}")
def jellyfin_proxy(path: str):
    route = f"/{path}"
    jf_path = _ROUTE_MAP.get(route)
    if jf_path:
        return jellyfin_svc.request(jf_path)
    return {"error": "Unknown endpoint"}


@router.get("-media/overview")
def media_overview():
    """Aggregated media page data: counts, continue watching, recently added, library, genres."""
    user_id = _get_user_id()
    if not user_id:
        return {"error": "No Jellyfin user found"}

    result = {}

    # Counts
    counts = jellyfin_svc.request("/Items/Counts")
    result["counts"] = counts if not isinstance(counts, dict) or "error" not in counts else None

    # Continue watching (resumable items)
    resume = jellyfin_svc.request(
        f"/Users/{user_id}/Items/Resume?Limit=10&Fields=Overview,RunTimeTicks,ImageTags,SeriesName,ParentIndexNumber,IndexNumber"
    )
    continue_watching = []
    if isinstance(resume, dict) and resume.get("Items"):
        for item in resume["Items"]:
            pos = item.get("UserData", {}).get("PlaybackPositionTicks", 0)
            total = item.get("RunTimeTicks", 1) or 1
            pct = round(pos / total * 100)
            poster_tag = item.get("ImageTags", {}).get("Primary", "")
            name = item.get("Name", "")
            if item.get("Type") == "Episode":
                name = f"{item.get('SeriesName', '')} S{item.get('ParentIndexNumber', '?')}E{item.get('IndexNumber', '?')}"
            continue_watching.append({
                "id": item["Id"],
                "name": name,
                "type": item.get("Type", ""),
                "progress": pct,
                "runtime_min": round(total / 600000000),
                "poster": _poster_url(item["Id"], poster_tag),
            })
    result["continue_watching"] = continue_watching

    # Now playing sessions
    sessions = jellyfin_svc.request("/Sessions")
    now_playing = []
    if isinstance(sessions, list):
        for s in sessions:
            np = s.get("NowPlayingItem")
            if np:
                pos = s.get("PlayState", {}).get("PositionTicks", 0)
                total = np.get("RunTimeTicks", 1) or 1
                pct = round(pos / total * 100)
                poster_tag = np.get("ImageTags", {}).get("Primary", "")
                now_playing.append({
                    "user": s.get("UserName", ""),
                    "client": s.get("Client", ""),
                    "device": s.get("DeviceName", ""),
                    "title": np.get("Name", ""),
                    "type": np.get("Type", ""),
                    "progress": pct,
                    "poster": _poster_url(np["Id"], poster_tag),
                    "is_paused": s.get("PlayState", {}).get("IsPaused", False),
                })
    result["now_playing"] = now_playing

    # Next up (series)
    nextup = jellyfin_svc.request(
        f"/Shows/NextUp?userId={user_id}&Limit=10&Fields=Overview,ImageTags,RunTimeTicks,ParentIndexNumber,IndexNumber"
    )
    next_episodes = []
    if isinstance(nextup, dict) and nextup.get("Items"):
        for item in nextup["Items"]:
            poster_tag = item.get("ImageTags", {}).get("Primary", "")
            next_episodes.append({
                "id": item["Id"],
                "series_name": item.get("SeriesName", ""),
                "season": item.get("ParentIndexNumber", 0),
                "episode": item.get("IndexNumber", 0),
                "name": item.get("Name", ""),
                "overview": (item.get("Overview") or "")[:150],
                "runtime_min": round(item.get("RunTimeTicks", 0) / 600000000),
                "poster": _poster_url(item["Id"], poster_tag),
            })
    result["next_up"] = next_episodes

    # Recently added (with posters)
    recent_movies = jellyfin_svc.request(
        f"/Users/{user_id}/Items?IncludeItemTypes=Movie&Recursive=true&SortBy=DateCreated&SortOrder=Descending&Limit=12&Fields=Overview,CommunityRating,RunTimeTicks,ImageTags,Genres"
    )
    recent_series = jellyfin_svc.request(
        f"/Users/{user_id}/Items?IncludeItemTypes=Series&Recursive=true&SortBy=DateCreated&SortOrder=Descending&Limit=6&Fields=Overview,CommunityRating,ImageTags,ChildCount"
    )
    recently_added = []
    for src in [recent_movies, recent_series]:
        if isinstance(src, dict) and src.get("Items"):
            for item in src["Items"]:
                poster_tag = item.get("ImageTags", {}).get("Primary", "")
                recently_added.append({
                    "id": item["Id"],
                    "name": item.get("Name", ""),
                    "type": item.get("Type", ""),
                    "year": str(item.get("ProductionYear", "")),
                    "rating": item.get("CommunityRating"),
                    "runtime_min": round(item.get("RunTimeTicks", 0) / 600000000) if item.get("RunTimeTicks") else None,
                    "genres": item.get("Genres", []),
                    "overview": (item.get("Overview") or "")[:120],
                    "poster": _poster_url(item["Id"], poster_tag),
                    "played": item.get("UserData", {}).get("Played", False),
                    "season_count": item.get("ChildCount"),
                })
    result["recently_added"] = recently_added

    # Genre breakdown
    all_items = jellyfin_svc.request(
        f"/Users/{user_id}/Items?IncludeItemTypes=Movie,Series&Recursive=true&Limit=200&Fields=Genres"
    )
    genre_counts = {}
    if isinstance(all_items, dict) and all_items.get("Items"):
        for item in all_items["Items"]:
            for g in item.get("Genres", []):
                genre_counts[g] = genre_counts.get(g, 0) + 1
    result["genres"] = sorted(
        [{"name": g, "count": c} for g, c in genre_counts.items()],
        key=lambda x: x["count"], reverse=True
    )

    return result
