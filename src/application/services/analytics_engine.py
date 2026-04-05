from datetime import datetime
import numpy as np
import pandas as pd


def _ensure_float(series: pd.Series) -> pd.Series:
    if series.dtype == object:
        return pd.to_numeric(series, errors="coerce").astype(np.float64)
    return series.astype(np.float64)


def build_time_series(
    records: list[dict],
    date_col: str,
    value_col: str,
    fill_gaps: bool = True,
) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=[date_col, value_col])
    df = pd.DataFrame(records)
    df[date_col] = pd.to_datetime(df[date_col], utc=True)
    df = df.sort_values(date_col).reset_index(drop=True)
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")

    if fill_gaps and len(df) > 1:
        # Normalize to date only to aggregate by day
        df[date_col] = df[date_col].dt.normalize()
        # Keep last value per day
        df = df.drop_duplicates(subset=[date_col], keep="last").set_index(date_col)
        # Resample to daily frequency and fill gaps
        df = df.resample("D").asfreq()
        df[value_col] = df[value_col].ffill()
        df = df.reset_index()

    return df


def compute_growth_rates(series: pd.Series) -> pd.Series:
    series = _ensure_float(series)
    return series.pct_change() * 100


def sma(series: pd.Series, window: int) -> pd.Series:
    series = _ensure_float(series)
    return series.rolling(window=window, min_periods=1).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    series = _ensure_float(series)
    return series.ewm(span=span, adjust=False).mean()


def growth_acceleration(series: pd.Series) -> pd.Series:
    series = _ensure_float(series)
    first = series.diff()
    return first.diff()


def linear_regression(series: pd.Series) -> dict:
    series = _ensure_float(series)
    clean = series.dropna()
    if len(clean) < 2:
        val = float(clean.iloc[0]) if len(clean) == 1 else 0.0
        return {
            "slope": 0.0,
            "relative_slope": 0.0,
            "intercept": round(val, 4),
            "r_squared": 0.0,
            "direction": "stable",
        }

    x = np.arange(len(clean), dtype=np.float64)
    y = clean.values.astype(np.float64)
    mean_y = np.mean(y)

    try:
        coeffs = np.polyfit(x, y, 1)
        slope, intercept = float(coeffs[0]), float(coeffs[1])

        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - mean_y) ** 2)
        r_squared = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        # Calculate relative slope (percentage of mean change per day)
        relative_slope = slope / mean_y if mean_y != 0 else 0
    except (ValueError, np.linalg.LinAlgError, ZeroDivisionError):
        return {"slope": 0.0, "relative_slope": 0.0, "intercept": 0.0, "r_squared": 0.0, "direction": "stable"}

    # Use a 0.5% threshold for significant growth/decline
    if abs(relative_slope) < 0.005:
        direction = "stable"
    elif relative_slope > 0:
        direction = "growing"
    else:
        direction = "declining"

    return {
        "slope": round(slope, 6),
        "relative_slope": round(float(relative_slope), 6),
        "intercept": round(intercept, 4),
        "r_squared": round(r_squared, 4),
        "direction": direction,
    }


def project_values(series: pd.Series, days_ahead: int) -> list[dict]:
    series = _ensure_float(series)
    clean = series.dropna()
    if len(clean) == 0 or days_ahead <= 0:
        return []

    projections = []
    # If using DateTime index, use it for date calculation
    last_date = clean.index[-1] if isinstance(clean.index, pd.DatetimeIndex) else None
    
    # If no datetime index but we have 'date' column in a DataFrame (if this was part of a DF)
    # But here we only have Series. Let's try to get date from Series name or last point
    last_val = float(clean.iloc[-1])

    if len(clean) < 2:
        for i in range(1, days_ahead + 1):
            point = {"day_offset": i, "projected_value": round(last_val, 2)}
            if last_date is not None:
                point["date"] = (pd.to_datetime(last_date) + pd.Timedelta(days=i)).isoformat()
            projections.append(point)
        return projections

    x = np.arange(len(clean), dtype=np.float64)
    y = clean.values.astype(np.float64)
    
    try:
        coeffs = np.polyfit(x, y, 1)
        # Linear projection starting from the model's last point
        for i in range(1, days_ahead + 1):
            # Use the model to predict next values
            val = float(np.polyval(coeffs, len(clean) - 1 + i))
            point = {"day_offset": i, "projected_value": max(0, round(val, 2))}
            if last_date is not None:
                point["date"] = (pd.to_datetime(last_date) + pd.Timedelta(days=i)).isoformat()
            projections.append(point)
    except:
        # Fallback to horizontal projection if polyfit fails
        for i in range(1, days_ahead + 1):
            point = {"day_offset": i, "projected_value": round(last_val, 2)}
            if last_date is not None:
                point["date"] = (pd.to_datetime(last_date) + pd.Timedelta(days=i)).isoformat()
            projections.append(point)
            
    return projections


def calculate_correlations(df: pd.DataFrame, metrics: list[str]) -> list[dict]:
    if len(df) < 3:
        return []
    
    # Ensure numeric and handle missing values
    subset = df[metrics].apply(pd.to_numeric, errors='coerce').ffill().fillna(0)
    
    # Filter out metrics with zero variance
    valid = [m for m in metrics if subset[m].std() > 0]
    if len(valid) < 2:
        return []

    corr_matrix = subset[valid].corr()
    results = []
    for i, m1 in enumerate(valid):
        for m2 in valid[i+1:]:
            val = corr_matrix.loc[m1, m2]
            if pd.notna(val):
                results.append({
                    "metric_a": m1,
                    "metric_b": m2,
                    "overall_correlation": round(float(val), 4)
                })
    return results


def descriptive_stats(series: pd.Series) -> dict:
    series = _ensure_float(series)
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
    series = _ensure_float(series)
    mean = series.mean()
    std = series.std()
    if std == 0 or pd.isna(std):
        return pd.Series(0.0, index=series.index)
    return (series - mean) / std


def detect_anomalies(df: pd.DataFrame, value_col: str, threshold: float = 2.0) -> pd.DataFrame:
    df = df.copy()
    df[value_col] = _ensure_float(df[value_col])
    z = compute_z_scores(df[value_col])
    df["z_score"] = z
    return df[df["z_score"].abs() > threshold]


def compute_percentile_ranks(series: pd.Series) -> pd.Series:
    series = _ensure_float(series)
    return series.rank(pct=True) * 100


def composite_score(df: pd.DataFrame, columns: list[str], weights: list[float] | None = None) -> pd.Series:
    if df.empty:
        return pd.Series([], dtype=np.float64)

    if weights is None:
        weights = [1.0] * len(columns)

    scores = pd.DataFrame(index=df.index)
    for col in columns:
        col_series = _ensure_float(df[col])
        col_min = col_series.min()
        col_max = col_series.max()
        if pd.isna(col_min) or pd.isna(col_max) or col_max - col_min == 0:
            scores[col] = 0.5
        else:
            scores[col] = (col_series - col_min) / (col_max - col_min)

    weight_arr = np.array(weights, dtype=np.float64)
    weight_arr = weight_arr / weight_arr.sum()

    existing_cols = [c for c in columns if c in scores.columns]
    if not existing_cols:
        return pd.Series(0.0, index=df.index)

    result = scores[existing_cols].values @ weight_arr[:len(existing_cols)]
    
    if len(result) == 0 and len(df) > 0:
        return pd.Series(0.0, index=df.index)
        
    return pd.Series(result * 100, index=df.index).round(2)


def quartile_distribution(series: pd.Series) -> dict:
    series = _ensure_float(series)
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
    df = df.copy()
    df[engagement_col] = _ensure_float(df[engagement_col])
    df["_dow"] = pd.to_datetime(df[date_col], utc=True).dt.dayofweek
    grouped = df.groupby("_dow")[engagement_col].mean().fillna(0.0)
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return [
        {"day": day_names[i], "day_index": i, "avg_engagement": round(float(grouped.get(i, 0.0)), 2)}
        for i in range(7)
    ]


def engagement_by_hour(df: pd.DataFrame, date_col: str, engagement_col: str) -> list[dict]:
    df = df.copy()
    df[engagement_col] = _ensure_float(df[engagement_col])
    df["_hour"] = pd.to_datetime(df[date_col], utc=True).dt.hour
    grouped = df.groupby("_hour")[engagement_col].mean().fillna(0.0)
    return [
        {"hour": h, "avg_engagement": round(float(grouped.get(h, 0.0)), 2)}
        for h in range(24)
    ]


def engagement_heatmap(df: pd.DataFrame, date_col: str, engagement_col: str) -> list[list[float]]:
    df = df.copy()
    df[engagement_col] = _ensure_float(df[engagement_col])
    ts = pd.to_datetime(df[date_col], utc=True)
    df["_dow"] = ts.dt.dayofweek
    df["_hour"] = ts.dt.hour
    pivot = df.pivot_table(values=engagement_col, index="_dow", columns="_hour", aggfunc="mean", fill_value=0)
    matrix = []
    for dow in range(7):
        row = []
        for h in range(24):
            if dow in pivot.index and h in pivot.columns:
                val = float(pivot.loc[dow, h])
                if pd.isna(val):
                    val = 0.0
            else:
                val = 0.0
            row.append(round(val, 2))
        matrix.append(row)
    return matrix


def best_posting_time(df: pd.DataFrame, date_col: str, engagement_col: str) -> dict | None:
    df = df.copy()
    df[engagement_col] = _ensure_float(df[engagement_col])
    ts = pd.to_datetime(df[date_col], utc=True)
    df["_dow"] = ts.dt.dayofweek
    df["_hour"] = ts.dt.hour
    grouped = df.groupby(["_dow", "_hour"])[engagement_col].mean().dropna()
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
    series = _ensure_float(series)
    
    # Handle split_date which might already have tzinfo
    split = pd.Timestamp(split_date)
    if split.tzinfo is None:
        split = split.tz_localize("UTC")
    else:
        split = split.tz_convert("UTC")
        
    dates_utc = pd.to_datetime(dates, utc=True)
    before = series[dates_utc < split].dropna()
    after = series[dates_utc >= split].dropna()

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
    series_a = _ensure_float(series_a)
    series_b = _ensure_float(series_b)
    
    # Check if either series has zero variance to avoid RuntimeWarning in divide
    if series_a.std() == 0 or series_b.std() == 0:
        return []
        
    corr = series_a.rolling(window=window, min_periods=window//2 or 2).corr(series_b)
    result = []
    for i, val in corr.items():
        if pd.notna(val):
            result.append({"index": int(i), "correlation": round(float(val), 4)})
    return result
