from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services import tasks as tasks_svc

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    column: str = "todo"
    entities: list[dict] = []
    date: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    column: str | None = None
    order: int | None = None
    entities: list[dict] | None = None
    date: str | None = None


class ReorderItem(BaseModel):
    id: str
    column: str
    order: int


@router.get("")
def list_tasks(date: str | None = Query(None)):
    return tasks_svc.list_tasks(for_date=date)


@router.post("")
def create_task(body: TaskCreate):
    return tasks_svc.create_task(body.title, body.column, body.entities, body.date)


@router.patch("/{task_id}")
def update_task(task_id: str, body: TaskUpdate):
    updates = body.model_dump(exclude_none=True)
    result = tasks_svc.update_task(task_id, updates)
    if result is None:
        return {"error": "Task not found"}
    return result


@router.delete("/{task_id}")
def delete_task(task_id: str):
    if tasks_svc.delete_task(task_id):
        return {"ok": True}
    return {"error": "Task not found"}


@router.post("/reorder")
def reorder(items: list[ReorderItem]):
    ok = tasks_svc.reorder([i.model_dump() for i in items])
    return {"ok": ok}


@router.post("/migrate")
def migrate(date: str | None = Query(None)):
    """Move all incomplete tasks from previous dates to the given date (default: today)."""
    migrated = tasks_svc.migrate_previous_todos(date)
    return {"ok": True, "migrated": len(migrated)}
