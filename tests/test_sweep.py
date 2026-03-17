"""
Tests for the FrequencySweep module.
"""

import math

import numpy as np
import pytest

from rfgenerator.signal_generator import Waveform
from rfgenerator.sweep import FrequencySweep, SweepMode


class TestFrequencySweepValidation:
    def test_zero_start_raises(self):
        with pytest.raises(ValueError, match="start_frequency"):
            FrequencySweep(start_frequency=0.0, stop_frequency=1e6)

    def test_zero_stop_raises(self):
        with pytest.raises(ValueError, match="stop_frequency"):
            FrequencySweep(start_frequency=1e6, stop_frequency=0.0)

    def test_equal_frequencies_raises(self):
        with pytest.raises(ValueError, match="differ"):
            FrequencySweep(start_frequency=1e6, stop_frequency=1e6)

    def test_negative_amplitude_raises(self):
        with pytest.raises(ValueError, match="amplitude"):
            FrequencySweep(start_frequency=1e6, stop_frequency=2e6, amplitude=-1.0)

    def test_negative_duration_raises(self):
        sweep = FrequencySweep(start_frequency=1e6, stop_frequency=2e6)
        with pytest.raises(ValueError, match="duration"):
            sweep.generate(-1e-3)


class TestFrequencySweepOutputShape:
    def test_output_length_linear(self):
        sr = 1_000_000
        duration = 1e-3
        sweep = FrequencySweep(1e6, 2e6, sample_rate=sr, mode=SweepMode.LINEAR)
        t, signal = sweep.generate(duration)
        expected = int(sr * duration)
        assert len(t) == expected
        assert len(signal) == expected

    def test_output_length_log(self):
        sr = 1_000_000
        duration = 1e-3
        sweep = FrequencySweep(1e6, 2e6, sample_rate=sr, mode=SweepMode.LOGARITHMIC)
        t, signal = sweep.generate(duration)
        expected = int(sr * duration)
        assert len(t) == expected
        assert len(signal) == expected


class TestLinearSweepFrequency:
    def test_starts_at_start_frequency(self):
        sweep = FrequencySweep(1e6, 2e6, sample_rate=1_000_000, mode=SweepMode.LINEAR)
        _, freq = sweep.instantaneous_frequency(1e-3)
        assert freq[0] == pytest.approx(1e6)

    def test_ends_at_stop_frequency(self):
        sweep = FrequencySweep(1e6, 2e6, sample_rate=1_000_000, mode=SweepMode.LINEAR)
        _, freq = sweep.instantaneous_frequency(1e-3)
        assert freq[-1] == pytest.approx(2e6, rel=1e-3)

    def test_linear_profile(self):
        """The frequency profile should be linear."""
        sweep = FrequencySweep(1e6, 2e6, sample_rate=1_000_000, mode=SweepMode.LINEAR)
        t, freq = sweep.instantaneous_frequency(1e-3)
        # Fit a line; residuals should be tiny
        coeffs = np.polyfit(t, freq, 1)
        expected_slope = (2e6 - 1e6) / 1e-3
        assert coeffs[0] == pytest.approx(expected_slope, rel=1e-6)


class TestLogarithmicSweepFrequency:
    def test_starts_at_start_frequency(self):
        sweep = FrequencySweep(1e6, 10e6, sample_rate=1_000_000,
                               mode=SweepMode.LOGARITHMIC)
        _, freq = sweep.instantaneous_frequency(1e-3)
        assert freq[0] == pytest.approx(1e6)

    def test_ends_at_stop_frequency(self):
        sweep = FrequencySweep(1e6, 10e6, sample_rate=1_000_000,
                               mode=SweepMode.LOGARITHMIC)
        _, freq = sweep.instantaneous_frequency(1e-3)
        # The last sample is one step before the endpoint, so allow ~0.5% tolerance
        assert freq[-1] == pytest.approx(10e6, rel=5e-3)


class TestSweepAmplitude:
    def test_sine_amplitude(self):
        sweep = FrequencySweep(1e6, 2e6, amplitude=2.0, sample_rate=1_000_000,
                               mode=SweepMode.LINEAR)
        _, signal = sweep.generate(1e-3)
        assert np.max(np.abs(signal)) == pytest.approx(2.0, rel=0.01)
