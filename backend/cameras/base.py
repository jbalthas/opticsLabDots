"""
base.py — Abstract base class for all camera drivers.

Each camera driver must implement:
  - ping()        : True if camera is reachable
  - get_info()    : dict of model/firmware/resolution
  - snapshot()    : bytes of a single JPEG/TIFF frame (uncompressed single-frame)
  - mjpeg_url()   : URL string the backend can proxy for live preview
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class CameraConfig:
    id: str
    name: str
    model: str
    driver: str
    ip: str
    port: int
    username: str
    password: str
    notes: Optional[str] = None


class BaseCamera(ABC):
    def __init__(self, config: CameraConfig) -> None:
        self.config = config

    @property
    def base_url(self) -> str:
        return f"http://{self.config.ip}:{self.config.port}"

    @property
    def auth(self) -> tuple[str, str]:
        return (self.config.username, self.config.password)

    @abstractmethod
    def ping(self) -> bool:
        """Return True if the camera responds on the network."""

    @abstractmethod
    def get_info(self) -> dict:
        """Return camera metadata: firmware, resolution, model, serial."""

    @abstractmethod
    def snapshot(self) -> bytes:
        """
        Capture a single frame as JPEG bytes.
        This is the IQ-testing capture path — single frame, no inter-frame
        video codec compression.
        """

    @abstractmethod
    def mjpeg_url(self) -> str:
        """
        Return the MJPEG stream URL for live browser preview.
        The backend proxies this URL; credentials are NOT exposed to the client.
        """
