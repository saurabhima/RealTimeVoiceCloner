from __future__ import annotations

import numpy as np

from ..dsp import PhaseVocoderPitchShifter
from .base import Backend


class PassthroughBackend(Backend):
    """No conversion. Use to validate audio routing and levels."""

    name = "passthrough"

    def process(self, x: np.ndarray) -> np.ndarray:
        return x


class PitchBackend(Backend):
    """DSP-only voice changer (no model, no GPU). Good first-run fallback."""

    name = "pitch"

    def __init__(self, semitones: float, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._ps = PhaseVocoderPitchShifter(semitones, sample_rate)

    @property
    def latency(self) -> int:
        return self._ps.latency

    def process(self, x: np.ndarray) -> np.ndarray:
        return self._ps.process(x)

    def reset(self) -> None:
        self._ps.reset()
