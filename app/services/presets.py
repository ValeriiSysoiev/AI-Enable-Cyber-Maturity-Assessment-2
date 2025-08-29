import os, json, re
from pathlib import Path
from typing import List, Dict, Any
from fastapi import HTTPException
from api.schemas import AssessmentPreset
from services.cache import get_cached, invalidate_cache_key, cache_manager
import sys
import aiofiles
import asyncio
sys.path.append("/app")
from config import config

BUNDLED: Dict[str, Path] = {}  # filled at startup with any bundled presets (e.g. cyber-for-ai.json)
DATA_DIR = Path("data/presets")

def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

async def _load_json(p: Path) -> Dict[str, Any]:
    """Async version of JSON file loading"""
    try:
        async with aiofiles.open(p, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"Invalid JSON in {p.name}: {e}") from e
    except OSError as e:
        raise HTTPException(500, f"File I/O error for {p.name}: {e}") from e

def _slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:40] or "preset"

def _transform_legacy_preset(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform legacy preset format to current AssessmentPreset schema format"""
    if "questions" in data and "pillars" in data:
        # This is the legacy format where questions are grouped separately
        legacy_questions = data.get("questions", {})
        pillars = []
        
        for pillar in data["pillars"]:
            pillar_id = pillar["id"]
            questions_for_pillar = legacy_questions.get(pillar_id, [])
            
            # Create a single capability per pillar with all questions
            capabilities = []
            if questions_for_pillar:
                capability = {
                    "id": f"{pillar_id}-capability",
                    "name": pillar["name"],
                    "questions": [
                        {
                            "id": q["id"],
                            "text": q["text"],
                            "weight": 1.0,
                            "scale": "0-5"
                        }
                        for q in questions_for_pillar
                    ]
                }
                capabilities.append(capability)
            
            transformed_pillar = {
                "id": pillar["id"],
                "name": pillar["name"],
                "capabilities": capabilities
            }
            pillars.append(transformed_pillar)
        
        # Return transformed data with required fields
        return {
            "id": data["id"],
            "name": data["name"],
            "version": data.get("version", "1.0"),
            "pillars": pillars
        }
    
    # If it's already in the correct format, return as-is
    return data

async def list_presets() -> List[Dict[str, Any]]:
    """List all available presets with caching for performance"""
    if not config.cache.enabled:
        return await _list_presets_uncached()
    
    async def compute_presets_list():
        return await _list_presets_uncached()
    
    return await get_cached(
        cache_name="presets",
        key="presets_list",
        factory=compute_presets_list,
        ttl_seconds=config.cache.presets_ttl_seconds,
        max_size_mb=config.cache.presets_max_size_mb,
        max_entries=config.cache.presets_max_entries,
        cleanup_interval_seconds=config.cache.cleanup_interval_seconds
    )


async def _list_presets_uncached() -> List[Dict[str, Any]]:
    """Internal uncached implementation of list_presets"""
    ensure_dirs()
    items: List[Dict[str, Any]] = []

    # bundled
    for pid, path in BUNDLED.items():
        data = await _load_json(path)
        try:
            # Transform legacy format if needed
            transformed_data = _transform_legacy_preset(data)
            preset = AssessmentPreset(**transformed_data)
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
        data = await _load_json(p)
        try:
            # Transform legacy format if needed
            transformed_data = _transform_legacy_preset(data)
            preset = AssessmentPreset(**transformed_data)
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
        return await _get_preset_uncached(preset_id)
    
    async def compute_preset():
        return await _get_preset_uncached(preset_id)
    
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


async def _get_preset_uncached(preset_id: str) -> AssessmentPreset:
    """Internal uncached implementation of get_preset"""
    ensure_dirs()
    # uploaded takes precedence
    up = DATA_DIR / f"{preset_id}.json"
    if up.exists():
        data = await _load_json(up)
        transformed_data = _transform_legacy_preset(data)
        return AssessmentPreset(**transformed_data)
    # then bundled
    path = BUNDLED.get(preset_id)
    if path and path.exists():
        data = await _load_json(path)
        transformed_data = _transform_legacy_preset(data)
        return AssessmentPreset(**transformed_data)
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
    
    async with aiofiles.open(out, "w", encoding="utf-8") as f:
        content = json.dumps(preset.model_dump(), ensure_ascii=False, indent=2)
        await f.write(content)
    
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
