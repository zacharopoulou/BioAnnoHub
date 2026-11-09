from pathlib import Path

from bio_annotation.report.html_report import write_html_report
from bio_annotation.report.html_report_v2 import write_html_report_v2


def html_report_v2_path(output_path: Path) -> Path:
    """results.json -> results_v2.html, next to results.html."""
    return output_path.with_name(output_path.stem + "_v2.html")


__all__ = ["html_report_v2_path", "write_html_report", "write_html_report_v2"]
