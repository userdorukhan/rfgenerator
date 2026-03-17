"""
Quick-start examples for the RF Generator library.

Run with:
    python examples/quickstart.py
"""

import sys
import os

# Allow running without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
from rfgenerator import (
    SignalGenerator,
    Waveform,
    AmplitudeModulation,
    FrequencyModulation,
    FrequencySweep,
    SweepMode,
    WavExporter,
    CsvExporter,
)

OUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUT_DIR, exist_ok=True)


def example_basic_sine():
    print("--- Basic 1 kHz sine wave ---")
    gen = SignalGenerator(
        frequency=1_000.0,
        amplitude=1.0,
        waveform=Waveform.SINE,
        sample_rate=44_100,
    )
    t, signal = gen.generate(duration=0.01)
    print(f"  Samples: {len(signal)}, peak: {signal.max():.4f} V")

    exporter = CsvExporter()
    out = exporter.export(os.path.join(OUT_DIR, "sine_1kHz.csv"), t, signal)
    print(f"  Saved → {out}\n")


def example_square_wave():
    print("--- Square wave (50 Hz) ---")
    gen = SignalGenerator(
        frequency=50.0,
        amplitude=3.3,
        waveform=Waveform.SQUARE,
        sample_rate=44_100,
    )
    t, signal = gen.generate(duration=0.1)
    print(f"  Samples: {len(signal)}, peak: {signal.max():.4f} V")

    exporter = WavExporter(sample_rate=44_100)
    out = exporter.export(os.path.join(OUT_DIR, "square_50Hz.wav"), signal)
    print(f"  Saved → {out}\n")


def example_am_modulation():
    print("--- AM modulation: 100 kHz carrier, 1 kHz message, m=0.5 ---")
    carrier = SignalGenerator(frequency=100_000, amplitude=1.0, sample_rate=1_000_000)
    am = AmplitudeModulation(carrier, modulation_frequency=1_000, modulation_index=0.5)
    t, signal = am.generate(duration=1e-3)
    print(f"  Samples: {len(signal)}, peak: {signal.max():.4f} V")

    exporter = CsvExporter()
    out = exporter.export(os.path.join(OUT_DIR, "am_100kHz.csv"), t, signal)
    print(f"  Saved → {out}\n")


def example_fm_modulation():
    print("--- FM modulation: 100 kHz carrier, 1 kHz message, Δf=5 kHz (β=5) ---")
    carrier = SignalGenerator(frequency=100_000, amplitude=1.0, sample_rate=1_000_000)
    fm = FrequencyModulation(
        carrier,
        modulation_frequency=1_000,
        frequency_deviation=5_000,
    )
    print(f"  Modulation index β = {fm.modulation_index}")
    t, signal = fm.generate(duration=1e-3)
    print(f"  Samples: {len(signal)}, peak: {abs(signal).max():.4f} V")

    exporter = CsvExporter()
    out = exporter.export(os.path.join(OUT_DIR, "fm_100kHz.csv"), t, signal)
    print(f"  Saved → {out}\n")


def example_frequency_sweep():
    print("--- Linear frequency sweep: 1 kHz → 10 kHz over 100 ms ---")
    sweep = FrequencySweep(
        start_frequency=1_000,
        stop_frequency=10_000,
        amplitude=1.0,
        sample_rate=44_100,
        mode=SweepMode.LINEAR,
    )
    t, signal = sweep.generate(duration=0.1)
    print(f"  Samples: {len(signal)}, peak: {signal.max():.4f} V")

    exporter = WavExporter(sample_rate=44_100)
    out = exporter.export(os.path.join(OUT_DIR, "sweep_1k_10k.wav"), signal)
    print(f"  Saved → {out}\n")


def example_log_sweep():
    print("--- Logarithmic sweep: 100 Hz → 10 kHz over 200 ms ---")
    sweep = FrequencySweep(
        start_frequency=100,
        stop_frequency=10_000,
        amplitude=1.0,
        sample_rate=44_100,
        mode=SweepMode.LOGARITHMIC,
    )
    t, signal = sweep.generate(duration=0.2)
    print(f"  Samples: {len(signal)}, peak: {signal.max():.4f} V")

    exporter = CsvExporter()
    out = exporter.export(os.path.join(OUT_DIR, "log_sweep_100_10k.csv"), t, signal)
    print(f"  Saved → {out}\n")


if __name__ == "__main__":
    example_basic_sine()
    example_square_wave()
    example_am_modulation()
    example_fm_modulation()
    example_frequency_sweep()
    example_log_sweep()
    print("All examples complete.  Output files written to:", OUT_DIR)
