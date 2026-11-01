"""GOD\'S EYE — FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import xarray as xr
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ocean_backend.api.routes import observations
from ocean_backend.api.routes.ai import router as ai_router
from ocean_backend.api.routes.comparison import router as comparison_router
from ocean_backend.api.routes.diagnostics import router as diagnostics_router
from ocean_backend.api.routes.visualization import router as visualization_router
from ocean_backend.api.routes.upload import router as upload_router
from ocean_backend.services.dataset_runtime import dataset_registry
from ocean_backend.services.upload_service import DatasetUploadService


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIR = PROJECT_ROOT / "frontend" / "dist"
DATA_DIR = PROJECT_ROOT / "src" / "ocean_backend" / "data"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Load bundled demo datasets on startup and close them on shutdown."""
    load_bundled_datasets()
    try:
        yield
    finally:
        dataset_registry.close_all()


app = FastAPI(
    title="GOD'S EYE",
    version="0.3.0",
    description="Ocean model visualization, observation collocation and scientific validation services.",
    lifespan=lifespan,
)


# Vite places hashed production assets under dist/assets.
# Mounting this directory lets the same FastAPI process serve the React build.
if (FRONTEND_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="frontend-assets")


def _register_bundled_dataset(dataset_id: str, path: Path) -> None:
    """Register a bundled NetCDF dataset so the demo works immediately."""
    if not path.exists() or dataset_id in dataset_registry._datasets:
        return

    dataset = xr.open_dataset(path, decode_cf=True)
    metadata = DatasetUploadService._build_metadata(
        dataset_id=dataset_id,
        filename=path.name,
        dataset=dataset,
    )
    dataset_registry.register(
        dataset_id=dataset_id,
        dataset=dataset,
        metadata=metadata,
        path=path,
    )


def load_bundled_datasets() -> None:
    """Make bundled demonstration datasets available to the frontend."""
    _register_bundled_dataset(
        "io-model-4d",
        DATA_DIR / "model_4d.nc",
    )
    _register_bundled_dataset(
        "io-model-3d",
        DATA_DIR / "model_3d.nc",
    )


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Return backend liveness."""
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    """Serve the high-caliber frontend from the same FastAPI process."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/ocean.html", include_in_schema=False)
def ocean_explorer() -> FileResponse:
    """Serve the legacy visual explorer shell used inside the React app."""
    return FileResponse(FRONTEND_DIR / "ocean.html")


@app.get("/frontend/{asset_path:path}", include_in_schema=False)
def frontend_asset(asset_path: str) -> FileResponse:
    """Serve future frontend assets without requiring a second server."""
    candidate = (FRONTEND_DIR / asset_path).resolve()
    if not str(candidate).startswith(str(FRONTEND_DIR.resolve())) or not candidate.is_file():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Frontend asset not found.")
    return FileResponse(candidate)


app.include_router(upload_router)
app.include_router(comparison_router)
app.include_router(observations.router)
app.include_router(diagnostics_router)
app.include_router(visualization_router)
app.include_router(ai_router)
