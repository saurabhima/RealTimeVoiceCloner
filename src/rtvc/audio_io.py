"""Live audio engine: USB mic -> pipeline -> output device (3.5mm jack / USB dongle)."""
from __future__ import annotations

import queue
import threading
import time

import numpy as np

from .config import AudioCfg
from .pipeline import VoicePipeline


class RingBuffer:
    """Single-producer/single-consumer float32 ring. Drops oldest on overflow."""

    def __init__(self, capacity: int):
        self.buf = np.zeros(capacity, np.float32)
        self.cap, self.r, self.size = capacity, 0, 0
        self.lock = threading.Lock()
        self.overflows = self.underruns = 0

    def write(self, x: np.ndarray):
        with self.lock:
            if len(x) > self.cap - self.size:
                drop = len(x) - (self.cap - self.size)
                self.r, self.size = (self.r + drop) % self.cap, self.size - drop
                self.overflows += 1
            w = (self.r + self.size) % self.cap
            first = min(len(x), self.cap - w)
            self.buf[w: w + first] = x[:first]
            self.buf[: len(x) - first] = x[first:]
            self.size += len(x)

    def read(self, n: int) -> np.ndarray:
        out = np.zeros(n, np.float32)
        with self.lock:
            k = min(n, self.size)
            if k < n:
                self.underruns += 1
            first = min(k, self.cap - self.r)
            out[:first] = self.buf[self.r: self.r + first]
            out[first:k] = self.buf[: k - first]
            self.r, self.size = (self.r + k) % self.cap, self.size - k
        return out


def _sd():
    import sounddevice as sd  # lazy: needs the PortAudio system library
    return sd


def list_devices() -> str:
    sd = _sd()
    return str(sd.query_devices())


def find_device(spec: str, kind: str):
    """Resolve a device by index or case-insensitive name substring ('' = default)."""
    if spec == "":
        return None
    if spec.isdigit():
        return int(spec)
    sd = _sd()
    key = "max_input_channels" if kind == "input" else "max_output_channels"
    for i, d in enumerate(sd.query_devices()):
        if spec.lower() in d["name"].lower() and d[key] > 0:
            return i
    raise SystemExit(f"no {kind} device matching '{spec}'. Run: rtvc devices")


class Engine:
    def __init__(self, cfg: AudioCfg, pipeline: VoicePipeline):
        self.cfg, self.pipe = cfg, pipeline
        self.block = pipeline.block
        self._inq: queue.Queue[np.ndarray] = queue.Queue(maxsize=64)
        self._ring = RingBuffer(cfg.device_rate)  # 1 s
        self._stop = threading.Event()
        self.in_overflows = 0
        self.max_proc_ms = 0.0

    def _in_cb(self, indata, frames, t, status):
        if status:
            self.in_overflows += 1
        try:
            self._inq.put_nowait(indata[:, 0].copy())
        except queue.Full:
            self.in_overflows += 1

    def _out_cb(self, outdata, frames, t, status):
        outdata[:] = self._ring.read(frames)[:, None]

    def _worker(self):
        while not self._stop.is_set():
            try:
                x = self._inq.get(timeout=0.1)
            except queue.Empty:
                continue
            t0 = time.perf_counter()
            self._ring.write(self.pipe.process(x))
            self.max_proc_ms = max(self.max_proc_ms, 1000 * (time.perf_counter() - t0))

    def run(self):
        sd, c = _sd(), self.cfg
        in_dev, out_dev = find_device(c.input_device, "input"), find_device(c.output_device, "output")
        budget = 1000.0 * self.block / c.device_rate
        print(f"pipeline latency ~{self.pipe.latency_ms:.0f} ms, block {budget:.0f} ms")
        th = threading.Thread(target=self._worker, daemon=True)
        th.start()
        with sd.InputStream(device=in_dev, channels=1, samplerate=c.device_rate,
                            blocksize=self.block, dtype="float32", callback=self._in_cb), \
             sd.OutputStream(device=out_dev, channels=c.output_channels, samplerate=c.device_rate,
                             blocksize=self.block, dtype="float32", callback=self._out_cb):
            print("running; Ctrl+C to stop")
            try:
                while True:
                    time.sleep(5)
                    flag = "  <-- SLOWER THAN REAL TIME" if self.max_proc_ms > budget else ""
                    print(f"proc max {self.max_proc_ms:.1f}/{budget:.0f} ms  "
                          f"underruns {self._ring.underruns}  overflows {self._ring.overflows + self.in_overflows}{flag}")
                    self.max_proc_ms = 0.0
            except KeyboardInterrupt:
                pass
            finally:
                self._stop.set()
                th.join(timeout=1)
