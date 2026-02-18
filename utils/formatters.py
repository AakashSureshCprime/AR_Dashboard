"""
Utility functions – formatting helpers used across the application.
"""


def fmt_usd(value: float) -> str:
    """
    Format a numeric value as USD with thousand separators.

    Examples:
        fmt_usd(9452.0)   -> '$9,452'
        fmt_usd(1234567)  -> '$1,234,567'
    """
    try:
        return f"${value:,.0f}"
    except (TypeError, ValueError):
        return "$0"


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
