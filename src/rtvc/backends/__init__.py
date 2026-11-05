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
    if cfg.name == "remote":
        from ..remote import RemoteRunner
        from .chunked import ChunkedBackend
        r = cfg.remote
        ms = lambda v: int(r.sample_rate * v / 1000)  # noqa: E731
        return ChunkedBackend(RemoteRunner(r.host, r.port, r.timeout_ms), r.sample_rate,
                              ms(r.chunk_ms), ms(r.context_ms), ms(r.crossfade_ms))
    raise ValueError(f"unknown backend: {cfg.name}")


__all__ = ["Backend", "create_backend"]
