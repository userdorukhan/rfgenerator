"""
Frequency sweep module.

Provides :class:`FrequencySweep`, which generates a signal whose carrier
frequency changes continuously from a start frequency to a stop frequency
over a specified duration (a *chirp*).
"""

from __future__ import annotations

import enum
import math

import numpy as np

from .signal_generator import SignalGenerator, Waveform


class SweepMode(enum.Enum):
    """Frequency trajectory for the sweep."""

    LINEAR = "linear"      # f(t) = f_start + (f_stop - f_start) * t / T
    LOGARITHMIC = "logarithmic"  # log sweep (equal octaves per unit time)


class FrequencySweep:
    """Generate a frequency-swept (chirp) signal.

    The instantaneous frequency changes from *start_frequency* to
    *stop_frequency* over the specified *duration*.  The phase is computed
    by integrating the instantaneous frequency so that there are no
    discontinuities at the start or end of the sweep.

    Parameters
    ----------
    start_frequency:
        Starting carrier frequency in Hz.  Must be positive.
    stop_frequency:
        Ending carrier frequency in Hz.  Must be positive and different
        from *start_frequency*.
    amplitude:
        Peak amplitude in Volts.  Defaults to 1.0 V.
    phase:
        Initial phase offset in degrees.  Defaults to 0°.
    waveform:
        Output waveform shape.  Defaults to :attr:`~rfgenerator.Waveform.SINE`.
        Only ``SINE`` produces a theoretically exact chirp; other waveforms
        apply the same phase to their respective shape function.
    sample_rate:
        Number of samples per second.  Defaults to 1 MHz.
    mode:
        Frequency trajectory – linear or logarithmic.
    """

    def __init__(
        self,
        start_frequency: float,
        stop_frequency: float,
        amplitude: float = 1.0,
        phase: float = 0.0,
        waveform: Waveform = Waveform.SINE,
        sample_rate: int = 1_000_000,
        mode: SweepMode = SweepMode.LINEAR,
    ) -> None:
        if start_frequency <= 0:
            raise ValueError(
                f"start_frequency must be positive, got {start_frequency}"
            )
        if stop_frequency <= 0:
            raise ValueError(
                f"stop_frequency must be positive, got {stop_frequency}"
            )
        if start_frequency == stop_frequency:
            raise ValueError("start_frequency and stop_frequency must differ")
        if sample_rate <= 0:
            raise ValueError(f"sample_rate must be positive, got {sample_rate}")
        if amplitude < 0:
            raise ValueError(f"amplitude must be non-negative, got {amplitude}")

        self.start_frequency = start_frequency
        self.stop_frequency = stop_frequency
        self.amplitude = amplitude
        self.phase = phase
        self.waveform = waveform
        self.sample_rate = sample_rate
        self.mode = mode

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, duration: float) -> tuple[np.ndarray, np.ndarray]:
        """Generate a swept signal of the given *duration* (seconds).

        Returns
        -------
        time : np.ndarray
            Time axis in seconds.
        signal : np.ndarray
            Output voltage in Volts.
        """
        if duration <= 0:
            raise ValueError(f"duration must be positive, got {duration}")

        num_samples = int(self.sample_rate * duration)
        t = np.linspace(0.0, duration, num_samples, endpoint=False)
        instantaneous_phase = self._integrated_phase(t, duration)

        if self.waveform is Waveform.SINE:
            wave = np.sin(instantaneous_phase)
        elif self.waveform is Waveform.SQUARE:
            wave = np.sign(np.sin(instantaneous_phase))
        elif self.waveform is Waveform.TRIANGLE:
            wave = (2.0 / math.pi) * np.arcsin(np.sin(instantaneous_phase))
        elif self.waveform is Waveform.SAWTOOTH:
            # Normalise phase to [0, 2π) then map to [-1, 1)
            norm = (instantaneous_phase % (2.0 * math.pi)) / (2.0 * math.pi)
            wave = 2.0 * norm - 1.0
        else:  # pragma: no cover
            raise ValueError(f"Unknown waveform: {self.waveform}")

        signal = self.amplitude * wave
        return t, signal

    def instantaneous_frequency(self, duration: float) -> tuple[np.ndarray, np.ndarray]:
        """Return the instantaneous frequency profile over *duration*.

        Returns
        -------
        time : np.ndarray
        frequency : np.ndarray
            Instantaneous frequency at each time point in Hz.
        """
        if duration <= 0:
            raise ValueError(f"duration must be positive, got {duration}")

        num_samples = int(self.sample_rate * duration)
        t = np.linspace(0.0, duration, num_samples, endpoint=False)
        f = self._instantaneous_freq(t, duration)
        return t, f

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _instantaneous_freq(self, t: np.ndarray, duration: float) -> np.ndarray:
        """Compute the instantaneous frequency at each time point."""
        f0 = self.start_frequency
        f1 = self.stop_frequency
        T = duration

        if self.mode is SweepMode.LINEAR:
            return f0 + (f1 - f0) * t / T
        else:  # LOGARITHMIC
            # f(t) = f0 * (f1/f0)^(t/T)  -- use log to avoid overflow
            log_ratio = math.log(f1 / f0)
            return f0 * np.exp(log_ratio * t / T)

    def _integrated_phase(self, t: np.ndarray, duration: float) -> np.ndarray:
        """Compute the integrated (unwrapped) phase θ(t) = ∫ 2π·f(τ)dτ + φ₀."""
        f0 = self.start_frequency
        f1 = self.stop_frequency
        T = duration
        phi0 = math.radians(self.phase)

        if self.mode is SweepMode.LINEAR:
            # ∫₀ᵗ f(τ)dτ = f0·t + (f1-f0)/(2T) · t²
            return 2.0 * math.pi * (f0 * t + (f1 - f0) / (2.0 * T) * t**2) + phi0
        else:  # LOGARITHMIC
            # ∫₀ᵗ f0·exp(ln(f1/f0)·τ/T) dτ = f0·T/ln(f1/f0) · (exp(ln(f1/f0)·t/T) - 1)
            log_ratio = math.log(f1 / f0)
            return (
                2.0 * math.pi * f0 * T / log_ratio * (np.exp(log_ratio * t / T) - 1.0)
                + phi0
            )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"FrequencySweep({self.start_frequency} Hz → {self.stop_frequency} Hz, "
            f"amplitude={self.amplitude} V, mode={self.mode.value}, "
            f"sample_rate={self.sample_rate} Hz)"
        )
