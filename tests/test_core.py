import numpy as np

from rtvc.backends.chunked import ChunkedBackend
from rtvc.config import AudioCfg, BackendCfg, GateCfg
from rtvc.backends import create_backend
from rtvc.dsp import NoiseGate, PhaseVocoderPitchShifter
from rtvc.pipeline import VoicePipeline
from rtvc.audio_io import RingBuffer


def peak_hz(x, sr):
    s = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    return np.argmax(s) * sr / len(x)


def sine(f, sr, secs=1.0):
    return (0.5 * np.sin(2 * np.pi * f * np.arange(int(sr * secs)) / sr)).astype(np.float32)


def feed(proc, x, blk):
    return np.concatenate([proc.process(x[i:i + blk]) for i in range(0, len(x), blk)])


def test_pitch_shift_up_fifth():
    sr = 16000
    y = feed(PhaseVocoderPitchShifter(7, sr), sine(220, sr, 1.5), 320)
    assert len(y) == 24000
    assert abs(peak_hz(y[8000:], sr) - 220 * 2 ** (7 / 12)) < 12


def test_pitch_zero_preserves_level():
    sr = 16000
    x = sine(300, sr)
    y = feed(PhaseVocoderPitchShifter(0, sr), x, 320)
    assert 0.8 < np.std(y[8000:]) / np.std(x) < 1.2


def test_chunked_identity_recovers_input():
    sr = 16000
    b = ChunkedBackend(lambda a: a, sr, chunk=3200, context=6400, xfade=320)
    x = np.random.default_rng(0).standard_normal(sr * 2).astype(np.float32) * 0.1
    y = feed(b, x, 320)
    lat = b.latency
    assert np.allclose(y[lat + 3200:], x[3200: len(y) - lat], atol=1e-5)


def test_gate_silences_noise_passes_speech():
    g = NoiseGate(16000)
    quiet = np.full(320, 1e-4, np.float32)
    for _ in range(3):
        out = g.process(quiet)
    assert np.max(np.abs(out)) == 0
    loud = sine(200, 16000, 0.02)
    g.process(loud)
    assert np.allclose(g.process(loud), loud)


def test_pipeline_length_and_limit_with_resampling():
    cfg = AudioCfg(device_rate=48000)
    pipe = VoicePipeline(cfg, GateCfg(), create_backend(BackendCfg(name="pitch")))
    y = feed(pipe, sine(200, 48000, 1.0) * 1.9, pipe.block)
    assert len(y) == 48000 and np.max(np.abs(y)) <= 0.89


def test_ring_buffer_wraps_and_underruns():
    r = RingBuffer(8)
    r.write(np.arange(6, dtype=np.float32)); r.read(4)
    r.write(np.arange(6, 11, dtype=np.float32))
    assert list(r.read(7)) == [4, 5, 6, 7, 8, 9, 10]
    assert r.read(2).tolist() == [0, 0] and r.underruns == 1
