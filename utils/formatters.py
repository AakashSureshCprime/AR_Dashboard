"""
Utility functions – formatting helpers used across the application.
"""


def fmt_usd(value: float) -> str:
    """
    Format a USD value into a compact human-readable string.
    Examples:
        1_200        → $1.2K
        1_200_000    → $1.2M
        1_200_000_000→ $1.2B
        999          → $999
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "$0"

    abs_val = abs(value)
    sign = "-" if value < 0 else ""

    if abs_val >= 1_000_000_000:
        formatted = f"{abs_val / 1_000_000_000:.1f}B"
    elif abs_val >= 1_000_000:
        formatted = f"{abs_val / 1_000_000:.1f}M"
    elif abs_val >= 1_000:
        formatted = f"{abs_val / 1_000:.1f}K"
    else:
        formatted = f"{abs_val:.0f}"

    return f"{sign}${formatted}"


def fmt_number(value: int) -> str:
    """
    Format an integer with thousand separators.

    Examples:
        fmt_number(1500) -> '1,500'
    """
    try:
        return f"{value:,}"
    except (TypeError, ValueError):
        return "0"


def fmt_percent(value: float, decimals: int = 2) -> str:
    """
    Format a numeric value as a percentage string.

    Examples:
        fmt_percent(45.678)   -> '45.68%'
        fmt_percent(100.0, 0) -> '100%'
    """
    try:
        return f"{value:.{decimals}f}%"
    except (TypeError, ValueError):
        return "0.00%"
