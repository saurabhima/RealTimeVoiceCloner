# Plugging in a neural voice-conversion model

The `onnx` backend runs any model that satisfies this contract (see `backends/onnx_vc.py`):

| | |
|---|---|
| Input 0 | `float32 [1, N]` mono audio at `backend.onnx.sample_rate` |
| Optional input `speaker`/`spk`/`target` | `float32` target-voice embedding from `speaker_embedding` (.npy) |
| Output 0 | `float32 [1, N]` or `[N]`, same length and rate as the input |

Each call receives `context_ms + chunk_ms` of audio; the stream is cross-faded across `crossfade_ms`.

Tips for the Pi:
* Export a content-encoder + vocoder pipeline (e.g. RVC, FreeVC, kNN-VC) to ONNX; quantise to int8 if needed.
* Real-time means inference time per call **< chunk_ms**. `rtvc run` prints `proc max X/Y ms` every 5 s.
* Pi 4: expect ~150-250 ms chunks for small models. Pi 5 handles larger ones. If too slow, use `backend = "pitch"`.
* Only use target voices you have consent to use; check the model's licence.
