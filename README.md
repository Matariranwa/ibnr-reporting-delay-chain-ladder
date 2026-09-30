# Reporting-Delay Chain Ladder for IBNR

A practical Python implementation of a monthly reporting-delay Chain Ladder for estimating **IBNR (Incurred But Not Reported)** from claim-level loss dates, report/intimation dates, and a reported monetary amount.

## What this project does

The workflow:

1. loads claim-level Excel data;
2. cleans and validates loss dates, report dates, and monetary amounts;
3. removes only **exact business-record duplicates**;
4. supports documented manual repairs through a local configuration file;
5. calculates calendar-month reporting delay;
6. constructs incremental and cumulative reporting-delay triangles;
7. calculates volume-weighted Chain Ladder development factors;
8. excludes the partially observed valuation-month diagonal from factor estimation;
9. applies selected tail-factor overrides where sparse late development is not credible;
10. projects ultimate reported amounts and IBNR; and
11. produces a separate sensitivity for unresolved data-quality records.

The valuation date used in the worked analysis was **15 May 2026**. Because May 2026 was only partially observed, factor estimation used complete calendar information through **30 April 2026**.

## Core formulas

For accident month `i` and development month `j`:

`Incremental(i,j)` = sum of reported monetary amounts for claims from accident month `i` reported at development month `j`.

`Cumulative(i,j)` = cumulative sum of the incremental triangle across development months.

Volume-weighted development factor:

`f_j = sum_i C(i,j+1) / sum_i C(i,j)`

Cumulative development factor (CDF):

`CDF_j = f_j × f_(j+1) × ... × f_(ultimate-1)`

Projected ultimate:

`Ultimate_i = Latest complete cumulative_i × CDF_i`

IBNR as at the valuation date:

`IBNR_i = max(Projected ultimate_i - Reported-to-date_i, 0)`

## Repository layout

```text
.
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│   └── reporting_delay_chain_ladder.py
├── docs/
│   └── METHODOLOGY.md
├── config/
│   └── manual_repairs_template.csv
└── outputs/
    └── README.md
```

## Data privacy

The original claim file contains claim identifiers and other potentially confidential information. **Do not commit the raw Excel dataset, repair file, claim-level audit exports, or private results to a public repository.**

The `.gitignore` included here blocks common raw-data and private-output paths.

## Running the analysis

Create a virtual environment, then install:

```bash
pip install -r requirements.txt
```

Place the source workbook locally at:

```text
data/Dataset.xlsx
```

If manual corrections have been independently verified, copy:

```text
config/manual_repairs_template.csv
```

to:

```text
config/manual_repairs.csv
```

and populate it locally. The real repair file should remain private.

Run:

```bash
python src/reporting_delay_chain_ladder.py
```

Aggregated model outputs will be written to `outputs/`.

## Important actuarial limitations

- The monetary field in the source workbook was named `RESERVE`, but settled claims also carried positive amounts. The analysis therefore treats it as the **reported monetary amount attached to each claim**, not automatically as current outstanding case reserve.
- A Reporting-Delay Chain Ladder estimates the ultimate on that reported-amount basis. It is not automatically equivalent to a paid-claims or standard incurred-claims Chain Ladder.
- Sparse late development can create unstable tail factors. Factor selection must be reviewed actuarially rather than applied mechanically.
- Unresolved date-quality records should not be assigned invented dates. They should be handled through data remediation or a separate sensitivity.

## Reproducibility

The public repository intentionally excludes the confidential source data. The code is structured so an authorised user can reproduce the analysis locally with the original workbook and any verified repair file.
