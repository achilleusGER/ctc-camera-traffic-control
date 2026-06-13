"""Media: Beweisfotos ausliefern (nur local-Backend in Phase 1)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import settings

router = APIRouter(prefix="/media", tags=["Media"])


def _safe_resolve(rel_path: str) -> Path:
    """Verhindert Path-Traversal: löst nur Paths innerhalb MEDIA_DIR auf."""
    base = settings.media_dir.resolve()
    candidate = (base / rel_path).resolve()
    if not str(candidate).startswith(str(base)):
        raise HTTPException(status_code=400, detail="Invalid path")
    return candidate


@router.get("/evidence/{path:path}")
async def get_evidence(path: str) -> FileResponse:
    p = _safe_resolve(path)
    if not p.is_file():
        raise HTTPException(status_code=404, detail="Evidence not found")
    return FileResponse(p, headers={"Cache-Control": "no-cache, must-revalidate"})


@router.get("/health")
async def media_health() -> dict:
    """Prüft, ob das Media-Verzeichnis lesbar ist."""
    base = settings.media_dir
    if not base.exists():
        return {"ok": False, "reason": "MEDIA_DIR existiert nicht", "path": str(base)}
    return {"ok": True, "path": str(base)}
