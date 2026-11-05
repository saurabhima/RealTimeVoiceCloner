from __future__ import annotations

from typing import Callable

import numpy as np

from .base import Backend


class ChunkedBackend(Backend):
    """Wraps an offline `runner(audio)->audio` (same length) for streaming use.

    Each inference sees `context` samples of history plus `chunk` new samples.
    The region around the chunk boundary is cross-faded with the previous
    inference's tail, hiding model discontinuities. Latency ~= chunk + xfade
    plus inference time, so keep inference faster than real time.
    """

    name = "chunked"

    def __init__(self, runner: Callable[[np.ndarray], np.ndarray], sample_rate: int,
                 chunk: int, context: int, xfade: int):
        if not 0 < xfade <= min(context, chunk):
            raise ValueError("need 0 < xfade <= min(context, chunk)")
        self.runner, self.sample_rate = runner, sample_rate
        self.chunk, self.ctx, self.xf = chunk, context, xfade
        self._fade = np.linspace(0, 1, xfade, dtype=np.float32)
        self.reset()

    @property
    def latency(self) -> int:
        return self.chunk + self.xf

    def reset(self):
        self._hist = np.zeros(self.ctx, np.float32)
        self._pend = np.zeros(0, np.float32)
        self._tail = np.zeros(self.xf, np.float32)
        self._fifo = np.zeros(self.chunk, np.float32)

    def process(self, x: np.ndarray) -> np.ndarray:
        n_req = len(x)
        self._pend = np.concatenate([self._pend, x.astype(np.float32, copy=False)])
        while len(self._pend) >= self.chunk:
            new, self._pend = self._pend[: self.chunk], self._pend[self.chunk:]
            window = np.concatenate([self._hist, new])
            y = np.asarray(self.runner(window), np.float32)
            if len(y) != len(window):
                raise RuntimeError(f"model returned {len(y)} samples for {len(window)} in")
            c, xf = self.ctx, self.xf
            head = self._tail * (1 - self._fade) + y[c - xf: c] * self._fade
            self._fifo = np.concatenate([self._fifo, head, y[c: c + self.chunk - xf]])
            self._tail = y[c + self.chunk - xf: c + self.chunk].copy()
            self._hist = window[-self.ctx:]
        out, self._fifo = self._fifo[:n_req], self._fifo[n_req:]
        return np.pad(out, (0, n_req - len(out))) if len(out) < n_req else out
