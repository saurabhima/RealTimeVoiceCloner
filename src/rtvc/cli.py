from __future__ import annotations

import argparse

import numpy as np

from .config import load_config
from .pipeline import VoicePipeline
from .backends import create_backend
from .wavio import read_wav, write_wav


def _build(args):
    cfg = load_config(args.config)
    if getattr(args, "backend", None):
        cfg.backend.name = args.backend
    if getattr(args, "semitones", None) is not None:
        cfg.backend.pitch.semitones = args.semitones
    for k in ("input_device", "output_device"):
        if getattr(args, k, None) is not None:
            setattr(cfg.audio, k, getattr(args, k))
    if getattr(args, "output_gain_db", None) is not None:
        cfg.audio.output_gain_db = args.output_gain_db
    return cfg


def cmd_devices(args):
    from .audio_io import list_devices
    print(list_devices())


def cmd_run(args):
    from .audio_io import Engine
    cfg = _build(args)
    if not (cfg.consent_acknowledged or args.accept_responsible_use):
        raise SystemExit("Refusing to start: confirm you will only convert voices you have "
                         "consent to use and will not deceive call recipients. Pass "
                         "--accept-responsible-use or set consent_acknowledged = true. See README.")
    pipe = VoicePipeline(cfg.audio, cfg.gate, create_backend(cfg.backend))
    Engine(cfg.audio, pipe).run()


def cmd_convert(args):
    cfg = _build(args)
    x, sr = read_wav(args.input)
    cfg.audio.device_rate = sr
    pipe = VoicePipeline(cfg.audio, cfg.gate, create_backend(cfg.backend))
    blk, out = pipe.block, []
    for i in range(0, len(x), blk):
        b = x[i:i + blk]
        out.append(pipe.process(np.pad(b, (0, blk - len(b)))))
    write_wav(args.output, np.concatenate(out)[: len(x)], sr)
    print(f"wrote {args.output} (backend={cfg.backend.name})")


def cmd_tone(args):
    """Play a 440 Hz tone to the output device to calibrate levels with the phone."""
    import sounddevice as sd
    from .audio_io import find_device
    cfg = _build(args)
    sr, n = cfg.audio.device_rate, cfg.audio.device_rate * args.seconds
    t = np.arange(n) / sr
    tone = (0.5 * 10 ** (cfg.audio.output_gain_db / 20) * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    sd.play(np.repeat(tone[:, None], cfg.audio.output_channels, 1), sr,
            device=find_device(cfg.audio.output_device, "output"), blocking=True)


def main(argv=None):
    p = argparse.ArgumentParser(prog="rtvc", description="Real-time voice converter")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("-c", "--config")
        sp.add_argument("--backend", choices=["passthrough", "pitch", "onnx"])
        sp.add_argument("--semitones", type=float)
        sp.add_argument("--output-gain-db", type=float, dest="output_gain_db")

    sub.add_parser("devices", help="list audio devices").set_defaults(fn=cmd_devices)
    r = sub.add_parser("run", help="live conversion"); common(r)
    r.add_argument("--input-device", dest="input_device"); r.add_argument("--output-device", dest="output_device")
    r.add_argument("--accept-responsible-use", action="store_true")
    r.set_defaults(fn=cmd_run)
    c = sub.add_parser("convert", help="offline wav -> wav (no hardware needed)"); common(c)
    c.add_argument("input"); c.add_argument("output"); c.set_defaults(fn=cmd_convert)
    t = sub.add_parser("tone", help="output a test tone"); common(t)
    t.add_argument("--output-device", dest="output_device"); t.add_argument("--seconds", type=int, default=5)
    t.set_defaults(fn=cmd_tone)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
