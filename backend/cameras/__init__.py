"""
cameras/__init__.py — Camera registry.

Loads camera configurations from config.yaml and returns the appropriate
driver instance for each camera ID.
"""

from __future__ import annotations

from typing import Optional
from .base import BaseCamera, CameraConfig
from .vivotek import VivotekCamera

_DRIVERS: dict[str, type[BaseCamera]] = {
    "vivotek": VivotekCamera,
}

# In-memory registry: camera_id -> driver instance (built at startup)
_registry: dict[str, BaseCamera] = {}


def build_registry(camera_configs: list[dict]) -> None:
    """Instantiate drivers for every camera in config.yaml."""
    _registry.clear()
    for cfg in camera_configs:
        driver_key = cfg.get("driver", "").lower()
        driver_cls = _DRIVERS.get(driver_key)
        if driver_cls is None:
            print(f"[cameras] Unknown driver '{driver_key}' for camera '{cfg.get('id')}' — skipping")
            continue
        config = CameraConfig(
            id=cfg["id"],
            name=cfg["name"],
            model=cfg["model"],
            driver=driver_key,
            ip=cfg["ip"],
            port=cfg.get("port", 80),
            username=cfg.get("username", "admin"),
            password=cfg.get("password", ""),
            notes=cfg.get("notes"),
        )
        _registry[config.id] = driver_cls(config)


def get_camera(camera_id: str) -> Optional[BaseCamera]:
    return _registry.get(camera_id)


def list_cameras() -> list[BaseCamera]:
    return list(_registry.values())
