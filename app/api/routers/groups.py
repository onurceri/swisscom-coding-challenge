from fastapi import APIRouter
from starlette.responses import JSONResponse

from app.api.schemas.schemas import CreateGroup, DeleteGroup
from app.celery_tasks import celery_app
from app.celery_tasks.create_task import create_group
from app.celery_tasks.delete_task import delete_group

router = APIRouter(
    prefix="/groups", tags=["Groups"], responses={404: {"description": "Not found"}}
)


@router.post("/create")
async def create(input_dto: CreateGroup):
    """
    Create a group with the given group_id
    """
    task = create_group.delay(input_dto.group_id)
    return JSONResponse({"task_id": task.id})


@router.post("/delete")
async def delete(input_dto: DeleteGroup):
    """
    Delete a group with the given group_id
    """
    task = delete_group.delay(input_dto.group_id)
    return JSONResponse({"task_id": task.id})


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    Return the status of the submitted task
    """
    task_result = celery_app.AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_result.id,
        "state": task_result.state,
        "status": task_result.status,
    }
