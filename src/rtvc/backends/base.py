from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class Backend(ABC):
    """A streaming voice converter.

    Contract: `process` receives mono float32 at `sample_rate` in chunks of any
    size (including zero) and returns the SAME number of samples, delayed by
    `latency` samples. Implementations keep their own state.
    """

    name = "base"
    sample_rate = 16000

    @property
    def latency(self) -> int:
        return 0

    @abstractmethod
    def process(self, x: np.ndarray) -> np.ndarray: ...

    def reset(self) -> None:  # pragma: no cover - default no-op
        pass
