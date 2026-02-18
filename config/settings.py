"""
Application configuration and constants for the AR Dashboard.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class AppConfig:
    """Immutable application-level configuration."""

    APP_TITLE: str = "AR Inflow Projection Dashboard"
    PAGE_ICON: str = ""
    LAYOUT: str = "wide"
    DATA_FILE: Path = Path(__file__).resolve().parent.parent / "AR_Source file(Sheet1) (1).csv"


@dataclass(frozen=True)
class ProjectionConfig:
    """Configuration for projection categorization."""

    # Keyword used to identify non-inflow (dispute) invoices.
    # Any Projection value containing this string is treated as non-inflow.
    DISPUTE_KEYWORD: str = "Dispute"

    # Color mapping for Review status badges
    REVIEW_COLORS: Dict[str, str] = field(default_factory=lambda: {
        "Green": "#28a745",
        "Yellow": "#ffc107",
        "Orange": "#fd7e14",
        "Red": "#dc3545",
        "Blue": "#007bff",
    })


@dataclass(frozen=True)
class ChartConfig:
    """Configuration for chart theming and display."""

    PRIMARY_COLOR: str = "#1f77b4"
    SUCCESS_COLOR: str = "#28a745"
    WARNING_COLOR: str = "#ffc107"
    DANGER_COLOR: str = "#dc3545"
    INFO_COLOR: str = "#17a2b8"

    BAR_COLOR_SEQUENCE: tuple = (
        "#1f77b4",
        "#2ca02c",
        "#ff7f0e",
        "#d62728",
        "#9467bd",
        "#8c564b",
    )

    # Color map for all possible Remarks categories
    REMARKS_COLORS: Dict[str, str] = field(default_factory=lambda: {
        "Current Due": "#28a745",   # green
        "Overdue": "#dc3545",       # red
        "Future Due": "#1f77b4",    # blue
        "Internal": "#9467bd",      # purple
        "Unapplied": "#ff7f0e",     # orange
    })

    CHART_HEIGHT: int = 450
    CHART_TEMPLATE: str = "plotly_white"


# Singleton instances
app_config = AppConfig()
projection_config = ProjectionConfig()
chart_config = ChartConfig()
