from pathlib import Path
import pandas as pd
import numpy as np

VALUATION_DATE = pd.Timestamp("2026-05-15")
LAST_COMPLETE_REPORT_MONTH = pd.Period("2026-04", freq="M")
TAIL_OVERRIDES = {19: 1.0}

RAW_BUSINESS_COLUMNS = [
    "INSURED", "REG NUMBER", "CLAIM No.", "SUM INSURED", "TPPD", "TPI",
    "COVER PERIOD", "DATE OF LOSS", "INTIMATION DATE", "STATUS", "RESERVE", "CLASS"
]

def load_claims(path: str) -> pd.DataFrame:
    return pd.read_excel(path)

def clean_amount(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.strip(),
        errors="coerce",
    )

def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["loss_date_clean"] = pd.to_datetime(
        out["DATE OF LOSS"], errors="coerce", dayfirst=True, format="mixed"
    )
    out["report_date_clean"] = pd.to_datetime(
        out["INTIMATION DATE"], errors="coerce", dayfirst=True, format="mixed"
    )
    fallback = pd.to_datetime(
        out["INTIMATION DATE.1"], errors="coerce", dayfirst=True, format="mixed"
    )
    out["report_date_clean"] = out["report_date_clean"].fillna(fallback)
    out["reserve_amount"] = clean_amount(out["RESERVE"])
    out["reporting_delay_days"] = (
        out["report_date_clean"] - out["loss_date_clean"]
    ).dt.days
    return out

def remove_exact_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    available = [c for c in RAW_BUSINESS_COLUMNS if c in df.columns]
    return df.drop_duplicates(subset=available, keep="first").copy()

def apply_manual_repairs(df: pd.DataFrame, repair_path: Path) -> pd.DataFrame:
    out = df.copy()
    if not repair_path.exists():
        return out

    repairs = pd.read_csv(repair_path)
    for _, row in repairs.iterrows():
        mask = out["CLAIM No."].astype(str) == str(row["claim_no"])
        if pd.notna(row.get("loss_date")):
            out.loc[mask, "loss_date_clean"] = pd.Timestamp(row["loss_date"])
        if pd.notna(row.get("report_date")):
            out.loc[mask, "report_date_clean"] = pd.Timestamp(row["report_date"])

    out["reporting_delay_days"] = (
        out["report_date_clean"] - out["loss_date_clean"]
    ).dt.days
    return out

def valid_model_mask(df: pd.DataFrame) -> pd.Series:
    return (
        df["loss_date_clean"].notna()
        & df["report_date_clean"].notna()
        & df["reserve_amount"].notna()
        & df["loss_date_clean"].dt.year.between(2000, 2026)
        & df["report_date_clean"].dt.year.between(2000, 2026)
        & (df["reporting_delay_days"] >= 0)
    )

def construct_triangles(model_data: pd.DataFrame):
    td = model_data[
        (model_data["loss_date_clean"] <= VALUATION_DATE)
        & (model_data["report_date_clean"] <= VALUATION_DATE)
    ].copy()

    td["accident_month"] = td["loss_date_clean"].dt.to_period("M")
    td["report_month"] = td["report_date_clean"].dt.to_period("M")
    td["development_month"] = (
        (td["report_date_clean"].dt.year - td["loss_date_clean"].dt.year) * 12
        + (td["report_date_clean"].dt.month - td["loss_date_clean"].dt.month)
    ).astype(int)

    max_dev = int(td["development_month"].max())
    accident_months = pd.period_range(
        td["accident_month"].min(), td["accident_month"].max(), freq="M"
    )
    development_months = list(range(max_dev + 1))

    grouped = td.groupby(
        ["accident_month", "development_month"], observed=False
    )["reserve_amount"].sum()

    incremental = pd.DataFrame(
        0.0, index=accident_months, columns=development_months
    )
    incremental.index.name = "Accident Month"
    incremental.columns.name = "Development Month"

    for (acc, dev), amount in grouped.items():
        incremental.loc[acc, dev] = amount

    observed = pd.DataFrame(
        False, index=accident_months, columns=development_months
    )
    valuation_month = VALUATION_DATE.to_period("M")

    for acc in accident_months:
        for dev in development_months:
            if acc + dev <= valuation_month:
                observed.loc[acc, dev] = True

    incremental = incremental.where(observed, np.nan)
    cumulative = incremental.cumsum(axis=1)
    return td, incremental, cumulative, max_dev

def calculate_factors(cumulative: pd.DataFrame, max_dev: int) -> pd.Series:
    rows = []
    for j in range(max_dev):
        nxt = j + 1
        eligible = cumulative[j].notna() & cumulative[nxt].notna()
        eligible &= (cumulative.index + nxt <= LAST_COMPLETE_REPORT_MONTH)

        denominator = cumulative.loc[eligible, j].sum()
        numerator = cumulative.loc[eligible, nxt].sum()
        factor = numerator / denominator if denominator > 0 else np.nan
        rows.append((j, factor))

    factors = pd.Series(dict(rows), dtype=float)
    for dev, value in TAIL_OVERRIDES.items():
        if dev in factors.index:
            factors.loc[dev] = value
    return factors

def calculate_cdfs(factors: pd.Series, max_dev: int) -> pd.Series:
    cdf = pd.Series(index=range(max_dev + 1), dtype=float)
    cdf.loc[max_dev] = 1.0
    for dev in range(max_dev - 1, -1, -1):
        cdf.loc[dev] = factors.loc[dev] * cdf.loc[dev + 1]
    return cdf

def project_ibnr(cumulative: pd.DataFrame, cdf: pd.Series, max_dev: int) -> pd.DataFrame:
    rows = []
    complete_month = LAST_COMPLETE_REPORT_MONTH

    for acc in cumulative.index:
        latest_complete_dev = (
            (complete_month.year - acc.year) * 12
            + (complete_month.month - acc.month)
        )
        latest_complete_dev = min(latest_complete_dev, max_dev)
        if latest_complete_dev < 0:
            continue

        reported_complete = cumulative.loc[acc, latest_complete_dev]
        current = cumulative.loc[acc].dropna()
        current_reported = current.iloc[-1] if len(current) else 0.0

        projected = reported_complete * cdf.loc[latest_complete_dev]
        ultimate = max(projected, current_reported)
        ibnr = max(projected - current_reported, 0.0)

        rows.append(
            {
                "Accident Month": str(acc),
                "Latest Complete Development": latest_complete_dev,
                "Reported at Valuation": current_reported,
                "CDF": cdf.loc[latest_complete_dev],
                "Projected Ultimate": ultimate,
                "IBNR": ibnr,
            }
        )

    return pd.DataFrame(rows)

def main():
    root = Path(__file__).resolve().parents[1]
    data_path = root / "data" / "Dataset.xlsx"
    repair_path = root / "config" / "manual_repairs.csv"
    output_dir = root / "outputs"
    output_dir.mkdir(exist_ok=True)

    claims = load_claims(data_path)
    claims = parse_dates(claims)
    claims = remove_exact_duplicates(claims)
    claims = apply_manual_repairs(claims, repair_path)

    mask = valid_model_mask(claims)
    model_data = claims.loc[mask].copy()
    excluded = claims.loc[~mask].copy()

    _, incremental, cumulative, max_dev = construct_triangles(model_data)
    factors = calculate_factors(cumulative, max_dev)
    cdf = calculate_cdfs(factors, max_dev)
    results = project_ibnr(cumulative, cdf, max_dev)

    reported = results["Reported at Valuation"].sum()
    ultimate = results["Projected Ultimate"].sum()
    ibnr = results["IBNR"].sum()

    unresolved_amount = excluded["reserve_amount"].sum()
    ratio = ibnr / reported if reported else np.nan
    additional = unresolved_amount * ratio if pd.notna(ratio) else np.nan

    summary = pd.DataFrame(
        {
            "Measure": [
                "Valuation Date",
                "Reported Amount",
                "Estimated Ultimate",
                "Estimated IBNR",
                "IBNR / Ultimate",
                "Unresolved Reported Amount",
                "Indicative Additional IBNR Sensitivity",
                "Sensitivity IBNR",
            ],
            "Value": [
                VALUATION_DATE.date().isoformat(),
                reported,
                ultimate,
                ibnr,
                ibnr / ultimate if ultimate else np.nan,
                unresolved_amount,
                additional,
                ibnr + additional,
            ],
        }
    )

    results.to_csv(output_dir / "ibnr_by_accident_month.csv", index=False)
    summary.to_csv(output_dir / "summary.csv", index=False)
    incremental.to_csv(output_dir / "incremental_triangle.csv")
    cumulative.to_csv(output_dir / "cumulative_triangle.csv")
    factors.rename("Selected Factor").to_csv(output_dir / "selected_factors.csv")
    cdf.rename("CDF").to_csv(output_dir / "cdfs.csv")

    print(summary.to_string(index=False))

if __name__ == "__main__":
    main()
