"""
Tests for the core SignalGenerator class.
"""

import math

import numpy as np
import pytest

from rfgenerator.signal_generator import SignalGenerator, Waveform


class TestSignalGeneratorValidation:
    def test_negative_frequency_raises(self):
        with pytest.raises(ValueError, match="frequency"):
            SignalGenerator(frequency=-1.0)

    def test_zero_frequency_raises(self):
        with pytest.raises(ValueError, match="frequency"):
            SignalGenerator(frequency=0.0)

    def test_negative_sample_rate_raises(self):
        with pytest.raises(ValueError, match="sample_rate"):
            SignalGenerator(frequency=1e6, sample_rate=-1)

    def test_negative_amplitude_raises(self):
        with pytest.raises(ValueError, match="amplitude"):
            SignalGenerator(frequency=1e6, amplitude=-0.5)

    def test_zero_duration_raises(self):
        gen = SignalGenerator(frequency=1e6)
        with pytest.raises(ValueError, match="duration"):
            gen.generate(0.0)

    def test_negative_duration_raises(self):
        gen = SignalGenerator(frequency=1e6)
        with pytest.raises(ValueError, match="duration"):
            gen.generate(-1e-3)


class TestSignalGeneratorProperties:
    def test_period(self):
        gen = SignalGenerator(frequency=1000.0)
        assert math.isclose(gen.period, 1e-3)

    def test_angular_frequency(self):
        gen = SignalGenerator(frequency=1.0)
        assert math.isclose(gen.angular_frequency, 2.0 * math.pi)


class TestSignalGeneratorOutputShape:
    def test_output_length(self):
        sr = 10_000
        duration = 0.5
        gen = SignalGenerator(frequency=100.0, sample_rate=sr)
        t, signal = gen.generate(duration)
        expected = int(sr * duration)
        assert len(t) == expected
        assert len(signal) == expected

    def test_time_axis_starts_at_zero(self):
        gen = SignalGenerator(frequency=100.0, sample_rate=10_000)
        t, _ = gen.generate(0.1)
        assert t[0] == pytest.approx(0.0)

    def test_generate_samples_matches_generate(self):
        gen = SignalGenerator(frequency=100.0, sample_rate=10_000)
        t, sig1 = gen.generate(0.1)
        sig2 = gen.generate_samples(t)
        np.testing.assert_array_almost_equal(sig1, sig2)


class TestSineWave:
    def test_amplitude(self):
        gen = SignalGenerator(frequency=1000.0, amplitude=2.5, sample_rate=100_000)
        _, signal = gen.generate(0.01)
        assert np.max(signal) == pytest.approx(2.5, rel=1e-3)
        assert np.min(signal) == pytest.approx(-2.5, rel=1e-3)

    def test_zero_phase_starts_near_zero(self):
        """A sine wave with 0° phase should start near 0 V."""
        gen = SignalGenerator(frequency=1000.0, phase=0.0, sample_rate=1_000_000)
        t, signal = gen.generate(1e-3)
        assert abs(signal[0]) < 0.01

    def test_90_degree_phase_starts_near_peak(self):
        """A sine wave with 90° phase should start near the peak."""
        gen = SignalGenerator(frequency=1000.0, amplitude=1.0, phase=90.0,
                              sample_rate=1_000_000)
        t, signal = gen.generate(1e-3)
        assert abs(signal[0] - 1.0) < 0.01

    def test_dc_offset(self):
        gen = SignalGenerator(frequency=1000.0, amplitude=1.0, dc_offset=0.5,
                              sample_rate=100_000)
        _, signal = gen.generate(0.01)
        assert np.mean(signal) == pytest.approx(0.5, abs=0.02)


class TestSquareWave:
    def test_values_are_plus_minus_amplitude(self):
        gen = SignalGenerator(frequency=100.0, amplitude=1.5, waveform=Waveform.SQUARE,
                              sample_rate=100_000)
        _, signal = gen.generate(0.1)
        unique = np.unique(np.round(signal, 6))
        assert set(unique).issubset({-1.5, 0.0, 1.5})

    def test_duty_cycle_near_50_percent(self):
        gen = SignalGenerator(frequency=100.0, amplitude=1.0, waveform=Waveform.SQUARE,
                              sample_rate=100_000)
        _, signal = gen.generate(1.0)
        positive_fraction = np.sum(signal > 0) / len(signal)
        assert positive_fraction == pytest.approx(0.5, abs=0.01)


class TestTriangleWave:
    def test_amplitude_bounds(self):
        gen = SignalGenerator(frequency=100.0, amplitude=2.0, waveform=Waveform.TRIANGLE,
                              sample_rate=100_000)
        _, signal = gen.generate(0.1)
        assert np.max(signal) == pytest.approx(2.0, rel=1e-3)
        assert np.min(signal) == pytest.approx(-2.0, rel=1e-3)

    def test_mean_near_zero(self):
        gen = SignalGenerator(frequency=100.0, amplitude=1.0, waveform=Waveform.TRIANGLE,
                              sample_rate=100_000)
        _, signal = gen.generate(1.0)
        assert np.mean(signal) == pytest.approx(0.0, abs=0.01)


class TestSawtoothWave:
    def test_amplitude_bounds(self):
        gen = SignalGenerator(frequency=100.0, amplitude=1.0, waveform=Waveform.SAWTOOTH,
                              sample_rate=100_000)
        _, signal = gen.generate(0.1)
        assert np.max(signal) <= 1.0 + 1e-9
        assert np.min(signal) >= -1.0 - 1e-9
