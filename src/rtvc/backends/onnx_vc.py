from __future__ import annotations

from pathlib import Path

import numpy as np

from ..config import OnnxCfg
from .chunked import ChunkedBackend


def make_onnx_backend(cfg: OnnxCfg) -> ChunkedBackend:
    """Load an ONNX voice-conversion model.

    Model contract (export your RVC / kNN-VC / FreeVC-style model to match):
      * input 0 : float32 [1, N] mono audio at cfg.sample_rate
      * optional input named 'speaker' / 'spk' / 'target': float32 embedding
        loaded from cfg.speaker_embedding (.npy)
      * output 0: float32 [1, N] or [N], same length and rate as the input
    """
    try:
        import onnxruntime as ort
    except ImportError as e:  # pragma: no cover
        raise SystemExit("onnx backend needs: pip install 'realtime-voice-cloner[onnx]'") from e
    path = Path(cfg.model)
    if not path.is_file():
        raise SystemExit(f"model not found: {path} (see docs/MODELS.md)")
    so = ort.SessionOptions()
    so.intra_op_num_threads = 3  # leave one Pi core for audio I/O
    sess = ort.InferenceSession(str(path), so, providers=["CPUExecutionProvider"])
    inputs = [i.name for i in sess.get_inputs()]
    spk = None
    if cfg.speaker_embedding:
        spk = np.load(cfg.speaker_embedding).astype(np.float32)
    spk_name = next((n for n in inputs[1:] if n.lower() in ("speaker", "spk", "target")), None)
    if spk_name and spk is None:
        raise SystemExit(f"model needs a '{spk_name}' input; set backend.onnx.speaker_embedding")

    def runner(audio: np.ndarray) -> np.ndarray:
        feed = {inputs[0]: audio[None, :]}
        if spk_name:
            feed[spk_name] = spk
        return np.asarray(sess.run(None, feed)[0]).reshape(-1)

    ms = lambda v: int(cfg.sample_rate * v / 1000)  # noqa: E731
    return ChunkedBackend(runner, cfg.sample_rate, ms(cfg.chunk_ms), ms(cfg.context_ms),
                          ms(cfg.crossfade_ms))
