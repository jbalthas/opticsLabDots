"""
vivotek.py — Camera driver for Vivotek IT9388 / IT9380-H network cameras.

Vivotek CGI API reference (IT9388 / IT9380 series):
  Snapshot  : GET /cgi-bin/viewer/video.jpg  (single JPEG, no video codec)
  MJPEG     : GET /cgi-bin/viewer/mjpeg.cgi  (multipart live stream)
  RTSP      : rtsp://{ip}/live.sdp            (H.264 — NOT used for IQ capture)
  Params    : GET /cgi-bin/admin/getparam.cgi?key&key...
  Set params: POST /cgi-bin/admin/setparam.cgi

Authentication: Vivotek cameras support both HTTP Digest and HTTP Basic auth
depending on firmware version.  This driver tries both automatically.
"""

from __future__ import annotations

import httpx
from typing import Optional

from .base import BaseCamera, CameraConfig

_TIMEOUT          = 5.0
_SNAPSHOT_TIMEOUT = 15.0

# Snapshot paths — tried in order, first 200+image wins
_SNAPSHOT_PATHS = [
    "/cgi-bin/viewer/video.jpg",
    "/video.jpg",
    "/cgi-bin/video.jpg",
    "/snapshot.jpg",
    "/cgi-bin/snapshot.cgi",
    "/cgi-bin/viewer/snapshot.jpg",
]

# MJPEG paths — tried in order
_MJPEG_PATHS = [
    "/cgi-bin/viewer/mjpeg.cgi",
    "/cgi-bin/viewer/mjpeg.cgi?channel=0",
    "/cgi-bin/viewer/mjpeg.cgi?channel=0&stream=0",
    "/video.mjpg",
    "/mjpeg.cgi",
]

_PATH_GETPARAM = "/cgi-bin/admin/getparam.cgi"
_PATH_SETPARAM = "/cgi-bin/admin/setparam.cgi"

_PARAM_MODEL      = "system_info_modelname"
_PARAM_SERIAL     = "system_info_serialnumber"
_PARAM_FIRMWARE   = "system_info_firmwareversion"
_PARAM_RESOLUTION = "videoin_c0_s0_resolution"


class VivotekCamera(BaseCamera):
    """Driver for Vivotek IT9388 and IT9380-H cameras."""

    def __init__(self, config: CameraConfig) -> None:
        super().__init__(config)
        # Try Basic Auth first (confirmed on IT9388), Digest as fallback (IT9380-H).
        # Working auth is cached after first success so subsequent calls are fast.
        self._basic_auth  = (config.username, config.password)
        self._digest_auth = httpx.DigestAuth(config.username, config.password)
        self._working_auth = None   # set after first successful request

        self._snapshot_path: Optional[str] = None

        # Client with no default auth — we pass auth per-request during discovery,
        # then set it on the client once we know which method works.
        self._client = httpx.Client(
            timeout=_TIMEOUT,
            verify=False,
            follow_redirects=True,
        )

    # ------------------------------------------------------------------
    # BaseCamera interface
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """Return True if the camera is reachable and credentials are accepted."""
        for auth in self._auths():
            try:
                r = self._client.get(
                    f"{self.base_url}/home.html", auth=auth, timeout=_TIMEOUT
                )
                if r.status_code == 200:
                    self._working_auth = auth
                    return True
            except Exception:
                pass
        return False

    def get_info(self) -> dict:
        keys = [_PARAM_MODEL, _PARAM_SERIAL, _PARAM_FIRMWARE, _PARAM_RESOLUTION]
        for auth in self._auths():
            try:
                r = self._client.get(
                    f"{self.base_url}{_PATH_GETPARAM}",
                    params="&".join(keys),
                    auth=auth,
                    timeout=_TIMEOUT,
                )
                if r.status_code == 200:
                    self._working_auth = auth
                    parsed = _parse_vivotek_params(r.text)
                    return {
                        "model":      parsed.get(_PARAM_MODEL, ""),
                        "serial":     parsed.get(_PARAM_SERIAL, ""),
                        "firmware":   parsed.get(_PARAM_FIRMWARE, ""),
                        "resolution": parsed.get(_PARAM_RESOLUTION, ""),
                    }
            except Exception:
                continue
        return {"model": "", "serial": "", "firmware": "", "resolution": ""}

    def snapshot(self) -> bytes:
        """
        Retrieve a single JPEG frame.
        Tries Basic Auth first, then Digest, across all known snapshot paths.
        Caches the working (auth, path) combination for fast subsequent calls.
        """
        # If we already know the working path, go straight to it
        if self._snapshot_path and self._working_auth is not None:
            try:
                r = self._client.get(
                    f"{self.base_url}{self._snapshot_path}",
                    auth=self._working_auth,
                    timeout=_SNAPSHOT_TIMEOUT,
                )
                if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
                    return r.content
            except Exception:
                pass
            # Cached combo failed — fall through to full discovery
            self._snapshot_path = None
            self._working_auth  = None

        paths = _SNAPSHOT_PATHS
        diagnostics: list[str] = []

        for auth in self._auths():
            auth_label = "Basic" if isinstance(auth, tuple) else "Digest"
            for path in paths:
                try:
                    r = self._client.get(
                        f"{self.base_url}{path}",
                        auth=auth,
                        timeout=_SNAPSHOT_TIMEOUT,
                    )
                    ct = r.headers.get("content-type", "")
                    if r.status_code == 200 and "image" in ct:
                        self._working_auth  = auth
                        self._snapshot_path = path
                        return r.content
                    diagnostics.append(f"[{auth_label}] {path} → HTTP {r.status_code}")
                except Exception as exc:
                    diagnostics.append(f"[{auth_label}] {path} → {exc}")

        raise RuntimeError(
            "Snapshot failed:\n" + "\n".join(f"  {d}" for d in diagnostics)
        )

    def mjpeg_url(self) -> str:
        """
        IT9388/IT9380 do not expose an HTTP MJPEG endpoint — all viewer CGI
        paths return 404. Live preview uses JPEG snapshot polling instead.
        This method is retained for interface compatibility but is not used
        by the cameras router (which falls back to snapshot polling).
        """
        return f"{self.base_url}{_SNAPSHOT_PATHS[0]}"

    def _auths(self) -> list:
        """Return auth methods with the known-working one first."""
        if self._working_auth is not None:
            others = [a for a in (self._basic_auth, self._digest_auth)
                      if a is not self._working_auth]
            return [self._working_auth] + others
        return [self._basic_auth, self._digest_auth]

    def get_param(self, *keys: str) -> dict[str, str]:
        for auth in self._auths():
            try:
                r = self._client.get(
                    f"{self.base_url}{_PATH_GETPARAM}",
                    params="&".join(keys),
                    auth=auth,
                    timeout=_TIMEOUT,
                )
                if r.status_code == 200:
                    self._working_auth = auth
                    return _parse_vivotek_params(r.text)
            except Exception:
                continue
        return {}

    def set_param(self, params: dict[str, str]) -> bool:
        for auth in self._auths():
            try:
                r = self._client.post(
                    f"{self.base_url}{_PATH_SETPARAM}",
                    data=params, auth=auth, timeout=_TIMEOUT,
                )
                if r.status_code == 200:
                    self._working_auth = auth
                    return True
            except Exception:
                continue
        return False

    def close(self) -> None:
        self._client.close()


def _parse_vivotek_params(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        result[key.strip()] = val.strip().strip("'\"")
    return result
