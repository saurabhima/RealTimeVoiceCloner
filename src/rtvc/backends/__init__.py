from __future__ import annotations

from ..config import BackendCfg
from .base import Backend
from .simple import PassthroughBackend, PitchBackend


def create_backend(cfg: BackendCfg) -> Backend:
    if cfg.name == "passthrough":
        return PassthroughBackend()
    if cfg.name == "pitch":
        return PitchBackend(cfg.pitch.semitones)
    if cfg.name == "onnx":
        from .onnx_vc import make_onnx_backend
        return make_onnx_backend(cfg.onnx)
    raise ValueError(f"unknown backend: {cfg.name}")


__all__ = ["Backend", "create_backend"]
