# RFA Test Data Analyser

**Automated multi-channel sensor data analysis pipeline for test engineering applications.**

Built by Prajwal Bekal — M.Sc. Mechatronics, DIT Cham

---

## What it does

This Python tool simulates the post-processing pipeline I built at Triveni Engineering for rotating component endurance testing. It takes raw multi-channel sensor data (vibration, force, torque, temperature), applies signal processing, runs FFT analysis, and automatically generates a structured PDF test report — no manual steps required.

**Input:** Raw sensor CSV file (or auto-generated synthetic data)

**Output:**
- `output/test_report.pdf` — Full PDF test report with metrics, FFT analysis, plots, and pass/fail verdict
- `output/plot_time_domain.png` — 4-channel time-domain overview
- `output/plot_fft.png` — FFT frequency spectrum with annotated peaks
- `output/plot_metrics.png` — Metrics vs acceptance limits bar chart

---

## Pipeline

```
Raw CSV data
    ↓
Butterworth low-pass filter (remove noise)
    ↓
Compute metrics (RMS, peak, mean per channel)
    ↓
FFT analysis — identify dominant frequencies
    ↓
Pass/fail evaluation against acceptance limits
    ↓
Automated PDF report generation
```

---

## Technical details

| Parameter | Value |
|---|---|
| Sampling rate | 10,000 Hz |
| Filter type | Butterworth low-pass, order 4 |
| Filter cutoff | 2,000 Hz |
| FFT | scipy.fft.rfft (single-sided) |
| Channels | Vibration (g), Force (N), Torque (Nm), Temperature (°C) |

**The synthetic test data simulates:**
- 3,000 RPM rotating component (50 Hz fundamental)
- 1x, 2x, 3x RPM harmonics
- Injected bearing defect frequency at ~187 Hz
- Realistic sensor noise on all channels

---

## Installation

```bash
pip install numpy pandas scipy matplotlib reportlab
```

## Usage

```bash
# Run with auto-generated synthetic data
python test_analyser.py

# Run with your own CSV file
python test_analyser.py your_sensor_data.csv
```

**CSV format expected:**
```
time_s, vibration_g, force_N, torque_Nm, temperature_C
0.0001, 1.234, 252.1, 22.3, 42.0
...
```

---

## Sample output

The tool detects an unexpected frequency peak at ~187 Hz (bearing defect signature) and flags it in the report with a recommendation to inspect the bearing before the next test run.

---

## Relevance to aerospace test engineering

This pipeline mirrors the test automation work I perform in practice:

- **Multi-channel DAQ** — simultaneous measurement of vibration, force, torque, temperature
- **Signal filtering** — Butterworth filter removes electrical noise before analysis
- **FFT analysis** — identifies frequency signatures, detects anomalies vs expected RPM harmonics
- **Automated reporting** — removes manual post-processing, ensures consistent documentation
- **Pass/fail evaluation** — compares measured values against configurable acceptance limits

The same architecture applies to rocket component testing: sensor data from a test stand → automated processing → structured report → pass/fail decision.

---

## Author

Prajwal Bekal
M.Sc. Mechatronics & Cyber-Physical Systems — Deggendorf Institute of Technology
prajwalbekal9@gmail.com
