"""
Tests for the output exporters (WAV and CSV).
"""

import csv
import wave
from pathlib import Path

import numpy as np
import pytest

from rfgenerator.output import CsvExporter, WavExporter
from rfgenerator.signal_generator import SignalGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_signal(freq: float = 1000.0, duration: float = 0.1,
                sr: int = 44_100) -> tuple[np.ndarray, np.ndarray]:
    gen = SignalGenerator(frequency=freq, amplitude=1.0, sample_rate=sr)
    return gen.generate(duration)


# ---------------------------------------------------------------------------
# WavExporter
# ---------------------------------------------------------------------------

class TestWavExporter:
    def test_creates_file(self, tmp_path):
        t, signal = make_signal()
        exporter = WavExporter(sample_rate=44_100)
        out = exporter.export(tmp_path / "out.wav", signal)
        assert out.exists()

    def test_wav_metadata(self, tmp_path):
        t, signal = make_signal(sr=44_100)
        exporter = WavExporter(sample_rate=44_100)
        out = exporter.export(tmp_path / "out.wav", signal)

        with wave.open(str(out), "r") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2  # 16-bit
            assert wf.getframerate() == 44_100
            assert wf.getnframes() == len(signal)

    def test_normalised_peak(self, tmp_path):
        """With normalise=True the peak int16 value should be MAX_AMPLITUDE."""
        t, signal = make_signal()
        exporter = WavExporter(sample_rate=44_100)
        out = exporter.export(tmp_path / "out.wav", signal, normalise=True)

        with wave.open(str(out), "r") as wf:
            raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        assert np.max(np.abs(raw)) == WavExporter.MAX_AMPLITUDE

    def test_all_zero_signal_does_not_crash(self, tmp_path):
        signal = np.zeros(1000)
        exporter = WavExporter(sample_rate=44_100)
        out = exporter.export(tmp_path / "zeros.wav", signal)
        assert out.exists()

    def test_invalid_sample_rate_raises(self):
        with pytest.raises(ValueError, match="sample_rate"):
            WavExporter(sample_rate=0)

    def test_non_1d_array_raises(self, tmp_path):
        exporter = WavExporter()
        with pytest.raises(ValueError, match="1-D"):
            exporter.export(tmp_path / "bad.wav", np.zeros((10, 2)))


# ---------------------------------------------------------------------------
# CsvExporter
# ---------------------------------------------------------------------------

class TestCsvExporter:
    def test_creates_file(self, tmp_path):
        t, signal = make_signal()
        exporter = CsvExporter()
        out = exporter.export(tmp_path / "out.csv", t, signal)
        assert out.exists()

    def test_header_row(self, tmp_path):
        t, signal = make_signal(duration=0.01)
        exporter = CsvExporter()
        out = exporter.export(tmp_path / "out.csv", t, signal)

        with out.open() as fh:
            reader = csv.reader(fh)
            header = next(reader)
        assert header == ["time_s", "voltage_V"]

    def test_row_count(self, tmp_path):
        t, signal = make_signal(sr=1000, duration=0.1)
        exporter = CsvExporter()
        out = exporter.export(tmp_path / "out.csv", t, signal)

        with out.open() as fh:
            rows = list(csv.reader(fh))
        # One header + one row per sample
        assert len(rows) == len(t) + 1

    def test_roundtrip_values(self, tmp_path):
        t, signal = make_signal(sr=1000, duration=0.01)
        exporter = CsvExporter()
        out = exporter.export(tmp_path / "out.csv", t, signal)

        t_loaded, v_loaded = [], []
        with out.open() as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                t_loaded.append(float(row["time_s"]))
                v_loaded.append(float(row["voltage_V"]))

        np.testing.assert_allclose(np.array(t_loaded), t, rtol=1e-6)
        np.testing.assert_allclose(np.array(v_loaded), signal, rtol=1e-6)

    def test_mismatched_shapes_raise(self, tmp_path):
        exporter = CsvExporter()
        with pytest.raises(ValueError, match="same shape"):
            exporter.export(tmp_path / "bad.csv", np.zeros(5), np.zeros(4))
