from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd


def build_time_series(
    records: list[dict],
    date_col: str,
    value_col: str,
) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=[date_col, value_col])
    df = pd.DataFrame(records)
    df[date_col] = pd.to_datetime(df[date_col], utc=True)
    df = df.sort_values(date_col).reset_index(drop=True)
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    return df


def compute_growth_rates(series: pd.Series) -> pd.Series:
    """Percentage change between consecutive values."""
    return series.pct_change() * 100


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=1).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def growth_acceleration(series: pd.Series) -> pd.Series:
    """Second derivative — rate of change of the growth rate."""
    first = series.diff()
    return first.diff()

def linear_regression(series: pd.Series) -> dict:
    """Fit OLS on the series index. Returns slope, intercept, r_squared, direction."""
    clean = series.dropna()
    if len(clean) < 2:
        return {"slope": None, "intercept": None, "r_squared": None, "direction": "insufficient_data"}

    x = np.arange(len(clean), dtype=np.float64)
    y = clean.values.astype(np.float64)

    coeffs = np.polyfit(x, y, 1)
    slope, intercept = float(coeffs[0]), float(coeffs[1])

    y_pred = np.polyval(coeffs, x)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

    if abs(slope) < 1e-6:
        direction = "stable"
    elif slope > 0:
        direction = "growing"
    else:
        direction = "declining"

    return {
        "slope": round(slope, 6),
        "intercept": round(intercept, 4),
        "r_squared": round(r_squared, 4),
        "direction": direction,
    }


def project_values(series: pd.Series, days_ahead: int) -> list[dict]:
    """Project future values using linear regression."""
    clean = series.dropna()
    if len(clean) < 2:
        return []

    x = np.arange(len(clean), dtype=np.float64)
    y = clean.values.astype(np.float64)
    coeffs = np.polyfit(x, y, 1)

    projections = []
    last_date = clean.index[-1] if isinstance(clean.index, pd.DatetimeIndex) else None
    for i in range(1, days_ahead + 1):
        val = float(np.polyval(coeffs, len(clean) - 1 + i))
        point = {"day_offset": i, "projected_value": round(val, 2)}
        if last_date is not None:
            point["date"] = (last_date + pd.Timedelta(days=i)).isoformat()
        projections.append(point)
    return projections


def descriptive_stats(series: pd.Series) -> dict:
    """Mean, median, std, min, max, skewness, kurtosis."""
    clean = series.dropna()
    if len(clean) == 0:
        return {k: None for k in ["mean", "median", "std", "min", "max", "skewness", "kurtosis", "count"]}
    return {
        "count": int(len(clean)),
        "mean": round(float(clean.mean()), 4),
        "median": round(float(clean.median()), 4),
        "std": round(float(clean.std()), 4) if len(clean) > 1 else 0.0,
        "min": round(float(clean.min()), 4),
        "max": round(float(clean.max()), 4),
        "skewness": round(float(clean.skew()), 4) if len(clean) > 2 else None,
        "kurtosis": round(float(clean.kurtosis()), 4) if len(clean) > 3 else None,
    }


def compute_z_scores(series: pd.Series) -> pd.Series:
    mean = series.mean()
    std = series.std()
    if std == 0 or pd.isna(std):
        return pd.Series(0.0, index=series.index)
    return (series - mean) / std


def detect_anomalies(df: pd.DataFrame, value_col: str, threshold: float = 2.0) -> pd.DataFrame:
    """Return rows where |z-score| > threshold."""
    z = compute_z_scores(df[value_col])
    df = df.copy()
    df["z_score"] = z
    return df[df["z_score"].abs() > threshold]


def compute_percentile_ranks(series: pd.Series) -> pd.Series:
    """Percentile rank for each value (0-100)."""
    return series.rank(pct=True) * 100


def composite_score(df: pd.DataFrame, columns: list[str], weights: list[float] | None = None) -> pd.Series:
    """Weighted normalized composite score (0-100 scale)."""
    if weights is None:
        weights = [1.0] * len(columns)

    scores = pd.DataFrame()
    for col in columns:
        col_min = df[col].min()
        col_max = df[col].max()
        if col_max - col_min == 0:
            scores[col] = 0.5
        else:
            scores[col] = (df[col] - col_min) / (col_max - col_min)

    weight_arr = np.array(weights, dtype=np.float64)
    weight_arr = weight_arr / weight_arr.sum()

    result = scores[columns].values @ weight_arr
    return pd.Series(result * 100, index=df.index).round(2)


def quartile_distribution(series: pd.Series) -> dict:
    """Count of values in each quartile."""
    clean = series.dropna()
    if len(clean) == 0:
        return {"q1": 0, "q2": 0, "q3": 0, "q4": 0}
    q25 = clean.quantile(0.25)
    q50 = clean.quantile(0.50)
    q75 = clean.quantile(0.75)
    return {
        "q1": int((clean <= q25).sum()),
        "q2": int(((clean > q25) & (clean <= q50)).sum()),
        "q3": int(((clean > q50) & (clean <= q75)).sum()),
        "q4": int((clean > q75).sum()),
    }


def engagement_by_day_of_week(df: pd.DataFrame, date_col: str, engagement_col: str) -> list[dict]:
    """Average engagement per day of week (0=Monday .. 6=Sunday)."""
    df = df.copy()
    df["_dow"] = pd.to_datetime(df[date_col], utc=True).dt.dayofweek
    grouped = df.groupby("_dow")[engagement_col].mean()
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return [
        {"day": day_names[i], "day_index": i, "avg_engagement": round(float(grouped.get(i, 0)), 2)}
        for i in range(7)
    ]


def engagement_by_hour(df: pd.DataFrame, date_col: str, engagement_col: str) -> list[dict]:
    """Average engagement per hour of day."""
    df = df.copy()
    df["_hour"] = pd.to_datetime(df[date_col], utc=True).dt.hour
    grouped = df.groupby("_hour")[engagement_col].mean()
    return [
        {"hour": h, "avg_engagement": round(float(grouped.get(h, 0)), 2)}
        for h in range(24)
    ]


def engagement_heatmap(df: pd.DataFrame, date_col: str, engagement_col: str) -> list[list[float]]:
    """7×24 matrix [day_of_week][hour] with average engagement."""
    df = df.copy()
    ts = pd.to_datetime(df[date_col], utc=True)
    df["_dow"] = ts.dt.dayofweek
    df["_hour"] = ts.dt.hour
    pivot = df.pivot_table(values=engagement_col, index="_dow", columns="_hour", aggfunc="mean", fill_value=0)
    matrix = []
    for dow in range(7):
        row = []
        for h in range(24):
            val = float(pivot.loc[dow, h]) if dow in pivot.index and h in pivot.columns else 0.0
            row.append(round(val, 2))
        matrix.append(row)
    return matrix


def best_posting_time(df: pd.DataFrame, date_col: str, engagement_col: str) -> dict | None:
    """Find the day-of-week + hour combination with the highest average engagement."""
    df = df.copy()
    ts = pd.to_datetime(df[date_col], utc=True)
    df["_dow"] = ts.dt.dayofweek
    df["_hour"] = ts.dt.hour
    grouped = df.groupby(["_dow", "_hour"])[engagement_col].mean()
    if grouped.empty:
        return None
    best = grouped.idxmax()
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return {
        "day": day_names[best[0]],
        "day_index": int(best[0]),
        "hour": int(best[1]),
        "avg_engagement": round(float(grouped.loc[best]), 2),
    }


def period_comparison(
    series: pd.Series, dates: pd.Series, split_date: datetime
) -> dict:
    """Compare metrics before and after a split date."""
    split = pd.Timestamp(split_date, tz="UTC")
    before = series[dates < split].dropna()
    after = series[dates >= split].dropna()

    def _stats(s: pd.Series) -> dict:
        if len(s) == 0:
            return {"mean": None, "median": None, "total": None, "count": 0}
        return {
            "mean": round(float(s.mean()), 4),
            "median": round(float(s.median()), 4),
            "total": round(float(s.sum()), 4),
            "count": int(len(s)),
        }

    before_stats = _stats(before)
    after_stats = _stats(after)

    change_pct = None
    if before_stats["mean"] and before_stats["mean"] != 0:
        change_pct = round((after_stats["mean"] - before_stats["mean"]) / before_stats["mean"] * 100, 2)

    return {
        "before": before_stats,
        "after": after_stats,
        "change_pct": change_pct,
    }


def rolling_correlation(
    series_a: pd.Series, series_b: pd.Series, window: int = 7
) -> list[dict]:
    """Rolling Pearson correlation between two series."""
    corr = series_a.rolling(window=window, min_periods=2).corr(series_b)
    result = []
    for i, val in corr.items():
        if pd.notna(val):
            result.append({"index": int(i), "correlation": round(float(val), 4)})
    return result
