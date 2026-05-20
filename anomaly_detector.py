import pandas as pd
import numpy as np


# ── 1. Z-Score: flags values far from the mean ──────────────────────────────
def zscore_anomaly(df: pd.DataFrame, threshold: float = 2.5) -> list:
    if df.empty or df["value"].std() == 0:
        return []
    mean = df["value"].mean()
    std  = df["value"].std()
    zs   = (df["value"] - mean) / std
    bad  = df[np.abs(zs) > threshold].copy()
    out  = []
    for r in bad.itertuples():
        z = abs((r.value - mean) / std)
        out.append({
            "timestamp": str(r.timestamp),
            "value":     round(r.value, 4),
            "reason":    f"Z-score {z:.2f} exceeds threshold {threshold} "
                         f"(mean={mean:.0f}, std={std:.0f})",
        })
    return out


# ── 2. IQR: flags spikes and drops outside the normal spread ─────────────────
def iqr_anomaly(df: pd.DataFrame, factor: float = 1.5) -> list:
    if df.empty:
        return []
    q1    = df["value"].quantile(0.25)
    q3    = df["value"].quantile(0.75)
    iqr   = q3 - q1
    lower = q1 - factor * iqr
    upper = q3 + factor * iqr
    bad   = df[(df["value"] < lower) | (df["value"] > upper)].copy()
    out   = []
    for r in bad.itertuples():
        direction = "HIGH" if r.value > upper else "LOW"
        out.append({
            "timestamp": str(r.timestamp),
            "value":     round(r.value, 4),
            "reason":    f"IQR outlier ({direction}) — "
                         f"normal range [{lower:.0f}, {upper:.0f}]",
        })
    return out


# ── 3. Trend: detects sustained upward or downward drift ────────────────────
def trend_anomaly(df: pd.DataFrame, window: int = 12,
                  slope_threshold: float = None) -> list:
    if len(df) < window:
        return []

    # Auto-scale threshold to 5 % of the mean per step if not specified
    if slope_threshold is None:
        slope_threshold = df["value"].mean() * 0.05

    df = df.reset_index(drop=True)
    out = []
    for i in range(window, len(df)):
        segment = df.iloc[i - window: i]["value"].values
        x       = np.arange(window)
        slope, _ = np.polyfit(x, segment, 1)
        if abs(slope) > slope_threshold:
            direction = "downward" if slope < 0 else "upward"
            out.append({
                "timestamp": str(df.iloc[i]["timestamp"]),
                "value":     round(df.iloc[i]["value"], 4),
                "reason":    f"Sustained {direction} trend — "
                             f"slope={slope:.1f} per interval "
                             f"(threshold ±{slope_threshold:.1f})",
            })
    return out


# ── 4. Flatline: detects zero / no-change (interface down) ──────────────────
def flatline_anomaly(df: pd.DataFrame, window: int = 6,
                     variance_threshold: float = 1.0) -> list:
    if len(df) < window:
        return []
    df  = df.reset_index(drop=True)
    out = []
    for i in range(window, len(df)):
        segment = df.iloc[i - window: i]["value"].values
        if segment.var() < variance_threshold:
            out.append({
                "timestamp": str(df.iloc[i]["timestamp"]),
                "value":     round(df.iloc[i]["value"], 4),
                "reason":    f"Flatline detected — variance {segment.var():.4f} "
                             f"< threshold {variance_threshold} "
                             f"(possible interface down or stuck counter)",
            })
    return out
