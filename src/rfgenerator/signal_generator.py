"""
Core RF signal generation module.

Provides :class:`SignalGenerator`, which synthesises common periodic
waveforms at arbitrary carrier frequencies, amplitudes, and phases.
"""

from __future__ import annotations

import enum
import math
from typing import Sequence

import numpy as np


class Waveform(enum.Enum):
    """Supported carrier waveform shapes."""

    SINE = "sine"
    SQUARE = "square"
    TRIANGLE = "triangle"
    SAWTOOTH = "sawtooth"


class SignalGenerator:
    """Software RF signal generator.

    Parameters
    ----------
    frequency:
        Carrier frequency in Hz.  Must be positive.
    amplitude:
        Peak amplitude in Volts.  Defaults to 1.0 V.
    phase:
        Initial phase offset in degrees.  Defaults to 0°.
    waveform:
        Carrier waveform shape.  Defaults to :attr:`Waveform.SINE`.
    sample_rate:
        Number of samples per second.  Defaults to 1 MHz.
    dc_offset:
        DC bias added to the output signal.  Defaults to 0 V.
    """

    def __init__(
        self,
        frequency: float,
        amplitude: float = 1.0,
        phase: float = 0.0,
        waveform: Waveform = Waveform.SINE,
        sample_rate: int = 1_000_000,
        dc_offset: float = 0.0,
    ) -> None:
        if frequency <= 0:
            raise ValueError(f"frequency must be positive, got {frequency}")
        if sample_rate <= 0:
            raise ValueError(f"sample_rate must be positive, got {sample_rate}")
        if amplitude < 0:
            raise ValueError(f"amplitude must be non-negative, got {amplitude}")

        self.frequency = frequency
        self.amplitude = amplitude
        self.phase = phase
        self.waveform = waveform
        self.sample_rate = sample_rate
        self.dc_offset = dc_offset

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, duration: float) -> tuple[np.ndarray, np.ndarray]:
        """Generate a signal of the given *duration* in seconds.

        Returns
        -------
        time : np.ndarray
            Time axis in seconds.
        signal : np.ndarray
            Instantaneous voltage values in Volts.
        """
        if duration <= 0:
            raise ValueError(f"duration must be positive, got {duration}")

        num_samples = int(self.sample_rate * duration)
        t = np.linspace(0.0, duration, num_samples, endpoint=False)
        signal = self._synthesise(t, self.frequency, self.amplitude, self.phase)
        return t, signal

    def generate_samples(
        self, time_axis: "np.ndarray | Sequence[float]"
    ) -> np.ndarray:
        """Generate signal values for an arbitrary *time_axis* array.

        Parameters
        ----------
        time_axis:
            Array of time points in seconds at which to evaluate the signal.

        Returns
        -------
        np.ndarray
            Signal values in Volts corresponding to each time point.
        """
        t = np.asarray(time_axis, dtype=float)
        return self._synthesise(t, self.frequency, self.amplitude, self.phase)

    # ------------------------------------------------------------------
    # Properties (read-write with validation)
    # ------------------------------------------------------------------

    @property
    def period(self) -> float:
        """Signal period in seconds."""
        return 1.0 / self.frequency

    @property
    def angular_frequency(self) -> float:
        """Angular frequency ω = 2π·f  (rad/s)."""
        return 2.0 * math.pi * self.frequency

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"SignalGenerator(frequency={self.frequency} Hz, "
            f"amplitude={self.amplitude} V, phase={self.phase}°, "
            f"waveform={self.waveform.value}, "
            f"sample_rate={self.sample_rate} Hz)"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _synthesise(
        self,
        t: np.ndarray,
        frequency: float,
        amplitude: float,
        phase_deg: float,
    ) -> np.ndarray:
        """Evaluate the chosen waveform at time points *t*."""
        phase_rad = math.radians(phase_deg)
        theta = 2.0 * math.pi * frequency * t + phase_rad

        if self.waveform is Waveform.SINE:
            wave = np.sin(theta)
        elif self.waveform is Waveform.SQUARE:
            wave = np.sign(np.sin(theta))
        elif self.waveform is Waveform.TRIANGLE:
            # Triangle wave via arcsin of sine
            wave = (2.0 / math.pi) * np.arcsin(np.sin(theta))
        elif self.waveform is Waveform.SAWTOOTH:
            # Sawtooth rising from -1 to +1 over each period
            wave = 2.0 * (t * frequency - np.floor(t * frequency + 0.5 - phase_deg / 360.0))
        else:  # pragma: no cover
            raise ValueError(f"Unknown waveform: {self.waveform}")

        return amplitude * wave + self.dc_offset
