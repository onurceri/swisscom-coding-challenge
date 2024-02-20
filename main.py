import time

import uvicorn as uvicorn
from fastapi import FastAPI

from app.api.routers import groups


def create_app() -> FastAPI:
    current_app = FastAPI(
        title="Group management with Celery and RabbitMQ",
        description="FastAPI Application to create and delete groups on nodes asynchronously using Celery and RabbitMQ.",
        version="1.0.0",
    )

    current_app.include_router(groups.router)
    return current_app


app = create_app()


@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(f"{process_time:0.4f} sec")
    return response


if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)
