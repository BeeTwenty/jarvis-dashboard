from fastapi import APIRouter

from app.services import jellyfin as jellyfin_svc

router = APIRouter(prefix="/api/jellyfin", tags=["media"])

_ROUTE_MAP = {
    "/items/counts": "/Items/Counts",
    "/items/latest": "/Items/Latest?Limit=10",
    "/sessions": "/Sessions",
    "/system/info": "/System/Info",
}


@router.get("/{path:path}")
def jellyfin_proxy(path: str):
    route = f"/{path}"
    jf_path = _ROUTE_MAP.get(route)
    if jf_path:
        return jellyfin_svc.request(jf_path)
    return {"error": "Unknown endpoint"}
