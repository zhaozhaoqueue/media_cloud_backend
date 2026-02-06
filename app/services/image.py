from __future__ import annotations

from pathlib import Path
from typing import Tuple

from PIL import Image

from app.services.storage import ensure_local_path


def generate_thumbnail(
    storage_root: str,
    source_key: str,
    thumb_key: str,
    max_size: Tuple[int, int],
) -> Path:
    source_path = Path(storage_root) / source_key
    if not source_path.exists():
        raise FileNotFoundError(f"Source image not found: {source_path}")

    thumb_path = ensure_local_path(storage_root, thumb_key)

    with Image.open(source_path) as img:
        img = img.convert("RGB")
        img.thumbnail(max_size)
        img.save(thumb_path, format="JPEG", quality=85)

    return thumb_path
