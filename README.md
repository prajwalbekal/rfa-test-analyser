# Rotating Component Test Data Analyser

[![Validate Rotating Component Test Data Analyser](https://github.com/prajwalbekal/rotating-component-test-analyser/actions/workflows/validate.yml/badge.svg)](https://github.com/prajwalbekal/rotating-component-test-analyser/actions/workflows/validate.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Automated multi-channel sensor data analysis pipeline for rotating component test engineering.**

Raw DAQ-style CSV data goes in. Filtered signals, metrics, FFT diagnostics, fault-signature detection, plots, and a structured PDF report come out.

## Why This Project Matters

Manual test-data review is slow, inconsistent, and easy to repeat incorrectly. This project shows how a test engineer can move from raw sensor data to a repeatable pass/fail report with diagnostic evidence, including detection of a planted bearing-defect signature.

The same structure can be adapted to motor test benches, drivetrain endurance tests, rotating machinery validation, aerospace component tests, and other sensor-heavy workflows.

## Features

- Multi-channel analysis for **vibration, force, torque, and temperature**
- 4th-order **Butterworth low-pass filtering** for noise reduction
- **FFT-based vibration analysis** with automatic dominant-frequency peak detection
- Configurable acceptance limits with **pass/fail evaluation**
- Automated **PDF report generation** with plots and engineering summary
- Optional **real-time DAQ simulator** with live FFT display
- Deterministic validation through `scripts/validate.py` and GitHub Actions

## Headline Result

The synthetic test data simulates a rotating component at **3,000 RPM** with 1x, 2x, and 3x shaft harmonics, sensor noise, and a planted **bearing-defect signature near 187 Hz**.

The pipeline correctly recovers:

| Detection | Frequency | Meaning |
| --- | ---: | --- |
| 1x shaft | `50 Hz` | Fundamental rotation rate |
| 2x shaft | `100 Hz` | Shaft harmonic |
| 3x shaft | `150 Hz` | Higher-order shaft harmonic |
| Bearing defect | `187 Hz` | Planted fault signature surfaced by FFT analysis |

That is the core engineering value: distinguishing expected rotational harmonics from a diagnostic fault signature.

## Pipeline

```text
Raw sensor CSV
  -> Butterworth low-pass filtering
  -> RMS, peak, and mean metrics
  -> Single-sided real FFT
  -> Acceptance-limit evaluation
  -> Automated PDF report
```

## Technical Details

| Item | Value |
| --- | --- |
| Sampling rate | `10,000 Hz` |
| Filter | `4th order Butterworth low-pass` |
| Cutoff frequency | `2,000 Hz` |
| FFT method | `Single-sided real FFT` |
| Channels | `Vibration`, `force`, `torque`, `temperature` |
| Report output | `PDF plus PNG plots` |

## Results Snapshot

Deterministic synthetic-data run:

| Check | Result |
| --- | ---: |
| Samples analysed | `50,000` |
| Vibration RMS | `1.6020 g` |
| Force peak | `271.9539 N` |
| Torque RMS | `22.0745 Nm` |
| Temperature peak | `59.5630 C` |
| Dominant FFT peaks | `50.0 Hz`, `100.0 Hz`, `187.0 Hz`, `150.0 Hz` |
| Diagnostic note | `187 Hz bearing-defect zone activity detected` |

## Visual Results

### Time-Domain Signals

![Time-domain multi-channel signals](docs/images/plot_time_domain.png)

### FFT Vibration Spectrum

![FFT vibration spectrum](docs/images/plot_fft.png)

### Metrics vs Acceptance Limits

![Metrics vs acceptance limits](docs/images/plot_metrics.png)

## Repository Structure

```text
.
+-- src/
|   +-- test_analyser.py      # Batch analysis and PDF report generation
|   +-- daq_realtime.py       # Real-time DAQ simulation and live FFT display
+-- docs/
|   +-- images/               # Generated plot previews for GitHub
|   +-- test_report_sample.pdf
+-- scripts/
|   +-- validate.py           # Deterministic validation checks
+-- .github/workflows/        # GitHub Actions CI
+-- requirements.txt
+-- LICENSE
+-- README.md
```

## Installation

### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Usage

Run the batch analyser with generated synthetic data:

```bash
python src/test_analyser.py
```

Run deterministic validation checks:

```bash
python scripts/validate.py
```

Validation confirms the channel limits, the 50 Hz shaft frequency, the 187 Hz bearing-defect signature, and the generated PDF/plot outputs.

Run with your own CSV file:

```bash
python src/test_analyser.py path/to/sensor_data.csv
```

Expected CSV format:

```csv
time_s,vibration_g,force_N,torque_Nm,temperature_C
0.0001,1.234,252.1,22.3,42.0
```

Run the real-time DAQ simulator:

```bash
python src/daq_realtime.py
```

## Output

The batch analyser writes files to `output/`:

- `test_report.pdf` - structured report with metrics, FFT analysis, plots, and pass/fail verdict
- `plot_time_domain.png` - four-channel time-domain overview
- `plot_fft.png` - vibration spectrum with dominant frequency peaks
- `plot_metrics.png` - metrics compared against acceptance limits

A sample report is available at [docs/test_report_sample.pdf](docs/test_report_sample.pdf).

## Skills Demonstrated

- **Signal processing** - DAQ workflows, Butterworth filtering, FFT analysis, peak detection
- **Test engineering** - multi-channel measurement, acceptance limits, automated pass/fail, fault-signature detection
- **Reporting automation** - programmatic PDF report generation with ReportLab
- **Verification engineering** - deterministic seeds, CI-runnable validation, reproducible outputs
- **Python toolchain** - NumPy, Pandas, SciPy, Matplotlib, ReportLab

Relevant for rotating machinery testing, condition monitoring, NVH, motor and drivetrain testing, aerospace test engineering, and automotive endurance testing.

## Author

Prajwal Bekal  
M.Sc. Mechatronics and Cyber-Physical Systems, Deggendorf Institute of Technology  
[GitHub](https://github.com/prajwalbekal) | [LinkedIn](https://de.linkedin.com/in/prajwal-bekal-5117b1150)

## License

MIT - see [LICENSE](LICENSE).

