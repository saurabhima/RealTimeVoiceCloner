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


def cmd_serve(args):
    from .remote import serve
    from . import server_runners as sr
    if args.runner == "knnvc":
        if not args.voice:
            raise SystemExit("--voice is required (create it with: rtvc enroll)")
        runner = sr.knnvc_runner(args.voice, args.topk, args.hub, args.device)
    else:
        runner = sr.identity_runner()
    print(f"serving '{args.runner}' on {args.host}:{args.port} (no auth: trusted network only)")
    serve(runner, args.host, args.port)


def cmd_enroll(args):
    from .server_runners import build_voice
    n = build_voice(args.wavs, args.out, args.hub, args.device)
    print(f"saved {n} feature frames (~{n * 0.02 / 60:.1f} min of speech) to {args.out}")


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
        sp.add_argument("--backend", choices=["passthrough", "pitch", "onnx", "remote"])
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
    sv = sub.add_parser("serve", help="host a neural model for the Pi (run on a laptop/desktop)")
    sv.add_argument("--runner", choices=["identity", "knnvc"], default="knnvc")
    sv.add_argument("--voice", help="feature bank made by `rtvc enroll`")
    sv.add_argument("--host", default="127.0.0.1"); sv.add_argument("--port", type=int, default=9000)
    sv.add_argument("--topk", type=int, default=4)
    sv.add_argument("--hub", default="bshall/knn-vc"); sv.add_argument("--device", default="auto")
    sv.set_defaults(fn=cmd_serve)
    en = sub.add_parser("enroll", help="build a target-voice feature bank from wav files (needs [server] extra)")
    en.add_argument("--out", required=True); en.add_argument("--hub", default="bshall/knn-vc")
    en.add_argument("--device", default="auto"); en.add_argument("wavs", nargs="+")
    en.set_defaults(fn=cmd_enroll)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
