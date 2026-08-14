"""
Utility formatting helpers for clean corporate presentation.
Ensures metric numbers are formatted cleanly without overflow or truncation.
"""

def format_currency(val: float) -> str:
    """Format currency values cleanly (e.g., $1.25M, $450.5K, $920.0M)."""
    if val is None:
        return "$0"
    abs_val = abs(val)
    sign = "-" if val < 0 else ""
    if abs_val >= 1_000_000:
        return f"{sign}${abs_val / 1_000_000:,.2f}M"
    elif abs_val >= 1_000:
        return f"{sign}${abs_val / 1_000:,.1f}K"
    else:
        return f"{sign}${abs_val:,.2f}"

def format_number(val: float) -> str:
    """Format large integer or float numbers cleanly."""
    if val is None:
        return "0"
    abs_val = abs(val)
    sign = "-" if val < 0 else ""
    if abs_val >= 1_000_000:
        return f"{sign}{abs_val / 1_000_000:,.2f}M"
    elif abs_val >= 10_000:
        return f"{sign}{abs_val / 1_000:,.1f}K"
    else:
        return f"{sign}{val:,.0f}"

def format_pct(val: float) -> str:
    """Format percentages cleanly."""
    if val is None:
        return "0.0%"
    return f"{val:.1f}%"
