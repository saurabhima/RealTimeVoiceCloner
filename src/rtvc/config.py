from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path


@dataclass
class AudioCfg:
    input_device: str = ""
    output_device: str = ""
    device_rate: int = 48000
    block_ms: int = 20
    output_channels: int = 2
    input_gain_db: float = 0.0
    output_gain_db: float = -12.0


@dataclass
class GateCfg:
    open_db: float = -45.0
    close_db: float = -50.0
    hold_ms: int = 200


@dataclass
class PitchCfg:
    semitones: float = 4.0


@dataclass
class OnnxCfg:
    model: str = "models/vc.onnx"
    sample_rate: int = 16000
    chunk_ms: int = 200
    context_ms: int = 400
    crossfade_ms: int = 20
    speaker_embedding: str = ""


@dataclass
class BackendCfg:
    name: str = "pitch"
    pitch: PitchCfg = field(default_factory=PitchCfg)
    onnx: OnnxCfg = field(default_factory=OnnxCfg)


@dataclass
class Config:
    consent_acknowledged: bool = False
    audio: AudioCfg = field(default_factory=AudioCfg)
    gate: GateCfg = field(default_factory=GateCfg)
    backend: BackendCfg = field(default_factory=BackendCfg)


def _merge(obj, data: dict, path: str = ""):
    names = {f.name for f in fields(obj)}
    for key, val in data.items():
        if key not in names:
            raise ValueError(f"unknown config key: {path}{key}")
        cur = getattr(obj, key)
        if is_dataclass(cur):
            _merge(cur, val, f"{path}{key}.")
        else:
            setattr(obj, key, type(cur)(val))
    return obj


def load_config(path: str | Path | None) -> Config:
    cfg = Config()
    if path:
        with open(path, "rb") as fh:
            _merge(cfg, tomllib.load(fh))
    return cfg
