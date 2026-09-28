"""
Prediction Engine: BG/NBD Client Repurchase Forecasts and RFM Analytics.

Encapsulates:
- RFM (Recency, Frequency, T) feature computation from transaction history
- BG/NBD (Beta-Geometric / Negative Binomial Distribution) model fitting via lifetimes
- Empirical gap estimation fallback for single-purchase clients
- Buy probability forecasting (30, 60, 90 days), expected purchase counts,
  and next purchase date window projections
"""
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

try:
    from lifetimes import BetaGeoFitter
    HAS_LIFETIMES = True
except ImportError:
    BetaGeoFitter = None
    HAS_LIFETIMES = False


def _to_scalar(val: Any) -> float:
    """Safely convert lifetimes numpy/array/scalar output to a Python float."""
    if isinstance(val, (np.ndarray, list, pd.Series)):
        return float(np.asanyarray(val).item())
    return float(val)


def prepare_rfm(
    transactions: pd.DataFrame,
    client_col: str = "client_name",
    date_col: str = "invdate",
    amount_col: str = "totalamount",
    observation_end: Optional[date] = None
) -> Tuple[pd.DataFrame, float]:
    """Transform raw invoice transactions into RFM features."""
    if transactions.empty:
        empty_cols = ["client", "frequency", "recency", "T", "first_purchase",
                      "last_purchase", "n_purchases", "total_amount", "gaps"]
        return pd.DataFrame(columns=empty_cols), 30.0

    df = transactions.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    if observation_end is None:
        observation_end = (df[date_col].max() + pd.Timedelta(days=1)).date()
    obs_ts = pd.Timestamp(observation_end)

    rfm_rows = []
    for client, g in df.groupby(client_col):
        sorted_g = g.sort_values(date_col)
        dates = sorted_g[date_col].drop_duplicates()
        tot_amount = float(sorted_g[amount_col].sum()) if amount_col in sorted_g else 0.0
        n_dates = len(dates)

        if n_dates < 2:
            first_dt = dates.iloc[0]
            t_days = max(0.0, float((obs_ts - first_dt).days))
            rfm_rows.append({
                "client": client, "frequency": 0, "recency": 0.0, "T": t_days,
                "first_purchase": first_dt.date(), "last_purchase": first_dt.date(),
                "n_purchases": 1, "total_amount": tot_amount, "gaps": [],
            })
            continue

        first_dt = dates.iloc[0]
        last_dt = dates.iloc[-1]
        frequency = n_dates - 1
        recency = max(0.0, float((last_dt - first_dt).days))
        t_days = max(0.0, float((obs_ts - first_dt).days))
        gaps = dates.diff().dropna().dt.days.tolist()

        rfm_rows.append({
            "client": client, "frequency": frequency, "recency": recency, "T": t_days,
            "first_purchase": first_dt.date(), "last_purchase": last_dt.date(),
            "n_purchases": n_dates, "total_amount": tot_amount, "gaps": gaps,
        })

    rfm_df = pd.DataFrame(rfm_rows)
    all_gaps = [g for sublist in rfm_df["gaps"] for g in sublist]
    median_pop_gap = float(np.median(all_gaps)) if all_gaps else 30.0
    return rfm_df, median_pop_gap


def train_bgf(rfm_df: pd.DataFrame, penalizer_coef: float = 0.01) -> Optional[Any]:
    """Fit a BetaGeoFitter model on clients with at least one repeat purchase."""
    if not HAS_LIFETIMES:
        return None
    fit_df = rfm_df[rfm_df["frequency"] >= 1].copy()
    if len(fit_df) < 3:
        return None
    try:
        bgf = BetaGeoFitter(penalizer_coef=penalizer_coef)
        bgf.fit(fit_df["frequency"], fit_df["recency"], fit_df["T"])
        return bgf
    except Exception:
        return None



def predict_repurchase(
    transactions: pd.DataFrame,
    client_col: str = "client_name",
    date_col: str = "invdate",
    amount_col: str = "totalamount",
    windows: Tuple[int, ...] = (30, 60, 90),
    as_of_date: Optional[date] = None,
    penalizer_coef: float = 0.01
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Compute BG/NBD repurchase predictions and summary metrics for all clients."""
    rfm_df, median_pop_gap = prepare_rfm(
        transactions, client_col=client_col, date_col=date_col,
        amount_col=amount_col, observation_end=as_of_date
    )

    if rfm_df.empty:
        summary = {
            "total_clients": 0, "active_clients": 0, "churn_risk_clients": 0,
            "repeat_clients": 0, "single_clients": 0, "repeat_rate_pct": 0.0,
            "expected_sales_90d": 0.0, "high_prob_30d": 0, "model_fitted": False,
        }
        return [], summary

    bgf = train_bgf(rfm_df, penalizer_coef=penalizer_coef)
    all_gaps = [g for sublist in rfm_df["gaps"] for g in sublist]
    pop_mean_gap = float(np.mean(all_gaps)) if all_gaps else 30.0

    records: List[Dict[str, Any]] = []

    for _, row in rfm_df.iterrows():
        client = str(row["client"])
        last_date: date = row["last_purchase"]
        first_date: date = row["first_purchase"]
        n_purchases: int = int(row["n_purchases"])
        tot_amt: float = float(row["total_amount"])
        gaps: List[int] = row["gaps"]
        freq: float = float(row["frequency"])
        rec: float = float(row["recency"])
        t_val: float = float(row["T"])

        if gaps:
            avg_gap = float(np.mean(gaps))
            med_gap = float(np.median(gaps))
        else:
            avg_gap = pop_mean_gap
            med_gap = median_pop_gap

        if bgf is not None and freq >= 0:
            def _expected(t_days: float) -> float:
                val = bgf.conditional_expected_number_of_purchases_up_to_time(
                    t_days, freq, rec, t_val
                )
                return max(0.0, _to_scalar(val))

            p_alive = _to_scalar(bgf.conditional_probability_alive(freq, rec, t_val))
            p_alive = max(0.0, min(1.0, p_alive))

            probs: Dict[int, float] = {}
            for w in windows:
                exp_w = _expected(float(w))
                prob = 1.0 - (p_alive ** max(1e-4, exp_w))
                probs[w] = max(0.0, min(1.0, prob))

            exp_90 = _expected(90.0)
        else:
            p_alive = 1.0 if n_purchases >= 1 else 0.0
            probs = {w: 0.0 for w in windows}
            exp_90 = 0.0

        if bgf is not None and freq >= 1:
            likely_day = None
            for d in range(7, 365, 7):
                if _expected(float(d)) >= 0.5:
                    likely_day = d
                    break
            if likely_day is None:
                likely_day = int(round(avg_gap))
        else:
            likely_day = int(round(med_gap))

        likely_day = max(1, likely_day)
        likely_next = last_date + timedelta(days=likely_day)

        half_window = max(7, int(round(med_gap * 0.5)))
        window_start = likely_next - timedelta(days=half_window)
        window_end = likely_next + timedelta(days=half_window)

        if n_purchases >= 4 and gaps and (np.std(gaps) < np.mean(gaps) * 0.7):
            conf = "HIGH"
        elif n_purchases >= 2:
            conf = "MEDIUM"
        else:
            conf = "LOW"

        if p_alive >= 0.70:
            status = "Active"
        elif p_alive >= 0.40:
            status = "At-Risk"
        else:
            status = "Churn-Risk"

        records.append({
            "client": client,
            "first_purchase": first_date.isoformat(),
            "last_purchase": last_date.isoformat(),
            "n_purchases": n_purchases,
            "total_amount": tot_amt,
            "avg_gap_days": round(avg_gap, 1),
            "median_gap_days": round(med_gap, 1),
            "p_alive": round(p_alive, 3),
            "status": status,
            "p_purchase_30d": round(probs.get(30, 0.0), 3),
            "p_purchase_60d": round(probs.get(60, 0.0), 3),
            "p_purchase_90d": round(probs.get(90, 0.0), 3),
            "expected_purchases_90d": round(exp_90, 2),
            "likely_next_date": likely_next.isoformat(),
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "confidence": conf,
        })

    records.sort(
        key=lambda r: (r["p_purchase_30d"], r["expected_purchases_90d"], r["p_alive"]),
        reverse=True
    )

    tot_clients = len(records)
    repeat_clients = sum(1 for r in records if r["n_purchases"] >= 2)
    single_clients = tot_clients - repeat_clients
    active_cnt = sum(1 for r in records if r["p_alive"] >= 0.60)
    churn_cnt = sum(1 for r in records if r["p_alive"] < 0.40)
    high_prob_30 = sum(1 for r in records if r["p_purchase_30d"] >= 0.50)
    rep_rate = (repeat_clients / tot_clients * 100.0) if tot_clients > 0 else 0.0

    summary = {
        "total_clients": tot_clients,
        "active_clients": active_cnt,
        "churn_risk_clients": churn_cnt,
        "repeat_clients": repeat_clients,
        "single_clients": single_clients,
        "repeat_rate_pct": round(rep_rate, 1),
        "expected_sales_90d": round(sum(r["expected_purchases_90d"] for r in records), 1),
        "high_prob_30d": high_prob_30,
        "model_fitted": bgf is not None,
    }

    return records, summary

