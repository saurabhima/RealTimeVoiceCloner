"""Model runners hosted by `rtvc serve` (run these on a laptop/desktop, not the Pi)."""
from __future__ import annotations

from typing import Callable

import numpy as np

Runner = Callable[[np.ndarray], np.ndarray]


def identity_runner() -> Runner:
    return lambda x: x


def _knnvc(hub: str, device: str):
    import torch
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    kw = dict(source="local") if not hub.count("/") == 1 or hub.startswith(("/", ".")) else {}
    model = torch.hub.load(hub, "knn_vc", prematched=True, trust_repo=True, pretrained=True,
                           device=device, **kw)
    return torch, model


def build_voice(wavs: list[str], out: str, hub: str = "bshall/knn-vc", device: str = "auto") -> int:
    """Enroll a target voice from 16-bit PCM .wav files (the kNN-VC paper uses ~5-8 min of clean speech; more = better). Saves a feature bank."""
    import soxr
    from .wavio import read_wav
    torch, knn = _knnvc(hub, device)
    clips = []
    for path in wavs:  # load ourselves: avoids torchaudio's backend/codec requirements
        x, sr = read_wav(path)
        x = soxr.resample(x, sr, 16000) if sr != 16000 else x
        clips.append(torch.from_numpy(np.ascontiguousarray(x, np.float32))[None])
    feats = knn.get_matching_set(clips)
    torch.save(feats, out)
    return feats.shape[0]


def knnvc_runner(voice: str, topk: int = 4, hub: str = "bshall/knn-vc", device: str = "auto",
                 auto_gain: bool = True) -> Runner:
    """kNN-VC (Baas et al. 2023): WavLM features of the source are replaced by the mean of their
    k nearest neighbours in the target voice's feature bank, then vocoded by HiFi-GAN.
    Any-to-one; no training needed."""
    torch, knn = _knnvc(hub, device)
    bank = torch.load(voice, map_location="cpu").to(knn.device)
    gain = [1.0]  # smoothed across windows so level follows the speaker without pumping

    def run(x: np.ndarray) -> np.ndarray:
        with torch.inference_mode():
            q = knn.get_features(torch.from_numpy(x)[None].to(knn.device), vad_trigger_level=0)
            y = knn.match(q, bank, topk=topk, tgt_loudness_db=None).cpu().numpy().astype(np.float32)
        y = y[: len(x)] if len(y) >= len(x) else np.pad(y, (0, len(x) - len(y)))
        if auto_gain:
            r_in, r_out = float(np.sqrt(np.mean(x * x))), float(np.sqrt(np.mean(y * y)))
            if r_in > 0.005 and r_out > 1e-5:  # only adapt on voiced windows
                gain[0] = 0.8 * gain[0] + 0.2 * min(r_in / r_out, 30.0)
            y = np.clip(y * gain[0], -1.0, 1.0)
        return y

    return run
