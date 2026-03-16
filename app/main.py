from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router

app = FastAPI(
    title="ShiftManager",
    description="Medical shift management system for Italian healthcare institutions",
    version="0.1.0",
    redirect_slashes=False,
)

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


_static = Path(__file__).parent / "static"


@app.get("/")
async def root():
    return FileResponse(str(_static / "index.html"))


app.mount("/static", StaticFiles(directory=str(_static)), name="static")
