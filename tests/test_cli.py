"""
Integration tests for the CLI module.
"""

import csv
import wave
from pathlib import Path

import numpy as np
import pytest

from rfgenerator.cli import main


class TestCLIGenerate:
    def test_generate_sine_csv(self, tmp_path):
        out = tmp_path / "sine.csv"
        rc = main([
            "generate",
            "--frequency", "1000",
            "--waveform", "sine",
            "--duration", "0.01",
            "--sample-rate", "44100",
            "--output", str(out),
        ])
        assert rc == 0
        assert out.exists()

    def test_generate_square_wav(self, tmp_path):
        out = tmp_path / "square.wav"
        rc = main([
            "generate",
            "--frequency", "1000",
            "--waveform", "square",
            "--duration", "0.01",
            "--sample-rate", "44100",
            "--output", str(out),
        ])
        assert rc == 0
        assert out.exists()
        with wave.open(str(out)) as wf:
            assert wf.getnframes() > 0

    def test_generate_no_output_succeeds(self, capsys):
        rc = main([
            "generate",
            "--frequency", "1000",
            "--duration", "0.001",
        ])
        assert rc == 0
        captured = capsys.readouterr()
        assert "sine" in captured.out

    def test_generate_with_dc_offset(self, tmp_path):
        out = tmp_path / "dc.csv"
        rc = main([
            "generate",
            "--frequency", "1000",
            "--dc-offset", "0.5",
            "--duration", "0.01",
            "--sample-rate", "10000",
            "--output", str(out),
        ])
        assert rc == 0

    def test_invalid_waveform_exits(self):
        with pytest.raises(SystemExit):
            main(["generate", "--frequency", "1000", "--waveform", "notawaveform"])


class TestCLIModulate:
    def test_am_csv(self, tmp_path):
        out = tmp_path / "am.csv"
        rc = main([
            "modulate", "am",
            "--carrier-frequency", "100000",
            "--mod-frequency", "1000",
            "--mod-index", "0.8",
            "--duration", "0.001",
            "--sample-rate", "1000000",
            "--output", str(out),
        ])
        assert rc == 0
        assert out.exists()

    def test_fm_csv(self, tmp_path):
        out = tmp_path / "fm.csv"
        rc = main([
            "modulate", "fm",
            "--carrier-frequency", "100000",
            "--mod-frequency", "1000",
            "--deviation", "5000",
            "--duration", "0.001",
            "--sample-rate", "1000000",
            "--output", str(out),
        ])
        assert rc == 0
        assert out.exists()

    def test_modulate_no_output_succeeds(self, capsys):
        rc = main([
            "modulate", "am",
            "--carrier-frequency", "100000",
            "--mod-frequency", "1000",
            "--duration", "0.001",
        ])
        assert rc == 0


class TestCLISweep:
    def test_linear_sweep_csv(self, tmp_path):
        out = tmp_path / "sweep.csv"
        rc = main([
            "sweep",
            "--start", "1000",
            "--stop", "5000",
            "--mode", "linear",
            "--duration", "0.01",
            "--sample-rate", "44100",
            "--output", str(out),
        ])
        assert rc == 0
        assert out.exists()

    def test_log_sweep_csv(self, tmp_path):
        out = tmp_path / "log_sweep.csv"
        rc = main([
            "sweep",
            "--start", "1000",
            "--stop", "10000",
            "--mode", "logarithmic",
            "--duration", "0.01",
            "--sample-rate", "44100",
            "--output", str(out),
        ])
        assert rc == 0
        assert out.exists()

    def test_sweep_no_output_succeeds(self, capsys):
        rc = main([
            "sweep",
            "--start", "1000",
            "--stop", "5000",
            "--duration", "0.001",
        ])
        assert rc == 0
