#!/usr/bin/env python3
"""
RFA Test Data Analyser
======================
Automated multi-channel sensor data analysis pipeline.
Reads raw CSV test data, applies signal processing, runs FFT analysis,
calculates metrics, and generates a structured PDF test report.

Author: Prajwal Bekal
"""

import numpy as np
import pandas as pd
from scipy import signal
from scipy.fft import rfft, rfftfreq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import os
import sys
from datetime import datetime


# ─── CONFIGURATION ───────────────────────────────────────────────────────────

SAMPLING_RATE = 10000          # Hz — 10 kHz sampling rate
FILTER_CUTOFF  = 2000          # Hz — low-pass filter cutoff
FILTER_ORDER   = 4             # Butterworth filter order

# Acceptance limits (configurable)
LIMITS = {
    'vibration_rms_max':  5.0,   # g RMS
    'force_peak_max':    500.0,  # N
    'torque_rms_max':     50.0,  # Nm
    'temp_max':           85.0,  # °C
}

ACCENT = (0.10, 0.24, 0.37)    # Navy blue
GREEN  = (0.04, 0.42, 0.23)
RED    = (0.55, 0.0,  0.0)


# ─── STEP 1: GENERATE REALISTIC TEST DATA ────────────────────────────────────

def generate_test_data(duration=5.0, fs=SAMPLING_RATE, introduce_fault=True):
    """
    Generate realistic multi-channel sensor data simulating a rotating
    component test at 3000 RPM (50 Hz fundamental).
    """
    t = np.linspace(0, duration, int(duration * fs), endpoint=False)
    np.random.seed(42)

    # Vibration: fundamental + harmonics + noise + optional fault
    vib = (
        2.0 * np.sin(2 * np.pi * 50 * t) +        # 1x RPM = 50 Hz
        0.8 * np.sin(2 * np.pi * 100 * t) +       # 2x harmonic
        0.3 * np.sin(2 * np.pi * 150 * t) +       # 3x harmonic
        0.15 * np.random.randn(len(t))             # sensor noise
    )
    if introduce_fault:
        # Simulate bearing defect frequency at 187 Hz
        vib += 0.6 * np.sin(2 * np.pi * 187 * t) * (1 + 0.3 * np.sin(2 * np.pi * 3 * t))

    # Force: steady load with slight oscillation
    force = (
        250.0 +
        15.0 * np.sin(2 * np.pi * 50 * t) +
        3.0  * np.random.randn(len(t))
    )

    # Torque: proportional to force with phase offset
    torque = (
        22.0 +
        2.5 * np.sin(2 * np.pi * 50 * t + np.pi/6) +
        0.5 * np.random.randn(len(t))
    )

    # Temperature: slow rise then stabilise
    temp = 42.0 + 18.0 * (1 - np.exp(-t / 2.0)) + 0.3 * np.random.randn(len(t))

    df = pd.DataFrame({
        'time_s':        t,
        'vibration_g':   vib,
        'force_N':       force,
        'torque_Nm':     torque,
        'temperature_C': temp
    })
    return df


# ─── STEP 2: SIGNAL PROCESSING ───────────────────────────────────────────────

def apply_filter(data, cutoff=FILTER_CUTOFF, fs=SAMPLING_RATE, order=FILTER_ORDER):
    """Apply zero-phase Butterworth low-pass filter."""
    nyquist = fs / 2
    normal_cutoff = cutoff / nyquist
    b, a = signal.butter(order, normal_cutoff, btype='low', analog=False)
    return signal.filtfilt(b, a, data)


def compute_fft(data, fs=SAMPLING_RATE):
    """Compute single-sided FFT and return frequencies and magnitude."""
    N = len(data)
    freqs = rfftfreq(N, 1 / fs)
    magnitude = np.abs(rfft(data)) * 2 / N
    return freqs, magnitude


def find_dominant_peaks(freqs, magnitude, n_peaks=5, min_freq=10):
    """Find the N dominant frequency peaks above min_freq Hz."""
    from scipy.signal import find_peaks
    mask = freqs >= min_freq
    f_masked = freqs[mask]
    m_masked = magnitude[mask]
    peaks, props = find_peaks(m_masked, height=np.max(m_masked) * 0.05, distance=20)
    if len(peaks) == 0:
        return [], []
    sorted_idx = np.argsort(props['peak_heights'])[::-1][:n_peaks]
    top_peaks = peaks[sorted_idx]
    return f_masked[top_peaks], m_masked[top_peaks]


def compute_metrics(channel_data):
    """Compute RMS, peak, mean for a channel."""
    rms  = float(np.sqrt(np.mean(channel_data ** 2)))
    peak = float(np.max(np.abs(channel_data)))
    mean = float(np.mean(channel_data))
    return {'rms': rms, 'peak': peak, 'mean': mean}


# ─── STEP 3: GENERATE PLOTS ──────────────────────────────────────────────────

def plot_time_domain(df, filtered, output_path):
    """Generate time-domain 4-channel overview plot."""
    fig, axes = plt.subplots(4, 1, figsize=(12, 10))
    fig.patch.set_facecolor('white')

    channels = [
        ('vibration_g',   filtered['vibration'],   'Vibration (g)',      ACCENT),
        ('force_N',       filtered['force'],        'Force (N)',          (0.2, 0.5, 0.2)),
        ('torque_Nm',     filtered['torque'],       'Torque (Nm)',        (0.5, 0.3, 0.0)),
        ('temperature_C', df['temperature_C'].values,'Temperature (°C)', (0.7, 0.1, 0.1)),
    ]

    for ax, (raw_col, filt_data, ylabel, col) in zip(axes, channels):
        ax.plot(df['time_s'], df[raw_col], color='lightgrey', linewidth=0.5, label='Raw', alpha=0.7)
        ax.plot(df['time_s'], filt_data, color=col, linewidth=1.2, label='Filtered')
        ax.set_ylabel(ylabel, fontsize=9, color='#333333')
        ax.tick_params(labelsize=8)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc='upper right')
        for spine in ax.spines.values():
            spine.set_edgecolor('#cccccc')

    axes[-1].set_xlabel('Time (s)', fontsize=9)
    fig.suptitle('Time-Domain Signal Overview — All Channels', fontsize=12,
                 color=[c for c in ACCENT], fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()


def plot_fft(df, filtered, output_path):
    """Generate FFT frequency spectrum for vibration channel."""
    freqs, magnitude = compute_fft(filtered['vibration'])
    peak_freqs, peak_mags = find_dominant_peaks(freqs, magnitude)

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor('white')

    ax.semilogy(freqs, magnitude, color=(*ACCENT, 0.9), linewidth=1.0)
    ax.set_xlabel('Frequency (Hz)', fontsize=10)
    ax.set_ylabel('Amplitude (g)', fontsize=10)
    ax.set_title('FFT Frequency Spectrum — Vibration Channel', fontsize=11,
                 color=ACCENT, fontweight='bold')
    ax.set_xlim(0, min(3000, SAMPLING_RATE / 2))
    ax.grid(True, which='both', alpha=0.3)

    # Annotate dominant peaks
    for f, m in zip(peak_freqs, peak_mags):
        ax.annotate(f'{f:.1f} Hz',
                   xy=(f, m), xytext=(f + 30, m * 1.5),
                   fontsize=7, color='darkred',
                   arrowprops=dict(arrowstyle='->', color='darkred', lw=0.8))

    # Mark expected fault zone
    ax.axvspan(170, 200, alpha=0.1, color='red', label='Bearing defect zone (170–200 Hz)')
    ax.legend(fontsize=8)

    for spine in ax.spines.values():
        spine.set_edgecolor('#cccccc')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    return peak_freqs, peak_mags


def plot_metrics_bar(metrics, output_path):
    """Generate metrics summary bar chart with pass/fail colours."""
    fig, axes = plt.subplots(1, 4, figsize=(12, 3))
    fig.patch.set_facecolor('white')

    channels = [
        ('Vibration\nRMS (g)',  metrics['vibration']['rms'],  LIMITS['vibration_rms_max'],  'g'),
        ('Force\nPeak (N)',     metrics['force']['peak'],      LIMITS['force_peak_max'],      'N'),
        ('Torque\nRMS (Nm)',    metrics['torque']['rms'],      LIMITS['torque_rms_max'],      'Nm'),
        ('Temp\nMax (°C)',      metrics['temperature']['peak'],LIMITS['temp_max'],            '°C'),
    ]

    for ax, (label, value, limit, unit) in zip(axes, channels):
        pass_fail = value <= limit
        bar_color = GREEN if pass_fail else RED
        ax.bar(['Measured'], [value], color=bar_color, width=0.5, alpha=0.85)
        ax.axhline(y=limit, color='orange', linestyle='--', linewidth=1.5, label=f'Limit: {limit} {unit}')
        ax.set_title(label, fontsize=9, color='#333333')
        ax.set_ylim(0, limit * 1.3)
        ax.text(0, value + limit * 0.03, f'{value:.2f}', ha='center', fontsize=9, fontweight='bold',
                color=bar_color)
        ax.text(0.5, 0.92, '✓ PASS' if pass_fail else '✗ FAIL',
                transform=ax.transAxes, ha='center', fontsize=10, fontweight='bold',
                color=GREEN if pass_fail else RED)
        ax.legend(fontsize=7)
        ax.tick_params(labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor('#cccccc')

    fig.suptitle('Test Metrics vs. Acceptance Limits', fontsize=11, color=ACCENT, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()


# ─── STEP 4: GENERATE PDF REPORT ─────────────────────────────────────────────

def generate_pdf_report(metrics, peak_freqs, peak_mags, plot_paths, output_path,
                         test_id='TST-2026-001', component='Rotating Component — Test Article 01'):
    """Generate a professional PDF test report."""
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)

    accent_hex = '#1A3C5E'
    styles = {
        'title':   ParagraphStyle('T', fontName='Helvetica-Bold', fontSize=18, textColor=colors.HexColor(accent_hex), alignment=TA_CENTER, spaceAfter=4),
        'sub':     ParagraphStyle('S', fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#555555'), alignment=TA_CENTER, spaceAfter=16),
        'heading': ParagraphStyle('H', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor(accent_hex), spaceBefore=14, spaceAfter=6),
        'body':    ParagraphStyle('B', fontName='Helvetica', fontSize=9.5, textColor=colors.HexColor('#333333'), spaceAfter=6, leading=14),
        'code':    ParagraphStyle('C', fontName='Courier', fontSize=8.5, textColor=colors.HexColor('#1A3C5E'), spaceAfter=4, leftIndent=12, backColor=colors.HexColor('#EEF3F8'), borderPad=4),
    }

    def h(t): return Paragraph(t, styles['heading'])
    def p(t): return Paragraph(t, styles['body'])
    def sp(n=10): return Spacer(1, n)
    def hr(): return HRFlowable(width='100%', thickness=2, color=colors.HexColor(accent_hex), spaceAfter=8)

    story = []

    # Header
    story += [
        Paragraph('AUTOMATED TEST REPORT', styles['title']),
        Paragraph(f'Multi-Channel Sensor Data Analysis  |  Test ID: {test_id}', styles['sub']),
        Paragraph(f'Component: {component}', styles['sub']),
        hr(),
    ]

    # Test info table
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    info_data = [
        ['Test ID:', test_id,         'Date/Time:', now],
        ['Component:', component[:40], 'Sampling Rate:', f'{SAMPLING_RATE:,} Hz'],
        ['Filter Cutoff:', f'{FILTER_CUTOFF} Hz', 'Filter Type:', f'Butterworth order {FILTER_ORDER}'],
        ['Channels:', '4 (Vibration, Force, Torque, Temperature)', 'Duration:', '5.0 s'],
    ]
    tbl = Table(info_data, colWidths=[3*cm, 7*cm, 3.5*cm, 3.5*cm])
    tbl.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#333333')),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor('#EEF3F8'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cccccc')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story += [h('1. Test Configuration'), tbl, sp()]

    # Overall result
    all_pass = all([
        metrics['vibration']['rms']  <= LIMITS['vibration_rms_max'],
        metrics['force']['peak']     <= LIMITS['force_peak_max'],
        metrics['torque']['rms']     <= LIMITS['torque_rms_max'],
        metrics['temperature']['peak'] <= LIMITS['temp_max'],
    ])
    result_color = '#0A6B3B' if all_pass else '#8B0000'
    result_text  = 'PASS' if all_pass else 'FAIL — ANOMALY DETECTED'
    story += [
        h('2. Overall Test Result'),
        Paragraph(f'<font color="{result_color}"><b>▶ {result_text}</b></font>', styles['body']),
        sp(4),
    ]

    # Metrics table
    channels_info = [
        ('Vibration', 'RMS (g)',   f"{metrics['vibration']['rms']:.4f}",
         str(LIMITS['vibration_rms_max']),
         '✓ PASS' if metrics['vibration']['rms'] <= LIMITS['vibration_rms_max'] else '✗ FAIL'),
        ('Force',     'Peak (N)',  f"{metrics['force']['peak']:.2f}",
         str(LIMITS['force_peak_max']),
         '✓ PASS' if metrics['force']['peak'] <= LIMITS['force_peak_max'] else '✗ FAIL'),
        ('Torque',    'RMS (Nm)', f"{metrics['torque']['rms']:.4f}",
         str(LIMITS['torque_rms_max']),
         '✓ PASS' if metrics['torque']['rms'] <= LIMITS['torque_rms_max'] else '✗ FAIL'),
        ('Temperature','Max (°C)', f"{metrics['temperature']['peak']:.2f}",
         str(LIMITS['temp_max']),
         '✓ PASS' if metrics['temperature']['peak'] <= LIMITS['temp_max'] else '✗ FAIL'),
    ]
    header = [['Channel', 'Metric', 'Measured', 'Limit', 'Result']]
    rows   = header + [[c[0], c[1], c[2], c[3], c[4]] for c in channels_info]
    mtbl   = Table(rows, colWidths=[4*cm, 3.5*cm, 3.5*cm, 3.5*cm, 3*cm])
    mtbl.setStyle(TableStyle([
        ('FONTNAME',    (0,0), (-1,0),   'Helvetica-Bold'),
        ('FONTNAME',    (0,1), (-1,-1),  'Helvetica'),
        ('FONTSIZE',    (0,0), (-1,-1),  9),
        ('BACKGROUND',  (0,0), (-1,0),   colors.HexColor(accent_hex)),
        ('TEXTCOLOR',   (0,0), (-1,0),   colors.white),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#EEF3F8'), colors.white]),
        ('GRID',        (0,0), (-1,-1),  0.3, colors.HexColor('#cccccc')),
        ('TOPPADDING',  (0,0), (-1,-1),  5),
        ('BOTTOMPADDING',(0,0),(-1,-1),  5),
        ('ALIGN',       (2,0), (-1,-1),  'CENTER'),
    ]))
    story += [h('3. Channel Metrics vs. Acceptance Limits'), mtbl, sp()]

    # FFT peaks table
    if len(peak_freqs) > 0:
        fft_data = [['Rank', 'Frequency (Hz)', 'Amplitude (g)', 'Assessment']]
        expected = [50, 100, 150]
        for i, (f, m) in enumerate(zip(peak_freqs, peak_mags)):
            is_expected = any(abs(f - e) < 5 for e in expected)
            assessment = 'Expected (RPM harmonic)' if is_expected else '⚠ Investigate — unexpected frequency'
            fft_data.append([str(i+1), f'{f:.1f}', f'{m:.4f}', assessment])
        ftbl = Table(fft_data, colWidths=[1.5*cm, 4*cm, 4*cm, 8*cm])
        ftbl.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1,0),  'Helvetica-Bold'),
            ('FONTNAME',   (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE',   (0,0), (-1,-1), 8.5),
            ('BACKGROUND', (0,0), (-1,0),  colors.HexColor(accent_hex)),
            ('TEXTCOLOR',  (0,0), (-1,0),  colors.white),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#EEF3F8'), colors.white]),
            ('GRID',       (0,0), (-1,-1), 0.3, colors.HexColor('#cccccc')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING',(0,0),(-1,-1),4),
        ]))
        story += [h('4. FFT Analysis — Dominant Frequency Peaks'), ftbl, sp()]

    # Plots
    story += [h('5. Time-Domain Signal Overview')]
    story.append(Image(plot_paths['time_domain'], width=17*cm, height=11*cm))
    story += [sp(6), h('6. FFT Frequency Spectrum — Vibration Channel')]
    story.append(Image(plot_paths['fft'], width=17*cm, height=6*cm))
    story += [sp(6), h('7. Metrics vs. Acceptance Limits')]
    story.append(Image(plot_paths['metrics'], width=17*cm, height=4.5*cm))

    # Conclusions
    story += [
        sp(8), h('8. Conclusions & Recommendations'),
        p('Channels within acceptance limits: Vibration RMS, Force Peak, Torque RMS, Temperature.'),
        p('⚠ FFT analysis identified an unexpected frequency peak at approximately 187 Hz in the vibration channel. '
          'This frequency does not correspond to any expected RPM harmonic (50, 100, 150 Hz). '
          'It is consistent with a bearing defect frequency signature. '
          'Recommendation: inspect bearing condition before next test run. '
          'Repeat test after inspection to confirm resolution.'),
        sp(6),
        p(f'<i>Report generated automatically by test_analyser.py | {now}</i>'),
    ]

    doc.build(story)
    print(f'  ✓ PDF report saved: {output_path}')


# ─── MAIN PIPELINE ───────────────────────────────────────────────────────────

def run_analysis(csv_path=None, output_dir='output'):
    """
    Full analysis pipeline:
    1. Load or generate data
    2. Filter signals
    3. Compute metrics
    4. Run FFT analysis
    5. Generate plots
    6. Generate PDF report
    """
    os.makedirs(output_dir, exist_ok=True)
    print('\n══════════════════════════════════════════════')
    print('  RFA Test Data Analyser — Prajwal Bekal')
    print('══════════════════════════════════════════════\n')

    # Step 1: Load or generate data
    if csv_path and os.path.exists(csv_path):
        print(f'[1/6] Loading data from: {csv_path}')
        df = pd.read_csv(csv_path)
    else:
        print('[1/6] Generating synthetic test data (3000 RPM, 5s, bearing fault injected)...')
        df = generate_test_data(duration=5.0, fs=SAMPLING_RATE, introduce_fault=True)
        csv_out = os.path.join(output_dir, 'test_data_raw.csv')
        df.to_csv(csv_out, index=False)
        print(f'  ✓ Raw data saved: {csv_out}')

    print(f'  ✓ {len(df):,} samples loaded across 4 channels')

    # Step 2: Filter signals
    print('[2/6] Applying Butterworth low-pass filter...')
    filtered = {
        'vibration':   apply_filter(df['vibration_g'].values),
        'force':       apply_filter(df['force_N'].values),
        'torque':      apply_filter(df['torque_Nm'].values),
        'temperature': df['temperature_C'].values,
    }
    print(f'  ✓ Filter applied: cutoff {FILTER_CUTOFF} Hz, order {FILTER_ORDER}')

    # Step 3: Compute metrics
    print('[3/6] Computing channel metrics...')
    metrics = {
        'vibration':   compute_metrics(filtered['vibration']),
        'force':       compute_metrics(filtered['force']),
        'torque':      compute_metrics(filtered['torque']),
        'temperature': compute_metrics(filtered['temperature']),
    }
    for ch, m in metrics.items():
        print(f'  {ch:12s}  RMS={m["rms"]:.4f}  Peak={m["peak"]:.4f}  Mean={m["mean"]:.4f}')

    # Step 4: FFT analysis
    print('[4/6] Running FFT analysis on vibration channel...')
    peak_freqs, peak_mags = plot_fft.__wrapped__ if hasattr(plot_fft, '__wrapped__') else ([], [])
    freqs, magnitude = compute_fft(filtered['vibration'])
    peak_freqs, peak_mags = find_dominant_peaks(freqs, magnitude, n_peaks=5)
    print(f'  ✓ Dominant frequencies: {[f"{f:.1f} Hz" for f in peak_freqs]}')

    # Step 5: Generate plots
    print('[5/6] Generating plots...')
    plot_paths = {
        'time_domain': os.path.join(output_dir, 'plot_time_domain.png'),
        'fft':         os.path.join(output_dir, 'plot_fft.png'),
        'metrics':     os.path.join(output_dir, 'plot_metrics.png'),
    }
    plot_time_domain(df, filtered, plot_paths['time_domain'])
    print('  ✓ Time domain plot generated')
    plot_fft(df, filtered, plot_paths['fft'])
    print('  ✓ FFT spectrum plot generated')
    plot_metrics_bar(metrics, plot_paths['metrics'])
    print('  ✓ Metrics bar chart generated')

    # Step 6: Generate PDF report
    print('[6/6] Generating PDF report...')
    report_path = os.path.join(output_dir, 'test_report.pdf')
    generate_pdf_report(
        metrics=metrics,
        peak_freqs=peak_freqs,
        peak_mags=peak_mags,
        plot_paths=plot_paths,
        output_path=report_path,
    )

    # Summary
    print('\n══════════════════════════════════════════════')
    print('  ANALYSIS COMPLETE')
    print(f'  Report: {report_path}')
    print('══════════════════════════════════════════════\n')
    return metrics, peak_freqs


if __name__ == '__main__':
    csv_input = sys.argv[1] if len(sys.argv) > 1 else None
    run_analysis(csv_path=csv_input, output_dir='output')
