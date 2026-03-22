from fastapi import APIRouter

from app.services import system as system_svc

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/system")
def get_system():
    return system_svc.get_system_stats()


@router.get("/processes")
def get_processes():
    return system_svc.get_processes()


@router.get("/storage")
def get_storage():
    return system_svc.get_storage()


@router.get("/weather")
async def get_weather():
    return await system_svc.get_weather()


@router.get("/bandwidth/history")
def get_bandwidth_history():
    return system_svc.get_bandwidth_history()
