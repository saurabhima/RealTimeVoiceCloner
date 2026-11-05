"""Hardware-independent processing chain: gate -> resample -> convert -> resample -> limit."""
from __future__ import annotations

import numpy as np
import soxr

from .backends.base import Backend
from .config import AudioCfg, GateCfg
from .dsp import NoiseGate, db_to_lin, soft_limit


class VoicePipeline:
    def __init__(self, audio: AudioCfg, gate: GateCfg, backend: Backend):
        self.backend = backend
        self.rate = audio.device_rate
        self.gate = NoiseGate(self.rate, gate.open_db, gate.close_db, gate.hold_ms)
        self.in_gain = db_to_lin(audio.input_gain_db)
        self.out_gain = db_to_lin(audio.output_gain_db)
        m = backend.sample_rate
        self._down = soxr.ResampleStream(self.rate, m, 1, dtype="float32") if m != self.rate else None
        self._up = soxr.ResampleStream(m, self.rate, 1, dtype="float32") if m != self.rate else None
        self._fifo = np.zeros(0, np.float32)
        self._primed = False
        self.block = int(self.rate * audio.block_ms / 1000)

    @property
    def latency_ms(self) -> float:
        return 1000.0 * (self.backend.latency / self.backend.sample_rate + 2 * self.block / self.rate)

    def process(self, x: np.ndarray) -> np.ndarray:
        """x: mono float32 at device rate. Returns the same number of samples."""
        n = len(x)
        if not self._primed:  # one block of jitter headroom
            self._fifo = np.zeros(n, np.float32)
            self._primed = True
        y = self.gate.process(x * self.in_gain)
        if self._down:
            y = self._down.resample_chunk(y)
        y = self.backend.process(np.ascontiguousarray(y, np.float32))
        if self._up:
            y = self._up.resample_chunk(y)
        self._fifo = np.concatenate([self._fifo, y])
        out, self._fifo = self._fifo[:n], self._fifo[n:]
        if len(out) < n:
            out = np.pad(out, (0, n - len(out)))
        return soft_limit(out * self.out_gain)
