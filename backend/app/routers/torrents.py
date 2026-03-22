from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.services import qbittorrent as qbit_svc

router = APIRouter(prefix="/api", tags=["torrents"])


class TorrentAddRequest(BaseModel):
    magnet: str
    category: str = ""


@router.get("/torrent-search")
def search(q: str = ""):
    if not q:
        return {"error": "Missing query"}
    return qbit_svc.search_torrents(q)


@router.post("/torrent-add")
def add_torrent(body: TorrentAddRequest):
    return qbit_svc.add_torrent(body.magnet, body.category)


@router.api_route("/qbit/{path:path}", methods=["GET", "POST"])
async def qbit_proxy(path: str, request: Request):
    qbit_path = f"/{path}"
    query = str(request.query_params)
    if query:
        qbit_path += f"?{query}"
    if request.method == "POST":
        body = (await request.body()).decode()
        return qbit_svc.request(qbit_path, method="POST", body=body)
    return qbit_svc.request(qbit_path)
