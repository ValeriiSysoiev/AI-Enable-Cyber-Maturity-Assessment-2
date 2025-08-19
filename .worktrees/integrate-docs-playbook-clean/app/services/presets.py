import os, json, re
from pathlib import Path
from typing import List, Dict, Any
from fastapi import HTTPException
from ..api.schemas import AssessmentPreset
from .cache import get_cached, invalidate_cache_key, cache_manager
from ..config import config

BUNDLED: Dict[str, Path] = {}  # filled at startup with any bundled presets (e.g. cyber-for-ai.json)
DATA_DIR = Path("data/presets")

def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def _load_json(p: Path) -> Dict[str, Any]:
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"Invalid JSON in {p.name}: {e}") from e
    except OSError as e:
        raise HTTPException(500, f"File I/O error for {p.name}: {e}") from e

def _slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:40] or "preset"

async def list_presets() -> List[Dict[str, Any]]:
    """List all available presets with caching for performance"""
    if not config.cache.enabled:
        return _list_presets_uncached()
    
    async def compute_presets_list():
        return _list_presets_uncached()
    
    return await get_cached(
        cache_name="presets",
        key="presets_list",
        factory=compute_presets_list,
        ttl_seconds=config.cache.presets_ttl_seconds,
        max_size_mb=config.cache.presets_max_size_mb,
        max_entries=config.cache.presets_max_entries,
        cleanup_interval_seconds=config.cache.cleanup_interval_seconds
    )


def _list_presets_uncached() -> List[Dict[str, Any]]:
    """Internal uncached implementation of list_presets"""
    ensure_dirs()
    items: List[Dict[str, Any]] = []

    # bundled
    for pid, path in BUNDLED.items():
        data = _load_json(path)
        try:
            preset = AssessmentPreset(**data)
            counts = {
                "pillars": len(preset.pillars),
                "capabilities": sum(len(p.capabilities) for p in preset.pillars),
                "questions": sum(len(c.questions) for p in preset.pillars for c in p.capabilities),
            }
            items.append({"id": preset.id, "name": preset.name, "version": preset.version, "source": "bundled", "counts": counts})
        except Exception:
            continue

    # uploaded
    for p in DATA_DIR.glob("*.json"):
        data = _load_json(p)
        try:
            preset = AssessmentPreset(**data)
            counts = {
                "pillars": len(preset.pillars),
                "capabilities": sum(len(p.capabilities) for p in preset.pillars),
                "questions": sum(len(c.questions) for p in preset.pillars for c in p.capabilities),
            }
            items.append({"id": preset.id, "name": preset.name, "version": preset.version, "source": "uploaded", "counts": counts})
        except Exception:
            continue

    # unique by id (prefer uploaded over bundled)
    out = {}
    for it in items:
        out[it["id"]] = it
    return list(out.values())

async def get_preset(preset_id: str) -> AssessmentPreset:
    """Get a specific preset with caching for performance"""
    if not config.cache.enabled:
        return _get_preset_uncached(preset_id)
    
    async def compute_preset():
        return _get_preset_uncached(preset_id)
    
    cached_preset = await get_cached(
        cache_name="presets",
        key=f"preset_{preset_id}",
        factory=compute_preset,
        ttl_seconds=config.cache.presets_ttl_seconds,
        max_size_mb=config.cache.presets_max_size_mb,
        max_entries=config.cache.presets_max_entries,
        cleanup_interval_seconds=config.cache.cleanup_interval_seconds
    )
    
    return AssessmentPreset(**cached_preset) if isinstance(cached_preset, dict) else cached_preset


def _get_preset_uncached(preset_id: str) -> AssessmentPreset:
    """Internal uncached implementation of get_preset"""
    ensure_dirs()
    # uploaded takes precedence
    up = DATA_DIR / f"{preset_id}.json"
    if up.exists():
        return AssessmentPreset(**_load_json(up))
    # then bundled
    path = BUNDLED.get(preset_id)
    if path and path.exists():
        return AssessmentPreset(**_load_json(path))
    raise HTTPException(404, "Preset not found")

async def save_uploaded_preset(data: dict) -> AssessmentPreset:
    """Save uploaded preset and invalidate related caches"""
    ensure_dirs()
    preset = AssessmentPreset(**data)
    
    # Validate preset.id to prevent path traversal
    safe_id = _validate_safe_filename(preset.id)
    out = DATA_DIR / f"{safe_id}.json"
    
    # Verify the resolved path is within DATA_DIR
    if not out.resolve().is_relative_to(DATA_DIR.resolve()):
        raise HTTPException(400, f"Invalid preset ID: path traversal detected")
    
    with out.open("w", encoding="utf-8") as f:
        json.dump(preset.model_dump(), f, ensure_ascii=False, indent=2)
    
    # Invalidate caches when preset is saved
    if config.cache.enabled:
        await invalidate_cache_key("presets", f"preset_{preset.id}")
        await invalidate_cache_key("presets", "presets_list")
    
    return preset

def _validate_safe_filename(filename: str) -> str:
    """Validate and sanitize filename to prevent path traversal"""
    # Remove any path separators and dangerous characters
    safe_filename = re.sub(r'[^A-Za-z0-9_.-]', '', filename)
    
    # Enforce reasonable length limit
    if len(safe_filename) > 100:
        safe_filename = safe_filename[:100]
    
    # Ensure it's not empty after sanitization
    if not safe_filename:
        raise HTTPException(400, "Invalid preset ID: contains only unsafe characters")
    
    # Prevent special filenames
    if safe_filename in ('.', '..') or safe_filename.startswith('.'):
        raise HTTPException(400, f"Invalid preset ID: '{safe_filename}' is not allowed")
    
    return safe_filename
