"""Canonical hashing of timeline state for determinism verification."""
import hashlib
import json
from enum import Enum
from typing import Dict, Any
from app.core.models import Timeline


def sorted_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(d, dict):
        return d
    return {k: sorted_dict(v) if isinstance(v, dict) else v for k, v in sorted(d.items())}


def canonical_hash(timeline: Timeline) -> str:
    """Compute deterministic SHA-256 canonical hash of timeline."""
    canonical = {
        "source_media_id": timeline.source_media_id,
        "segments": [
            {
                "source_media_id": s.source_media_id,
                "source_start_s": round(s.source_start_s, 6),
                "source_end_s": round(s.source_end_s, 6),
                "speed": round(s.speed, 6),
            }
            for s in timeline.segments
        ],
        "anchors": sorted([
            {
                "type": a.type.value if isinstance(a.type, Enum) else str(a.type),
                "source_start_s": round(a.source_start_s, 6),
                "source_end_s": round(a.source_end_s, 6),
                "properties": sorted_dict(a.properties),
                "active": a.active,
            }
            for a in timeline.anchors
        ], key=lambda x: (x["type"], x["source_start_s"])),
        "background_music": timeline.background_music.model_dump() if timeline.background_music else None,
        "auto_captions_enabled": timeline.auto_captions_enabled,
    }
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
