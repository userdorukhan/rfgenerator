"""
Command-line interface for the RF Generator.

Usage examples
--------------
Generate a 1 MHz sine wave for 1 ms and write a CSV file::

    python -m rfgenerator generate \\
        --frequency 1e6 --waveform sine --duration 1e-3 \\
        --output signal.csv

Generate an FM-modulated 100 MHz carrier and write a WAV file::

    python -m rfgenerator modulate fm \\
        --carrier-frequency 100e6 --mod-frequency 1000 \\
        --deviation 75e3 --duration 1e-3 \\
        --output fm_signal.wav

Run a linear frequency sweep from 1 MHz to 10 MHz::

    python -m rfgenerator sweep \\
        --start 1e6 --stop 10e6 --duration 1e-3 --mode linear \\
        --output sweep.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from .modulation import AmplitudeModulation, FrequencyModulation
from .output import CsvExporter, WavExporter
from .signal_generator import SignalGenerator, Waveform
from .sweep import FrequencySweep, SweepMode


def _waveform(value: str) -> Waveform:
    try:
        return Waveform(value.lower())
    except ValueError:
        choices = ", ".join(w.value for w in Waveform)
        raise argparse.ArgumentTypeError(
            f"invalid waveform '{value}'.  Choose from: {choices}"
        )


def _sweep_mode(value: str) -> SweepMode:
    try:
        return SweepMode(value.lower())
    except ValueError:
        choices = ", ".join(m.value for m in SweepMode)
        raise argparse.ArgumentTypeError(
            f"invalid sweep mode '{value}'.  Choose from: {choices}"
        )


def _export(path: str, t: np.ndarray, signal: np.ndarray, sample_rate: int) -> None:
    """Export signal to *path*; format is inferred from the file extension."""
    p = Path(path)
    ext = p.suffix.lower()

    if ext == ".csv":
        exporter = CsvExporter()
        out = exporter.export(p, t, signal)
        print(f"Exported CSV to: {out}")
    elif ext in (".wav", ".wave"):
        exporter = WavExporter(sample_rate=sample_rate)
        out = exporter.export(p, signal)
        print(f"Exported WAV to: {out}")
    else:
        print(
            f"Unknown file extension '{ext}'.  "
            "Supported formats: .csv, .wav",
            file=sys.stderr,
        )
        sys.exit(1)


# -----------------------------------------------------------------------
# Sub-command: generate
# -----------------------------------------------------------------------

def cmd_generate(args: argparse.Namespace) -> None:
    gen = SignalGenerator(
        frequency=args.frequency,
        amplitude=args.amplitude,
        phase=args.phase,
        waveform=args.waveform,
        sample_rate=args.sample_rate,
        dc_offset=args.dc_offset,
    )
    t, signal = gen.generate(args.duration)

    print(
        f"Generated {args.waveform.value} wave: "
        f"f={args.frequency:.3g} Hz, A={args.amplitude} V, "
        f"duration={args.duration:.3g} s, samples={len(signal)}"
    )

    if args.output:
        _export(args.output, t, signal, args.sample_rate)
    else:
        print("No --output specified; signal not saved.")


# -----------------------------------------------------------------------
# Sub-command: modulate
# -----------------------------------------------------------------------

def cmd_modulate(args: argparse.Namespace) -> None:
    carrier = SignalGenerator(
        frequency=args.carrier_frequency,
        amplitude=args.amplitude,
        phase=args.carrier_phase,
        sample_rate=args.sample_rate,
    )

    if args.mod_type == "am":
        mod = AmplitudeModulation(
            carrier=carrier,
            modulation_frequency=args.mod_frequency,
            modulation_index=args.mod_index,
            modulation_phase=args.mod_phase,
        )
        label = (
            f"AM carrier={args.carrier_frequency:.3g} Hz "
            f"mod={args.mod_frequency:.3g} Hz "
            f"index={args.mod_index}"
        )
    elif args.mod_type == "fm":
        mod = FrequencyModulation(
            carrier=carrier,
            modulation_frequency=args.mod_frequency,
            frequency_deviation=args.deviation,
            modulation_phase=args.mod_phase,
        )
        label = (
            f"FM carrier={args.carrier_frequency:.3g} Hz "
            f"mod={args.mod_frequency:.3g} Hz "
            f"deviation={args.deviation:.3g} Hz"
        )
    else:  # pragma: no cover
        print(f"Unknown modulation type: {args.mod_type}", file=sys.stderr)
        sys.exit(1)

    t, signal = mod.generate(args.duration)
    print(f"Generated {label}, samples={len(signal)}")

    if args.output:
        _export(args.output, t, signal, args.sample_rate)
    else:
        print("No --output specified; signal not saved.")


# -----------------------------------------------------------------------
# Sub-command: sweep
# -----------------------------------------------------------------------

def cmd_sweep(args: argparse.Namespace) -> None:
    sweep = FrequencySweep(
        start_frequency=args.start,
        stop_frequency=args.stop,
        amplitude=args.amplitude,
        phase=args.phase,
        waveform=args.waveform,
        sample_rate=args.sample_rate,
        mode=args.mode,
    )
    t, signal = sweep.generate(args.duration)

    print(
        f"Generated {args.mode.value} sweep: "
        f"{args.start:.3g} Hz → {args.stop:.3g} Hz, "
        f"duration={args.duration:.3g} s, samples={len(signal)}"
    )

    if args.output:
        _export(args.output, t, signal, args.sample_rate)
    else:
        print("No --output specified; signal not saved.")


# -----------------------------------------------------------------------
# Argument parser
# -----------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rfgenerator",
        description="RF Generator – Engineering Solutions at Berkeley Consulting",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- shared arguments ------------------------------------------------
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--duration",
        type=float,
        default=1e-3,
        metavar="SECONDS",
        help="Signal duration in seconds (default: 1e-3)",
    )
    shared.add_argument(
        "--amplitude",
        type=float,
        default=1.0,
        metavar="VOLTS",
        help="Peak amplitude in Volts (default: 1.0)",
    )
    shared.add_argument(
        "--sample-rate",
        type=int,
        default=1_000_000,
        metavar="HZ",
        help="Sample rate in Hz (default: 1 000 000)",
    )
    shared.add_argument(
        "--output",
        type=str,
        default=None,
        metavar="FILE",
        help="Output file path (.csv or .wav)",
    )

    # -- generate --------------------------------------------------------
    gen_p = subparsers.add_parser(
        "generate",
        parents=[shared],
        help="Generate a single-frequency carrier signal",
    )
    gen_p.add_argument("--frequency", type=float, required=True, metavar="HZ")
    gen_p.add_argument(
        "--waveform",
        type=_waveform,
        default=Waveform.SINE,
        metavar="SHAPE",
        help="Waveform shape: sine, square, triangle, sawtooth (default: sine)",
    )
    gen_p.add_argument("--phase", type=float, default=0.0, metavar="DEG")
    gen_p.add_argument("--dc-offset", type=float, default=0.0, metavar="VOLTS")
    gen_p.set_defaults(func=cmd_generate)

    # -- modulate --------------------------------------------------------
    mod_p = subparsers.add_parser(
        "modulate",
        parents=[shared],
        help="Generate an AM or FM modulated signal",
    )
    mod_p.add_argument(
        "mod_type",
        choices=["am", "fm"],
        help="Modulation type",
    )
    mod_p.add_argument("--carrier-frequency", type=float, required=True, metavar="HZ")
    mod_p.add_argument("--carrier-phase", type=float, default=0.0, metavar="DEG")
    mod_p.add_argument("--mod-frequency", type=float, required=True, metavar="HZ")
    mod_p.add_argument("--mod-phase", type=float, default=0.0, metavar="DEG")
    mod_p.add_argument(
        "--mod-index",
        type=float,
        default=1.0,
        metavar="[0,1]",
        help="AM modulation index (default: 1.0)",
    )
    mod_p.add_argument(
        "--deviation",
        type=float,
        default=75_000.0,
        metavar="HZ",
        help="FM peak frequency deviation in Hz (default: 75 000)",
    )
    mod_p.set_defaults(func=cmd_modulate)

    # -- sweep -----------------------------------------------------------
    sweep_p = subparsers.add_parser(
        "sweep",
        parents=[shared],
        help="Generate a frequency-swept (chirp) signal",
    )
    sweep_p.add_argument("--start", type=float, required=True, metavar="HZ")
    sweep_p.add_argument("--stop", type=float, required=True, metavar="HZ")
    sweep_p.add_argument(
        "--mode",
        type=_sweep_mode,
        default=SweepMode.LINEAR,
        metavar="MODE",
        help="Sweep mode: linear, logarithmic (default: linear)",
    )
    sweep_p.add_argument(
        "--waveform",
        type=_waveform,
        default=Waveform.SINE,
        metavar="SHAPE",
        help="Waveform shape (default: sine)",
    )
    sweep_p.add_argument("--phase", type=float, default=0.0, metavar="DEG")
    sweep_p.set_defaults(func=cmd_sweep)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
