"""
Tests for the modulation module (AM and FM).
"""

import math

import numpy as np
import pytest

from rfgenerator.modulation import AmplitudeModulation, FrequencyModulation
from rfgenerator.signal_generator import SignalGenerator


def make_carrier(freq: float = 1e6, sr: int = 10_000_000) -> SignalGenerator:
    return SignalGenerator(frequency=freq, amplitude=1.0, sample_rate=sr)


class TestAmplitudeModulationValidation:
    def test_zero_mod_frequency_raises(self):
        with pytest.raises(ValueError, match="modulation_frequency"):
            AmplitudeModulation(make_carrier(), modulation_frequency=0.0)

    def test_mod_index_above_1_raises(self):
        with pytest.raises(ValueError, match="modulation_index"):
            AmplitudeModulation(make_carrier(), modulation_frequency=1000.0,
                                modulation_index=1.5)

    def test_negative_mod_index_raises(self):
        with pytest.raises(ValueError, match="modulation_index"):
            AmplitudeModulation(make_carrier(), modulation_frequency=1000.0,
                                modulation_index=-0.1)

    def test_negative_duration_raises(self):
        am = AmplitudeModulation(make_carrier(), modulation_frequency=1000.0)
        with pytest.raises(ValueError, match="duration"):
            am.generate(-1e-3)


class TestAmplitudeModulationOutput:
    def test_output_shape(self):
        sr = 1_000_000
        duration = 1e-3
        carrier = SignalGenerator(frequency=100_000, sample_rate=sr)
        am = AmplitudeModulation(carrier, modulation_frequency=1000.0)
        t, signal = am.generate(duration)
        expected = int(sr * duration)
        assert len(t) == expected
        assert len(signal) == expected

    def test_envelope_with_full_modulation(self):
        """With m=1 the envelope should reach 2×A_c and dip to 0."""
        sr = 10_000_000
        carrier = SignalGenerator(frequency=1_000_000, amplitude=1.0, sample_rate=sr)
        am = AmplitudeModulation(carrier, modulation_frequency=1000.0,
                                 modulation_index=1.0)
        _, signal = am.generate(2e-3)
        assert np.max(np.abs(signal)) == pytest.approx(2.0, rel=0.01)
        assert np.min(np.abs(signal)) == pytest.approx(0.0, abs=0.05)

    def test_zero_modulation_index_is_pure_carrier(self):
        """m=0 should yield an unmodulated carrier."""
        sr = 10_000_000
        carrier = SignalGenerator(frequency=1_000_000, amplitude=1.0, sample_rate=sr)
        am = AmplitudeModulation(carrier, modulation_frequency=1000.0,
                                 modulation_index=0.0)
        _, signal = am.generate(1e-3)
        # Peak should be exactly 1.0
        assert np.max(np.abs(signal)) == pytest.approx(1.0, rel=0.001)


class TestFrequencyModulationValidation:
    def test_zero_mod_frequency_raises(self):
        with pytest.raises(ValueError, match="modulation_frequency"):
            FrequencyModulation(make_carrier(), modulation_frequency=0.0,
                                frequency_deviation=1000.0)

    def test_zero_deviation_raises(self):
        with pytest.raises(ValueError, match="frequency_deviation"):
            FrequencyModulation(make_carrier(), modulation_frequency=1000.0,
                                frequency_deviation=0.0)

    def test_negative_duration_raises(self):
        fm = FrequencyModulation(make_carrier(), modulation_frequency=1000.0,
                                 frequency_deviation=5000.0)
        with pytest.raises(ValueError, match="duration"):
            fm.generate(-1e-3)


class TestFrequencyModulationOutput:
    def test_output_shape(self):
        sr = 1_000_000
        duration = 1e-3
        carrier = SignalGenerator(frequency=100_000, sample_rate=sr)
        fm = FrequencyModulation(carrier, modulation_frequency=1000.0,
                                 frequency_deviation=5000.0)
        t, signal = fm.generate(duration)
        expected = int(sr * duration)
        assert len(t) == expected
        assert len(signal) == expected

    def test_constant_amplitude(self):
        """FM should not change the carrier amplitude."""
        sr = 10_000_000
        carrier = SignalGenerator(frequency=1_000_000, amplitude=1.5, sample_rate=sr)
        fm = FrequencyModulation(carrier, modulation_frequency=1000.0,
                                 frequency_deviation=10_000.0)
        _, signal = fm.generate(1e-3)
        # All values must stay within [-1.5, 1.5]
        assert np.max(np.abs(signal)) == pytest.approx(1.5, rel=0.01)

    def test_modulation_index(self):
        carrier = SignalGenerator(frequency=1_000_000)
        fm = FrequencyModulation(carrier, modulation_frequency=1000.0,
                                 frequency_deviation=5000.0)
        assert fm.modulation_index == pytest.approx(5.0)
