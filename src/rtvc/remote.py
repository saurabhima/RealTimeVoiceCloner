"""Remote inference: the Pi streams audio windows to a stronger machine over TCP.

Wire format (both directions, little-endian): uint32 n_samples, then n float32 samples.
The server returns exactly the number of samples it received.
There is NO authentication or encryption: bind to a trusted LAN, or tunnel with SSH/WireGuard.
"""
from __future__ import annotations

import socket
import struct
import threading
import time
from typing import Callable

import numpy as np

MAX_SAMPLES = 16000 * 30  # sanity cap per message


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            raise ConnectionError("peer closed")
        buf += part
    return bytes(buf)


def send_audio(sock: socket.socket, x: np.ndarray) -> None:
    x = np.ascontiguousarray(x, dtype="<f4")
    sock.sendall(struct.pack("<I", len(x)) + x.tobytes())


def recv_audio(sock: socket.socket) -> np.ndarray:
    (n,) = struct.unpack("<I", _recv_exact(sock, 4))
    if n > MAX_SAMPLES:
        raise ValueError(f"message too large: {n} samples")
    return np.frombuffer(_recv_exact(sock, 4 * n), dtype="<f4").astype(np.float32)


class RemoteRunner:
    """Client-side runner. Fails CLOSED: if the server is unreachable or slow it
    returns silence, never the unconverted microphone audio."""

    def __init__(self, host: str, port: int, timeout_ms: int = 800, retry_s: float = 2.0):
        self.addr, self.timeout, self.retry_s = (host, port), timeout_ms / 1000, retry_s
        self._sock: socket.socket | None = None
        self._next_try = 0.0
        self.failures = 0

    def _connect(self) -> bool:
        if time.monotonic() < self._next_try:
            return False
        try:
            s = socket.create_connection(self.addr, timeout=self.timeout)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(self.timeout)
            self._sock = s
            return True
        except OSError:
            self._next_try = time.monotonic() + self.retry_s
            return False

    def close(self):
        if self._sock:
            self._sock.close()
        self._sock = None

    def __call__(self, window: np.ndarray) -> np.ndarray:
        if self._sock is None and not self._connect():
            self.failures += 1
            return np.zeros_like(window)
        try:
            send_audio(self._sock, window)
            y = recv_audio(self._sock)
            if len(y) != len(window):
                raise ValueError("length mismatch")
            return y
        except (OSError, ValueError, ConnectionError):
            self.close()
            self._next_try = time.monotonic() + self.retry_s
            self.failures += 1
            return np.zeros_like(window)


def serve(runner: Callable[[np.ndarray], np.ndarray], host: str = "127.0.0.1", port: int = 9000,
          ready: threading.Event | None = None, stop: threading.Event | None = None) -> None:
    """Blocking TCP server; one thread per client."""
    stop = stop or threading.Event()
    lock = threading.Lock()  # models are not thread-safe: serialise inference

    def handle(conn: socket.socket):
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        with conn:
            while not stop.is_set():
                try:
                    x = recv_audio(conn)
                except (ConnectionError, OSError, ValueError):
                    return
                with lock:
                    y = np.asarray(runner(x), np.float32).reshape(-1)
                if len(y) < len(x):
                    y = np.pad(y, (0, len(x) - len(y)))
                send_audio(conn, y[: len(x)])

    with socket.socket() as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, port))
        srv.listen(4)
        srv.settimeout(0.2)
        if ready:
            ready.set()
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            threading.Thread(target=handle, args=(conn,), daemon=True).start()
