from pathlib import Path
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from test_analyser import (  # noqa: E402
    find_unexpected_peaks,
    has_fault_zone_peak,
    run_analysis,
)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        metrics, peak_freqs = run_analysis(output_dir=tmp)
        out_dir = Path(tmp)

        checks = [
            ("vibration RMS below limit", metrics["vibration"]["rms"] < 5.0),
            ("force peak below limit", metrics["force"]["peak"] < 500.0),
            ("torque RMS below limit", metrics["torque"]["rms"] < 50.0),
            ("temperature peak below limit", metrics["temperature"]["peak"] < 85.0),
            ("50 Hz shaft frequency detected", any(abs(freq - 50.0) < 1.0 for freq in peak_freqs)),
            ("187 Hz bearing-defect signature detected", has_fault_zone_peak(peak_freqs)),
            ("unexpected FFT peak is surfaced", len(find_unexpected_peaks(peak_freqs)) > 0),
            ("PDF report generated", (out_dir / "test_report.pdf").exists()),
            ("time-domain plot generated", (out_dir / "plot_time_domain.png").exists()),
            ("FFT plot generated", (out_dir / "plot_fft.png").exists()),
            ("metrics plot generated", (out_dir / "plot_metrics.png").exists()),
        ]

    failed = False
    for label, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'} - {label}")
        failed = failed or not passed

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

