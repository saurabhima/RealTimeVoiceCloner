"""Small, dependency-light DSP building blocks (numpy only)."""
from __future__ import annotations

import numpy as np


def db_to_lin(db: float) -> float:
    return float(10.0 ** (db / 20.0))


def rms_db(x: np.ndarray) -> float:
    if x.size == 0:
        return -120.0
    return 20.0 * np.log10(float(np.sqrt(np.mean(x * x))) + 1e-9)


def soft_limit(x: np.ndarray, ceiling: float = 0.89) -> np.ndarray:
    """tanh limiter: transparent below ~0.5, never exceeds `ceiling`."""
    return (ceiling * np.tanh(x / ceiling)).astype(np.float32)


class NoiseGate:
    """Block-level gate with hysteresis, hold time and click-free gain ramps."""

    def __init__(self, sample_rate: int, open_db=-45.0, close_db=-50.0, hold_ms=200):
        self.open_db, self.close_db = open_db, close_db
        self.hold_samples = int(sample_rate * hold_ms / 1000)
        self._open = False
        self._hold = 0
        self._gain = 0.0

    def process(self, x: np.ndarray) -> np.ndarray:
        level = rms_db(x)
        if level >= self.open_db:
            self._open, self._hold = True, self.hold_samples
        elif self._open and level < self.close_db:
            self._hold -= len(x)
            if self._hold <= 0:
                self._open = False
        else:
            self._hold = self.hold_samples if self._open else 0
        target = 1.0 if self._open else 0.0
        if self._gain == target == 1.0:
            return x
        ramp = np.linspace(self._gain, target, len(x), dtype=np.float32)
        self._gain = target
        return x * ramp


class PhaseVocoderPitchShifter:
    """Streaming pitch shifter (phase vocoder with bin remapping).

    Feed arbitrary-sized chunks to `process`; it returns exactly as many samples,
    delayed by `latency` samples. Pure numpy, runs well within budget on a Pi 4.
    """

    def __init__(self, semitones: float, sample_rate: int = 16000, n_fft: int = 1024):
        self.ratio = 2.0 ** (semitones / 12.0)
        self.n = n_fft
        self.hop = n_fft // 4
        self.sample_rate = sample_rate
        self.win = np.hanning(n_fft + 1)[:-1].astype(np.float32)
        self.omega = 2 * np.pi * np.arange(n_fft // 2 + 1) * self.hop / n_fft
        bins = np.arange(n_fft // 2 + 1)
        tgt = np.round(bins * self.ratio).astype(int)
        keep = tgt <= n_fft // 2
        self._src, self._tgt = bins[keep], tgt[keep]
        self.reset()

    @property
    def latency(self) -> int:
        return self.n

    def reset(self):
        nb = self.n // 2 + 1
        self._in = np.zeros(0, np.float32)
        self._acc = np.zeros(self.n, np.float32)
        self._fifo = np.zeros(self.n, np.float32)  # primes output with latency
        self._last_phase = np.zeros(nb)
        self._syn_phase = np.zeros(nb)

    def _frame(self, frame: np.ndarray) -> np.ndarray:
        spec = np.fft.rfft(frame * self.win)
        mag, phase = np.abs(spec), np.angle(spec)
        dphi = phase - self._last_phase - self.omega
        self._last_phase = phase
        dphi -= 2 * np.pi * np.round(dphi / (2 * np.pi))
        freq = self.omega + dphi  # per-hop phase advance of true frequency
        nmag = np.zeros_like(mag)
        nfreq = np.zeros_like(freq)
        np.add.at(nmag, self._tgt, mag[self._src])
        nfreq[self._tgt] = freq[self._src] * self.ratio
        self._syn_phase += nfreq
        out = np.fft.irfft(nmag * np.exp(1j * self._syn_phase), self.n)
        return (out * self.win / 1.5).astype(np.float32)  # hann^2 @75% overlap = 1.5

    def process(self, x: np.ndarray) -> np.ndarray:
        n_req = len(x)
        self._in = np.concatenate([self._in, x.astype(np.float32, copy=False)])
        while len(self._in) >= self.n:
            self._acc += self._frame(self._in[: self.n])
            self._fifo = np.concatenate([self._fifo, self._acc[: self.hop]])
            self._acc = np.concatenate([self._acc[self.hop:], np.zeros(self.hop, np.float32)])
            self._in = self._in[self.hop:]
        out = self._fifo[:n_req]
        self._fifo = self._fifo[n_req:]
        if len(out) < n_req:
            out = np.pad(out, (0, n_req - len(out)))
        return out
