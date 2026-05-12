#!/usr/bin/env python3
"""
Real-Time Multi-Channel DAQ Simulator
======================================
Simulates a live DAQ system reading vibration, force, torque, and temperature
from a rotating component test stand — with animated real-time plotting.

Features:
- 4-channel simultaneous data streams (vibration, force, torque, temperature)
- Live FFT spectrum updating in real time
- Simulated bearing fault that activates mid-test
- Pass/fail limit indicators
- Scrolling time-domain window

Author: Prajwal Bekal
M.Sc. Mechatronics — DIT Cham
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.animation as animation
from matplotlib.patches import FancyArrowPatch
from collections import deque
import time

# ─── CONFIGURATION ───────────────────────────────────────────────────────────

SAMPLING_RATE   = 1000          # Hz (reduced for real-time display)
WINDOW_SECONDS  = 3.0           # seconds of data visible in scrolling window
UPDATE_INTERVAL = 50            # ms between frame updates
SHAFT_RPM       = 3000          # simulated shaft speed
FAULT_ONSET_SEC = 8.0           # bearing fault activates at this time

# Acceptance limits
LIMITS = {
    'vibration_rms': 5.0,       # g RMS
    'force_peak':    500.0,     # N
    'torque_rms':    50.0,      # Nm
    'temp_max':      85.0,      # °C
}

ACCENT  = '#1A3C5E'
GREEN   = '#0A6B3B'
RED     = '#8B0000'
ORANGE  = '#B85C00'
BGCOL   = '#F8FAFC'
GRIDCOL = '#E0E8F0'

WINDOW_SAMPLES = int(WINDOW_SECONDS * SAMPLING_RATE)
FFT_SAMPLES    = 4096           # samples used for FFT (higher = better resolution)


# ─── SIGNAL GENERATOR ────────────────────────────────────────────────────────

class SignalGenerator:
    """Generates realistic rotating machinery sensor signals in real time."""

    def __init__(self, fs=SAMPLING_RATE):
        self.fs      = fs
        self.t       = 0.0
        self.dt      = 1.0 / fs
        self.f0      = SHAFT_RPM / 60.0    # fundamental frequency in Hz
        self.fault_active = False
        self.fault_ramp   = 0.0            # gradual fault build-up

    def next_sample(self):
        """Generate one sample across all channels at current time."""
        t = self.t

        # Activate fault gradually after FAULT_ONSET_SEC
        if t >= FAULT_ONSET_SEC:
            self.fault_active = True
            self.fault_ramp = min(1.0, (t - FAULT_ONSET_SEC) / 3.0)

        # ── Vibration (g) ──────────────────────────────────────────────────
        vib = (
            2.0 * np.sin(2*np.pi * self.f0 * t) +           # 1x = 50 Hz
            0.7 * np.sin(2*np.pi * 2*self.f0 * t) +         # 2x = 100 Hz
            0.25 * np.sin(2*np.pi * 3*self.f0 * t) +        # 3x = 150 Hz
            0.12 * np.random.randn()                         # noise
        )
        if self.fault_active:
            # Bearing defect at 187 Hz, amplitude-modulated at shaft frequency
            fault_sig = (
                self.fault_ramp * 0.8 *
                np.sin(2*np.pi * 187 * t) *
                (1.0 + 0.4 * np.sin(2*np.pi * self.f0 * t))
            )
            vib += fault_sig

        # ── Force (N) ──────────────────────────────────────────────────────
        force = (
            250.0 +
            12.0 * np.sin(2*np.pi * self.f0 * t) +
            2.0  * np.random.randn()
        )
        if self.fault_active:
            force += self.fault_ramp * 15.0 * abs(np.sin(2*np.pi * 187 * t))

        # ── Torque (Nm) ────────────────────────────────────────────────────
        torque = (
            22.0 +
            2.0 * np.sin(2*np.pi * self.f0 * t + np.pi/6) +
            0.4 * np.random.randn()
        )

        # ── Temperature (°C) ───────────────────────────────────────────────
        # Slow exponential rise to steady state, slight increase if fault
        temp_steady = 55.0 * (1.0 - np.exp(-t / 8.0)) + 40.0
        fault_heat  = self.fault_ramp * 8.0 * (1.0 - np.exp(-(t - FAULT_ONSET_SEC) / 5.0)) if self.fault_active else 0.0
        temp = temp_steady + fault_heat + 0.15 * np.random.randn()

        self.t += self.dt
        return vib, force, torque, temp


# ─── REAL-TIME DAQ DISPLAY ───────────────────────────────────────────────────

class RealTimeDAQ:
    """Real-time multi-channel DAQ display with FFT and metrics."""

    def __init__(self):
        self.gen = SignalGenerator()

        # Rolling data buffers
        self.times    = deque(maxlen=WINDOW_SAMPLES)
        self.vib_buf  = deque(maxlen=WINDOW_SAMPLES)
        self.force_buf= deque(maxlen=WINDOW_SAMPLES)
        self.torque_buf=deque(maxlen=WINDOW_SAMPLES)
        self.temp_buf = deque(maxlen=WINDOW_SAMPLES)

        # Longer buffer for FFT
        self.vib_fft_buf = deque(maxlen=FFT_SAMPLES)

        self.start_time = time.time()
        self._build_layout()

    def _build_layout(self):
        """Build the matplotlib figure layout."""
        self.fig = plt.figure(figsize=(16, 9), facecolor=BGCOL)
        self.fig.canvas.manager.set_window_title('Real-Time Multi-Channel DAQ — Prajwal Bekal')

        gs = gridspec.GridSpec(4, 3, figure=self.fig,
                               left=0.07, right=0.97,
                               top=0.92, bottom=0.07,
                               hspace=0.45, wspace=0.35)

        # Title
        self.fig.text(0.5, 0.96,
                      'Real-Time Multi-Channel DAQ Simulator — Rotating Component Test',
                      ha='center', va='top', fontsize=13, fontweight='bold',
                      color=ACCENT)
        self.fig.text(0.5, 0.935,
                      f'Shaft: {SHAFT_RPM} RPM  |  fs: {SAMPLING_RATE} Hz  '
                      f'|  Window: {WINDOW_SECONDS}s  |  Bearing fault onset: {FAULT_ONSET_SEC}s',
                      ha='center', va='top', fontsize=8.5, color='#555555')

        # Time domain axes (left 2/3)
        self.ax_vib   = self.fig.add_subplot(gs[0, :2])
        self.ax_force = self.fig.add_subplot(gs[1, :2])
        self.ax_torq  = self.fig.add_subplot(gs[2, :2])
        self.ax_temp  = self.fig.add_subplot(gs[3, :2])

        # FFT axis (right 1/3, rows 0–1)
        self.ax_fft   = self.fig.add_subplot(gs[0:2, 2])

        # Metrics axis (right 1/3, rows 2–3)
        self.ax_met   = self.fig.add_subplot(gs[2:4, 2])

        # Style all axes
        for ax in [self.ax_vib, self.ax_force, self.ax_torq,
                   self.ax_temp, self.ax_fft, self.ax_met]:
            ax.set_facecolor(BGCOL)
            for spine in ax.spines.values():
                spine.set_edgecolor(GRIDCOL)
            ax.tick_params(labelsize=7.5, colors='#444444')
            ax.grid(True, color=GRIDCOL, linewidth=0.7)

        # Labels
        self.ax_vib.set_ylabel('Vibration (g)', fontsize=8, color=ACCENT)
        self.ax_force.set_ylabel('Force (N)', fontsize=8, color='#2a6a2a')
        self.ax_torq.set_ylabel('Torque (Nm)', fontsize=8, color='#7a4a00')
        self.ax_temp.set_ylabel('Temp (°C)', fontsize=8, color='#8b0000')
        self.ax_temp.set_xlabel('Time (s)', fontsize=8)
        self.ax_fft.set_xlabel('Frequency (Hz)', fontsize=8)
        self.ax_fft.set_ylabel('Amplitude (g)', fontsize=8)
        self.ax_fft.set_title('Live FFT — Vibration', fontsize=9, color=ACCENT, fontweight='bold')
        self.ax_met.set_title('Live Metrics', fontsize=9, color=ACCENT, fontweight='bold')
        self.ax_met.axis('off')

        # Limit lines
        self.ax_vib.axhline(LIMITS['vibration_rms'], color=ORANGE, lw=0.8, ls='--', alpha=0.7, label=f'RMS limit: {LIMITS["vibration_rms"]}g')
        self.ax_force.axhline(LIMITS['force_peak'], color=ORANGE, lw=0.8, ls='--', alpha=0.7)
        self.ax_temp.axhline(LIMITS['temp_max'], color=RED, lw=0.8, ls='--', alpha=0.7)

        # Initialise plot lines
        self.line_vib,   = self.ax_vib.plot([], [],   color=ACCENT,   lw=0.9)
        self.line_force, = self.ax_force.plot([], [],  color='#2a6a2a',lw=0.9)
        self.line_torq,  = self.ax_torq.plot([], [],   color='#7a4a00',lw=0.9)
        self.line_temp,  = self.ax_temp.plot([], [],   color='#8b0000',lw=0.9)
        self.line_fft,   = self.ax_fft.plot([], [],    color=ACCENT,   lw=0.9)

        # Fault annotation (hidden initially)
        self.fault_text = self.fig.text(0.33, 0.50, '', ha='center',
                                        fontsize=11, fontweight='bold',
                                        color=RED, alpha=0.0,
                                        bbox=dict(boxstyle='round,pad=0.4',
                                                  facecolor='#ffe0e0',
                                                  edgecolor=RED, lw=1.5))

        # Metrics text placeholder
        self.metrics_text = self.ax_met.text(0.05, 0.95, '',
                                              transform=self.ax_met.transAxes,
                                              fontsize=9, va='top', ha='left',
                                              fontfamily='monospace',
                                              color='#222222')

        self.ax_vib.legend(fontsize=7, loc='upper right')

    def _compute_rms(self, buf):
        arr = np.array(buf)
        return float(np.sqrt(np.mean(arr**2))) if len(arr) > 0 else 0.0

    def update(self, frame):
        """Animation update function — called every UPDATE_INTERVAL ms."""
        # Generate several samples per frame to keep up with real time
        samples_per_frame = max(1, int(SAMPLING_RATE * UPDATE_INTERVAL / 1000))

        for _ in range(samples_per_frame):
            vib, force, torque, temp = self.gen.next_sample()
            elapsed = time.time() - self.start_time
            self.times.append(elapsed)
            self.vib_buf.append(vib)
            self.force_buf.append(force)
            self.torque_buf.append(torque)
            self.temp_buf.append(temp)
            self.vib_fft_buf.append(vib)

        if len(self.times) < 10:
            return

        t_arr  = np.array(self.times)
        v_arr  = np.array(self.vib_buf)
        f_arr  = np.array(self.force_buf)
        tq_arr = np.array(self.torque_buf)
        tp_arr = np.array(self.temp_buf)

        # Update time domain plots
        self.line_vib.set_data(t_arr, v_arr)
        self.line_force.set_data(t_arr, f_arr)
        self.line_torq.set_data(t_arr, tq_arr)
        self.line_temp.set_data(t_arr, tp_arr)

        t_min, t_max = t_arr[0], t_arr[-1]
        self.ax_vib.set_xlim(t_min, max(t_max, WINDOW_SECONDS))
        self.ax_force.set_xlim(t_min, max(t_max, WINDOW_SECONDS))
        self.ax_torq.set_xlim(t_min, max(t_max, WINDOW_SECONDS))
        self.ax_temp.set_xlim(t_min, max(t_max, WINDOW_SECONDS))

        pad = 0.5
        self.ax_vib.set_ylim(v_arr.min()-pad, v_arr.max()+pad)
        self.ax_force.set_ylim(f_arr.min()-5, f_arr.max()+5)
        self.ax_torq.set_ylim(tq_arr.min()-1, tq_arr.max()+1)
        self.ax_temp.set_ylim(tp_arr.min()-2, tp_arr.max()+2)

        # FFT update
        if len(self.vib_fft_buf) >= FFT_SAMPLES:
            fft_data = np.array(self.vib_fft_buf)
            window   = np.hanning(len(fft_data))
            spectrum = np.abs(np.fft.rfft(fft_data * window)) * 2 / len(fft_data)
            freqs    = np.fft.rfftfreq(len(fft_data), 1.0/SAMPLING_RATE)
            mask     = freqs <= 400
            self.line_fft.set_data(freqs[mask], spectrum[mask])
            self.ax_fft.set_xlim(0, 400)
            ymax = max(spectrum[mask].max() * 1.2, 0.1)
            self.ax_fft.set_ylim(0, ymax)

            # Highlight fault zone
            if self.gen.fault_active:
                self.ax_fft.set_facecolor('#fff5f5')
            else:
                self.ax_fft.set_facecolor(BGCOL)

        # Metrics panel
        vib_rms   = self._compute_rms(self.vib_buf)
        force_peak= float(np.max(np.abs(np.array(self.force_buf)))) if self.force_buf else 0
        torq_rms  = self._compute_rms(self.torque_buf)
        temp_val  = float(self.temp_buf[-1]) if self.temp_buf else 0

        def pf(val, limit):
            return f'{"✓ PASS" if val <= limit else "✗ FAIL"}  [{val:.2f} / {limit}]'

        metrics_str = (
            f'Elapsed: {time.time()-self.start_time:.1f}s\n'
            f'Shaft:   {SHAFT_RPM} RPM\n'
            f'──────────────────────\n'
            f'Vib RMS: {pf(vib_rms, LIMITS["vibration_rms"])}\n'
            f'Force Pk:{pf(force_peak, LIMITS["force_peak"])}\n'
            f'Torq RMS:{pf(torq_rms, LIMITS["torque_rms"])}\n'
            f'Temp:    {pf(temp_val, LIMITS["temp_max"])}\n'
            f'──────────────────────\n'
            f'Fault:   {"⚠ ACTIVE" if self.gen.fault_active else "None detected"}\n'
            f'         {"Bearing 187 Hz" if self.gen.fault_active else ""}'
        )
        color = RED if self.gen.fault_active else GREEN
        self.metrics_text.set_text(metrics_str)
        self.metrics_text.set_color(color if self.gen.fault_active else '#222222')

        # Fault warning overlay
        if self.gen.fault_active:
            alpha = min(1.0, self.gen.fault_ramp * 2)
            self.fault_text.set_text('⚠  BEARING FAULT DETECTED — 187 Hz')
            self.fault_text.set_alpha(alpha * 0.85)
        else:
            self.fault_text.set_alpha(0.0)

        return (self.line_vib, self.line_force, self.line_torq,
                self.line_temp, self.line_fft, self.metrics_text, self.fault_text)

    def run(self):
        """Start the real-time animation."""
        print('\n══════════════════════════════════════════════')
        print('  Real-Time DAQ Simulator — Prajwal Bekal')
        print('══════════════════════════════════════════════')
        print(f'  Channels:    Vibration, Force, Torque, Temperature')
        print(f'  Sampling:    {SAMPLING_RATE} Hz')
        print(f'  Shaft speed: {SHAFT_RPM} RPM ({SHAFT_RPM/60:.1f} Hz)')
        print(f'  Fault onset: {FAULT_ONSET_SEC}s (bearing defect at 187 Hz)')
        print('\n  Close the plot window to stop.\n')

        self.anim = animation.FuncAnimation(
            self.fig,
            self.update,
            interval=UPDATE_INTERVAL,
            blit=False,
            cache_frame_data=False
        )
        plt.show()


# ─── RUN ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    daq = RealTimeDAQ()
    daq.run()
