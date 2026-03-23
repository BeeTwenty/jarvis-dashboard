from fastapi import APIRouter

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
    }
