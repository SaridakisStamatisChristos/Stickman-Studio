"""
SFX Synthesizer - Generates synthesized sound effects locally.
No copyrighted samples. All generated programmatically.
"""

from __future__ import annotations

import array
import logging
import math
import os
import random
import struct
import wave
from typing import Callable

logger = logging.getLogger(__name__)

try:
    import numpy as np
    _NP = True
except ImportError:  # pragma: no cover
    np = None  # type: ignore
    _NP = False


class SFXSynth:
    """
    Generates common cartoon/UI sound effects via pure synthesis.
    All effects are brief (< 500 ms) and appropriate for video narration.
    """

    def __init__(self, sample_rate: int = 44100) -> None:
        self.sample_rate = sample_rate

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_sfx(self, sfx_name: str, output_path: str) -> bool:
        """
        Generate a sound effect and save to *output_path* (WAV).

        Supported names: pop, whoosh, click, impact, notification,
                         transition, footstep, success, error, swoosh.
        """
        generators: dict[str, Callable[[], bytes]] = {
            "pop":            self._generate_pop,
            "whoosh":         self._generate_whoosh,
            "click":          self._generate_click,
            "impact":         self._generate_impact,
            "notification":   self._generate_notification,
            "transition":     self._generate_transition,
            "footstep":       self._generate_footstep,
            "footsteps":      self._generate_footstep,
            "success":        self._generate_success,
            "error":          self._generate_error,
            "swoosh":         self._generate_swoosh,
            "fire_crackle":   self._generate_fire_crackle,
            "rain_ambient":   self._generate_rain_ambient,
            "taiko_hit":      self._generate_taiko_hit,
            "katana_whoosh":  self._generate_katana_whoosh,
            "chime_soft":     self._generate_chime_soft,
            "pencil_scratch": self._generate_pencil_scratch,
            "crt_static":     self._generate_crt_static,
            # Cartoon Sound Stems (Created by Atharv Hatwar)
            "boing":          self._generate_boing,
            "slide_whistle":  self._generate_slide_whistle,
            "chime_idea":     self._generate_chime_idea,
            "coin_clink":     self._generate_coin_clink,
            # Extended Audio Suite (Created by Atharv Hatwar)
            "dramatic_boom":   self._generate_dramatic_boom,
            "boom":            self._generate_dramatic_boom,
            "bass_drop":       self._generate_dramatic_boom,
            "applause_cheer":  self._generate_applause_cheer,
            "applause":        self._generate_applause_cheer,
            "cheer":           self._generate_applause_cheer,
            "keyboard_typing": self._generate_keyboard_typing,
            "typing":          self._generate_keyboard_typing,
            "keyboard":        self._generate_keyboard_typing,
            "cash_register":   self._generate_cash_register,
            "kaching":         self._generate_cash_register,
            "cash":            self._generate_cash_register,
            "magic_sparkle":   self._generate_magic_sparkle,
            "sparkle":         self._generate_magic_sparkle,
            "magic":           self._generate_magic_sparkle,
            "ding_bell":       self._generate_ding_bell,
            "ding":            self._generate_ding_bell,
            "bell":            self._generate_ding_bell,
            "punch_hit":       self._generate_punch_hit,
            "punch":           self._generate_punch_hit,
            "slap":            self._generate_punch_hit,
            "animal_bark":     self._generate_animal_bark,
            "bark":            self._generate_animal_bark,
            "dog_bark":        self._generate_animal_bark,
            "animal_meow":     self._generate_animal_meow,
            "meow":            self._generate_animal_meow,
            "cat_meow":        self._generate_animal_meow,
            "rocket_whoosh":   self._generate_rocket_whoosh,
            "rocket":          self._generate_rocket_whoosh,
            "thruster":        self._generate_rocket_whoosh,
            "clock_tick":      self._generate_clock_tick,
            "clock":           self._generate_clock_tick,
            "tick":            self._generate_clock_tick,
        }

        generator = generators.get(sfx_name.lower())
        if generator is None:
            logger.warning("Unknown SFX name '%s'", sfx_name)
            return False

        try:
            pcm_bytes = generator()
            self._save_wav(pcm_bytes, output_path)
            return True
        except Exception as exc:
            logger.error("SFX generation failed (%s): %s", sfx_name, exc, exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Individual SFX generators – each returns raw 16-bit PCM bytes
    # ------------------------------------------------------------------

    def _generate_pop(self) -> bytes:
        """Pristine melodic bubble pop at ~520 Hz with subtle octave harmonic (60 ms)."""
        dur = 0.060
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        f1, f2 = 523.25, 1046.50  # C5 + C6
        for i in range(n):
            t = i * inv_sr
            env = math.exp(-t * 60.0)
            signal[i] = (math.sin(2.0 * math.pi * f1 * t) * 0.70 + math.sin(2.0 * math.pi * f2 * t) * 0.18) * env
        return self._pcm(signal)

    def _generate_whoosh(self) -> bytes:
        """Clean harmonic cinematic sweep from 220 Hz to 780 Hz with zero white noise static (220 ms)."""
        dur = 0.220
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        phase = 0.0
        phase2 = 0.0
        for i in range(n):
            t = i * inv_sr
            frac = t / dur
            # Smooth exponential frequency glide
            freq = 220.0 * (3.5 ** frac)
            env = math.sin(math.pi * frac) ** 1.5
            signal[i] = (math.sin(phase) * 0.45 + math.sin(phase2) * 0.15) * env
            phase += 2.0 * math.pi * freq * inv_sr
            phase2 += 2.0 * math.pi * (freq * 1.5) * inv_sr
            if phase > 2.0 * math.pi:
                phase -= 2.0 * math.pi
            if phase2 > 2.0 * math.pi:
                phase2 -= 2.0 * math.pi

        return self._pcm(signal)

    def _generate_click(self) -> bytes:
        """Very short sharp acoustic click at ~1000 Hz (20 ms)."""
        dur = 0.020
        freq = 1000.0
        return self._pcm(self._sine_decay(freq, dur, amplitude=0.8, decay_rate=140.0))

    def _generate_impact(self) -> bytes:
        """Solid low sub-bass kick at ~65 Hz with exponential decay, zero distortion (160 ms)."""
        dur = 0.160
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        phase = 0.0
        for i in range(n):
            t = i * inv_sr
            # Pitch drop kick from 110 Hz down to 55 Hz
            freq = 55.0 + 55.0 * math.exp(-t / 0.035)
            phase += 2.0 * math.pi * freq * inv_sr
            env = math.exp(-t / 0.065)
            signal[i] = math.sin(phase) * 0.75 * env
            if phase > 2.0 * math.pi:
                phase -= 2.0 * math.pi

        return self._pcm(signal)

    def _generate_notification(self) -> bytes:
        """Two-tone chime: G5 (100 ms) then C6 (100 ms)."""
        g5 = self._freq_note("G5")
        c6 = self._freq_note("C6")
        part1 = self._sine_adsr(g5, 0.100, amplitude=0.5)
        part2 = self._sine_adsr(c6, 0.100, amplitude=0.5)
        return self._pcm(self._concat(part1, part2))

    def _generate_transition(self) -> bytes:
        """Smooth harmonic transition sweep from 260 Hz to 980 Hz (240 ms)."""
        dur = 0.240
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        phase = 0.0
        for i in range(n):
            t = i * inv_sr
            frac = t / dur
            freq = 260.0 + 720.0 * frac
            env = math.sin(math.pi * frac)  # fade in/out
            signal[i] = math.sin(phase) * 0.45 * env
            phase += 2.0 * math.pi * freq * inv_sr
            if phase > 2.0 * math.pi:
                phase -= 2.0 * math.pi

        return self._pcm(signal)

    def _generate_footstep(self) -> bytes:
        """Acoustic wooden marimba tap at ~120 Hz, completely free of white noise static (50 ms)."""
        dur = 0.050
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        f = 120.0
        for i in range(n):
            t = i * inv_sr
            env = math.exp(-t * 85.0)
            signal[i] = math.sin(2.0 * math.pi * f * t) * 0.40 * env

        return self._pcm(signal)

    def _generate_success(self) -> bytes:
        """C5-E5-G5 arpeggio (100 ms each note)."""
        c5 = self._freq_note("C5")
        e5 = self._freq_note("E5")
        g5 = self._freq_note("G5")
        parts = [
            self._sine_adsr(c5, 0.100, amplitude=0.5),
            self._sine_adsr(e5, 0.100, amplitude=0.5),
            self._sine_adsr(g5, 0.150, amplitude=0.5),
        ]
        return self._pcm(self._concat(*parts))

    def _generate_error(self) -> bytes:
        """Low buzzer with slight distortion at ~150 Hz (200 ms)."""
        dur = 0.200
        freq = 150.0
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        two_pi_f = 2.0 * math.pi * freq
        for i in range(n):
            t = i * inv_sr
            env = 1.0 - t / dur  # linear decay
            v = math.sin(two_pi_f * t)
            # Soft clipping / slight distortion
            v = math.tanh(v * 2.5) * 0.5
            signal[i] = v * env * 0.65

        return self._pcm(signal)

    def _generate_swoosh(self) -> bytes:
        """Falling pitch sweep from 1200 Hz down to 150 Hz (300 ms)."""
        dur = 0.300
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        phase = 0.0
        for i in range(n):
            t = i * inv_sr
            frac = t / dur
            freq = 1200.0 - 1050.0 * frac
            env = math.sin(math.pi * frac)
            signal[i] = math.sin(phase) * 0.55 * env
            phase += 2.0 * math.pi * freq * inv_sr
            if phase > 2.0 * math.pi:
                phase -= 2.0 * math.pi

        return self._pcm(signal)

    def _generate_fire_crackle(self) -> bytes:
        """Warm acoustic hearth harmonic tone with gentle subtle warmth, zero harsh static (400 ms)."""
        dur = 0.400
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        f = 130.81  # C3
        for i in range(n):
            t = i * inv_sr
            env = math.sin(math.pi * (t / dur)) ** 1.2
            signal[i] = (math.sin(2.0 * math.pi * f * t) * 0.45 + math.sin(2.0 * math.pi * f * 2.0 * t) * 0.15) * env
        return self._pcm(signal)

    def _generate_rain_ambient(self) -> bytes:
        """Gentle acoustic ambient pad tone, zero harsh white noise (400 ms)."""
        dur = 0.400
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        f = 164.81  # E3
        for i in range(n):
            t = i * inv_sr
            env = math.sin(math.pi * (t / dur)) ** 1.4
            signal[i] = (math.sin(2.0 * math.pi * f * t) * 0.40 + math.sin(2.0 * math.pi * f * 1.5 * t) * 0.15) * env
        return self._pcm(signal)

    def _generate_taiko_hit(self) -> bytes:
        """Deep ceremonial feudal taiko drum impact with pitch drop (350 ms)."""
        dur = 0.35
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        phase = 0.0
        for i in range(n):
            t = i * inv_sr
            freq = 62.0 + 78.0 * math.exp(-t / 0.035)
            phase += 2.0 * math.pi * freq * inv_sr
            env = math.exp(-t / 0.11)
            signal[i] = math.sin(phase) * 0.78 * env
        return self._pcm(signal)

    def _generate_katana_whoosh(self) -> bytes:
        """Crisp steel blade unsheathe harmonic shimmer (220 ms)."""
        dur = 0.22
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        for i in range(n):
            t = i * inv_sr
            frac = t / dur
            ring = (math.sin(2 * math.pi * 2450.0 * t) * 0.32 + math.sin(2 * math.pi * 3820.0 * t) * 0.18) * math.exp(-t / 0.09)
            signal[i] = ring * math.sin(math.pi * min(1.0, frac * 1.15))
        return self._pcm(signal)

    def _generate_chime_soft(self) -> bytes:
        """Warm cozy cafe bell / acoustic harmonic chime (280 ms)."""
        dur = 0.28
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        f1 = self._freq_note("E5")
        f2 = self._freq_note("B5")
        for i in range(n):
            t = i * inv_sr
            env = min(1.0, t / 0.008) * math.exp(-t / 0.10)
            signal[i] = (math.sin(2 * math.pi * f1 * t) * 0.55 + math.sin(2 * math.pi * f2 * t) * 0.28) * env
        return self._pcm(signal)

    def _generate_pencil_scratch(self) -> bytes:
        """Soft acoustic sketch tap, clean and static-free (120 ms)."""
        dur = 0.120
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        f = 440.0
        for i in range(n):
            t = i * inv_sr
            env = math.exp(-t * 45.0)
            signal[i] = math.sin(2.0 * math.pi * f * t) * 0.30 * env
        return self._pcm(signal)

    def _generate_crt_static(self) -> bytes:
        """Retro channel blip: clean musical dual tone, zero TV static/fuzz (120 ms)."""
        dur = 0.120
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        f = 587.33  # D5
        for i in range(n):
            t = i * inv_sr
            env = math.exp(-t * 35.0)
            signal[i] = math.sin(2.0 * math.pi * f * t) * 0.35 * env
        return self._pcm(signal)

    # ------------------------------------------------------------------
    # DSP helpers
    # ------------------------------------------------------------------

    def _zeros_f(self, n: int) -> list[float]:
        return [0.0] * n

    def _sine_decay(
        self,
        freq: float,
        duration: float,
        amplitude: float = 0.5,
        decay_rate: float = 30.0,
    ) -> list[float]:
        """Sine wave with exponential decay."""
        n = int(self.sample_rate * duration)
        inv_sr = 1.0 / self.sample_rate
        two_pi_f = 2.0 * math.pi * freq
        signal = [0.0] * n
        for i in range(n):
            t = i * inv_sr
            env = math.exp(-decay_rate * t)
            signal[i] = amplitude * math.sin(two_pi_f * t) * env
        return signal

    def _sine_adsr(
        self,
        freq: float,
        duration: float,
        amplitude: float = 0.5,
        attack: float = 0.005,
        decay: float = 0.05,
        sustain: float = 0.5,
        release: float = 0.03,
    ) -> list[float]:
        """Sine wave shaped with a simple ADSR envelope."""
        n = int(self.sample_rate * duration)
        inv_sr = 1.0 / self.sample_rate
        sr = self.sample_rate
        two_pi_f = 2.0 * math.pi * freq

        a_samps = max(1, int(attack * sr))
        d_samps = max(1, int(decay * sr))
        r_samps = max(1, int(release * sr))
        s_samps = max(0, n - a_samps - d_samps - r_samps)

        env_list = [0.0] * n
        for i in range(min(a_samps, n)):
            env_list[i] = i / a_samps
        for i in range(min(d_samps, n - a_samps)):
            env_list[a_samps + i] = 1.0 - (i / d_samps) * (1.0 - sustain)
        end_d = a_samps + d_samps
        for i in range(s_samps):
            if end_d + i < n:
                env_list[end_d + i] = sustain
        end_s = end_d + s_samps
        for i in range(r_samps):
            if end_s + i < n:
                env_list[end_s + i] = sustain * (1.0 - i / max(1, r_samps))

        signal = [0.0] * n
        for i in range(n):
            t = i * inv_sr
            signal[i] = amplitude * math.sin(two_pi_f * t) * env_list[i]
        return signal

    def _concat(self, *parts: list[float]) -> list[float]:
        """Concatenate multiple sample lists."""
        result: list[float] = []
        for p in parts:
            result.extend(p)
        return result

    def _generate_boing(self) -> bytes:
        """Cartoon spring bounce (160 ms rising pitch modulation)."""
        dur = 0.180
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        for i in range(n):
            t = i / self.sample_rate
            f = 160.0 + 380.0 * (t / dur) + 40.0 * math.sin(2.0 * math.pi * 24.0 * t)
            env = math.exp(-t / 0.09)
            signal[i] = 0.8 * math.sin(2.0 * math.pi * f * t) * env
        return self._pcm(signal)

    def _generate_slide_whistle(self) -> bytes:
        """Cartoon comedic downward slide whistle (220 ms)."""
        dur = 0.220
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        for i in range(n):
            t = i / self.sample_rate
            f = 820.0 - 580.0 * (t / dur)
            env = math.sin(math.pi * t / dur)
            signal[i] = 0.7 * math.sin(2.0 * math.pi * f * t) * env
        return self._pcm(signal)

    def _generate_chime_idea(self) -> bytes:
        """Crisp harmonic idea lightbulb chime (240 ms)."""
        dur = 0.240
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        for i in range(n):
            t = i / self.sample_rate
            env = math.exp(-t / 0.08)
            signal[i] = 0.5 * (math.sin(2.0 * math.pi * 1318.5 * t) + 0.6 * math.sin(2.0 * math.pi * 2637.0 * t)) * env
        return self._pcm(signal)

    def _generate_coin_clink(self) -> bytes:
        """High metallic coin ping (120 ms)."""
        dur = 0.120
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        for i in range(n):
            t = i / self.sample_rate
            env = math.exp(-t / 0.035)
            signal[i] = 0.6 * (math.sin(2.0 * math.pi * 2960.0 * t) + 0.4 * math.sin(2.0 * math.pi * 4400.0 * t)) * env
        return self._pcm(signal)

    # ------------------------------------------------------------------
    # Extended Audio Suite Generators (Atharv Hatwar Edition)
    # ------------------------------------------------------------------

    def _generate_dramatic_boom(self) -> bytes:
        """Cinematic low-end bass drop with warm sub-bass punch (650 ms)."""
        dur = 0.650
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        phase = 0.0
        for i in range(n):
            t = i * inv_sr
            # Pitch sweep 85 Hz -> 35 Hz
            freq = 35.0 + 50.0 * math.exp(-t / 0.12)
            phase += 2.0 * math.pi * freq * inv_sr
            env = math.exp(-t / 0.18)
            # Gentle saturation for rich harmonic weight
            v = math.sin(phase) + 0.35 * math.sin(phase * 2.0)
            signal[i] = math.tanh(v * 1.5) * 0.85 * env
            if phase > 2.0 * math.pi:
                phase -= 2.0 * math.pi
        return self._pcm(signal)

    def _generate_applause_cheer(self) -> bytes:
        """Enthusiastic crowd clapping and cheer synthesized via modulated noise pulses (650 ms)."""
        dur = 0.650
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        # Deterministic pseudo-random seed sequence for reproducibility
        rng = random.Random(42)
        # Create randomized clap pulse centers
        num_claps = 28
        clap_times = [rng.uniform(0.04, dur - 0.06) for _ in range(num_claps)]
        clap_freqs = [rng.uniform(850.0, 1400.0) for _ in range(num_claps)]
        clap_amps = [rng.uniform(0.3, 0.7) for _ in range(num_claps)]

        for k in range(num_claps):
            c_t = clap_times[k]
            f = clap_freqs[k]
            amp = clap_amps[k]
            start_i = int(c_t * self.sample_rate)
            pulse_len = int(0.025 * self.sample_rate)
            for j in range(pulse_len):
                idx = start_i + j
                if idx < n:
                    pt = j * inv_sr
                    penv = math.exp(-pt * 120.0)
                    signal[idx] += amp * math.sin(2.0 * math.pi * f * pt) * penv

        # Add warm resonant cheer pad harmonic (F4 + A4 + C5)
        for i in range(n):
            t = i * inv_sr
            env = math.sin(math.pi * (t / dur)) ** 1.3
            chord = (
                math.sin(2.0 * math.pi * 349.23 * t) * 0.18 +
                math.sin(2.0 * math.pi * 440.00 * t) * 0.14 +
                math.sin(2.0 * math.pi * 523.25 * t) * 0.12
            )
            signal[i] = (signal[i] * 0.65 + chord) * env

        return self._pcm(signal)

    def _generate_keyboard_typing(self) -> bytes:
        """Mechanical keyboard switch clicks (350 ms)."""
        dur = 0.350
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        keystrokes = [0.02, 0.09, 0.18, 0.27]
        click_freqs = [(1850.0, 2600.0), (1920.0, 2800.0), (1780.0, 2500.0), (2100.0, 2900.0)]
        for k, (t_hit, (f1, f2)) in enumerate(zip(keystrokes, click_freqs)):
            start_i = int(t_hit * self.sample_rate)
            click_len = int(0.035 * self.sample_rate)
            for j in range(click_len):
                idx = start_i + j
                if idx < n:
                    pt = j * inv_sr
                    env = math.exp(-pt * 160.0)
                    v = (math.sin(2.0 * math.pi * f1 * pt) * 0.45 +
                         math.sin(2.0 * math.pi * f2 * pt) * 0.30 +
                         math.sin(2.0 * math.pi * 320.0 * pt) * 0.25)
                    signal[idx] += v * env * 0.70
        return self._pcm(signal)

    def _generate_cash_register(self) -> bytes:
        """Dual metallic bell chime ('ka-ching!') with latch drawer snap (380 ms)."""
        dur = 0.380
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        f1, f2 = 1318.51, 1975.53  # E6 and B6
        for i in range(n):
            t = i * inv_sr
            # Bell 1: starts at t = 0.0
            b1 = (math.sin(2.0 * math.pi * f1 * t) * 0.65 + math.sin(2.0 * math.pi * (f1 * 2) * t) * 0.20) * math.exp(-t / 0.10)
            # Bell 2: starts at t = 0.06s
            b2 = 0.0
            if t >= 0.06:
                dt2 = t - 0.06
                b2 = (math.sin(2.0 * math.pi * f2 * dt2) * 0.75 + math.sin(2.0 * math.pi * (f2 * 1.5) * dt2) * 0.22) * math.exp(-dt2 / 0.12)
            # Latch snap at t = 0.18s
            snap = 0.0
            if t >= 0.18:
                dt3 = t - 0.18
                snap = (math.sin(2.0 * math.pi * 850.0 * dt3) * 0.40 + math.sin(2.0 * math.pi * 1450.0 * dt3) * 0.30) * math.exp(-dt3 / 0.035)
            signal[i] = b1 + b2 + snap
        return self._pcm(signal)

    def _generate_magic_sparkle(self) -> bytes:
        """Whimsical ascending 5-note pentatonic chime arpeggio with shimmering decay (460 ms)."""
        dur = 0.460
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        notes = [1046.50, 1174.66, 1318.51, 1567.98, 2093.00]  # C6, D6, E6, G6, C7
        offsets = [0.00, 0.06, 0.12, 0.18, 0.24]
        for note_f, t_offset in zip(notes, offsets):
            start_i = int(t_offset * self.sample_rate)
            for j in range(n - start_i):
                idx = start_i + j
                pt = j * inv_sr
                env = math.exp(-pt / 0.08)
                v = (math.sin(2.0 * math.pi * note_f * pt) * 0.50 +
                     math.sin(2.0 * math.pi * (note_f * 2.0) * pt) * 0.25)
                signal[idx] += v * env * 0.55
        return self._pcm(signal)

    def _generate_ding_bell(self) -> bytes:
        """Pristine brass service desk bell with rich overtone decay (450 ms)."""
        dur = 0.450
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        f0 = 1174.66  # D6
        f1 = f0 * 2.76  # Inharmonic brass bell mode
        for i in range(n):
            t = i * inv_sr
            attack = min(1.0, t / 0.003)
            env = attack * math.exp(-t / 0.13)
            signal[i] = (math.sin(2.0 * math.pi * f0 * t) * 0.70 + math.sin(2.0 * math.pi * f1 * t) * 0.25) * env
        return self._pcm(signal)

    def _generate_punch_hit(self) -> bytes:
        """Cartoon comic punch impact with pitch drop thud (180 ms)."""
        dur = 0.180
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        phase = 0.0
        for i in range(n):
            t = i * inv_sr
            # Pitch drop 190 Hz -> 45 Hz
            freq = 45.0 + 145.0 * math.exp(-t / 0.025)
            phase += 2.0 * math.pi * freq * inv_sr
            env = math.exp(-t / 0.055)
            # Transient slap at start
            slap = math.sin(2.0 * math.pi * 950.0 * t) * math.exp(-t / 0.012) * 0.45 if t < 0.04 else 0.0
            v = math.sin(phase) * 0.75 + slap
            signal[i] = math.tanh(v * 1.8) * 0.85 * env
            if phase > 2.0 * math.pi:
                phase -= 2.0 * math.pi
        return self._pcm(signal)

    def _generate_animal_bark(self) -> bytes:
        """Stylized friendly dog double-bark (360 ms)."""
        dur = 0.360
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        barks = [0.00, 0.16]
        for t_start in barks:
            start_i = int(t_start * self.sample_rate)
            bark_len = int(0.12 * self.sample_rate)
            phase = 0.0
            for j in range(bark_len):
                idx = start_i + j
                if idx < n:
                    pt = j * inv_sr
                    frac = pt / 0.12
                    # Vocal pitch bend 340 Hz -> 230 Hz
                    freq = 230.0 + 110.0 * (1.0 - frac)
                    phase += 2.0 * math.pi * freq * inv_sr
                    env = math.sin(math.pi * frac) ** 1.2
                    v = (math.sin(phase) * 0.60 + math.sin(phase * 2.0) * 0.25)
                    signal[idx] += math.tanh(v * 1.4) * env * 0.75
                    if phase > 2.0 * math.pi:
                        phase -= 2.0 * math.pi
        return self._pcm(signal)

    def _generate_animal_meow(self) -> bytes:
        """Stylized cute cat meow with rising and falling pitch contour (440 ms)."""
        dur = 0.440
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        phase = 0.0
        for i in range(n):
            t = i * inv_sr
            frac = t / dur
            # Pitch contour: 540 Hz rises to 820 Hz then descends to 420 Hz
            if frac < 0.38:
                freq = 540.0 + 280.0 * (frac / 0.38)
            else:
                freq = 820.0 - 400.0 * ((frac - 0.38) / 0.62)
            phase += 2.0 * math.pi * freq * inv_sr
            env = math.sin(math.pi * frac) ** 1.1
            # Vocal harmonic formant
            v = math.sin(phase) * 0.55 + math.sin(phase * 2.0) * 0.28 + math.sin(phase * 3.0) * 0.12
            signal[i] = v * env * 0.70
            if phase > 2.0 * math.pi:
                phase -= 2.0 * math.pi
        return self._pcm(signal)

    def _generate_rocket_whoosh(self) -> bytes:
        """Rocket thruster ignition and soaring whoosh sweep (520 ms)."""
        dur = 0.520
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        phase1 = 0.0
        phase2 = 0.0
        for i in range(n):
            t = i * inv_sr
            frac = t / dur
            # Soaring accelerating sweep 140 Hz -> 860 Hz
            freq1 = 140.0 + 720.0 * (frac ** 1.8)
            # Low rumble 45 Hz -> 85 Hz
            freq2 = 45.0 + 40.0 * frac
            phase1 += 2.0 * math.pi * freq1 * inv_sr
            phase2 += 2.0 * math.pi * freq2 * inv_sr
            env = math.sin(math.pi * (frac ** 0.8)) ** 1.3
            v = math.sin(phase1) * 0.48 + math.sin(phase2) * 0.38 + 0.15 * math.sin(phase1 * 1.5)
            signal[i] = v * env * 0.80
            if phase1 > 2.0 * math.pi:
                phase1 -= 2.0 * math.pi
            if phase2 > 2.0 * math.pi:
                phase2 -= 2.0 * math.pi
        return self._pcm(signal)

    def _generate_clock_tick(self) -> bytes:
        """Crisp acoustic clock 'tick-tock' impulse (240 ms)."""
        dur = 0.240
        n = int(self.sample_rate * dur)
        signal = self._zeros_f(n)
        inv_sr = 1.0 / self.sample_rate
        ticks = [(0.00, 1380.0), (0.12, 1080.0)]
        for t_pos, f in ticks:
            start_i = int(t_pos * self.sample_rate)
            t_len = int(0.04 * self.sample_rate)
            for j in range(t_len):
                idx = start_i + j
                if idx < n:
                    pt = j * inv_sr
                    env = math.exp(-pt * 180.0)
                    v = (math.sin(2.0 * math.pi * f * pt) * 0.65 +
                         math.sin(2.0 * math.pi * (f * 1.8) * pt) * 0.25)
                    signal[idx] += v * env * 0.70
        return self._pcm(signal)

    @staticmethod
    def _freq_note(note: str) -> float:
        """Return Hz for a note string like 'C5', 'G#4'."""
        NOTE_MAP = {
            "C": 0, "C#": 1, "Db": 1,
            "D": 2, "D#": 3, "Eb": 3,
            "E": 4,
            "F": 5, "F#": 6, "Gb": 6,
            "G": 7, "G#": 8, "Ab": 8,
            "A": 9, "A#": 10, "Bb": 10,
            "B": 11,
        }
        for name, semitone in sorted(NOTE_MAP.items(), key=lambda x: -len(x[0])):
            if note.startswith(name):
                octave = int(note[len(name):])
                midi = (octave + 1) * 12 + semitone
                return 440.0 * (2.0 ** ((midi - 69) / 12.0))
        raise ValueError(f"Unknown note: {note!r}")

    def _normalize(self, signal: list[float]) -> list[float]:
        """Normalize to peak ~0.9."""
        peak = max((abs(v) for v in signal), default=0.0)
        if peak < 1e-6:
            return signal
        factor = 0.9 / peak
        return [v * factor for v in signal]

    def _pcm(self, signal: list[float]) -> bytes:
        """Convert float list ([-1, 1]) to 16-bit signed PCM bytes."""
        signal = self._normalize(signal)
        parts = []
        for v in signal:
            s = max(-32768, min(32767, int(v * 32767)))
            parts.append(struct.pack("<h", s))
        return b"".join(parts)

    def _save_wav(self, pcm_bytes: bytes, path: str) -> None:
        """Save raw 16-bit mono PCM *bytes* to a WAV file at *path*."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm_bytes)
