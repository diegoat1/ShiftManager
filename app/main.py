from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router, auth_router
from app.api.admin_documents import types_router
from app.core.config import settings

app = FastAPI(
    title="ShiftManager",
    description="Medical shift management system for Italian healthcare institutions",
    version="0.2.0",
    redirect_slashes=False,
)

app.include_router(api_router)
app.include_router(auth_router)
app.include_router(types_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


_static = Path(__file__).parent / "static"

# Mount uploads directory
_uploads = Path(settings.UPLOAD_DIR)
_uploads.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads)), name="uploads")


@app.get("/")
async def root():
    return FileResponse(str(_static / "index.html"))


@app.get("/sw.js")
async def service_worker():
    return FileResponse(
        str(_static / "sw.js"),
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"},
    )


@app.get("/manifest.json")
async def manifest():
    return FileResponse(str(_static / "manifest.json"), media_type="application/manifest+json")


app.mount("/static", StaticFiles(directory=str(_static)), name="static")
