# Methodology and Audit Trail

## 1. Objective

Estimate IBNR as at **15 May 2026** using a monthly **reporting-delay Chain Ladder** based on claim-level:

- date of loss;
- intimation/report date; and
- reported monetary amount (`RESERVE` in the source workbook).

The method models the emergence of reported claim amounts by time from accident month to report month.

## 2. Initial source data

The source workbook contained **651 rows and 21 columns**.

Key fields included:

- `CLAIM No.`
- `DATE OF LOSS`
- `DATE OF LOSS.1`
- `year of loss`
- `INTIMATION DATE`
- `INTIMATION DATE.1`
- `delay in moths`
- `delay in years`
- `STATUS`
- `RESERVE`
- `CLASS`

All records were `MOTOR PRIVATE`.

## 3. Data-quality findings

Several derived date fields and delay fields were unreliable. Examples included years such as 5900, 6013, 205, and 225, together with implausible delay values such as 1499 months and ±125 years.

Therefore the analysis did not rely on the pre-existing delay columns.

The primary loss date was rebuilt from the raw `DATE OF LOSS` field and the report date from `INTIMATION DATE`, with `INTIMATION DATE.1` used only as a parsing fallback where appropriate.

The reporting delay used for the triangle was calculated from **calendar months**, not elapsed complete months:

`Development month = 12 × (report year - loss year) + (report month - loss month)`

This ensures:

`Accident month + Development month = Report month`

## 4. Initial clean modelling dataset

A record was retained where:

- loss date was available and plausible;
- report date was available and plausible;
- reported monetary amount was numeric;
- report date was on or after loss date.

The first cleaned model retained:

- **597 of 651 claims (91.71%)**
- **20,949,769.96** of the original **22,672,821.19** monetary amount
- **92.40%** of the source monetary amount

The valid reporting-delay distribution had a median of roughly 18 days and a mean of roughly 36 days, supporting monthly rather than annual development periods.

## 5. Valuation date and partial month

The valuation date was set to **15 May 2026**.

The May 2026 diagonal was included in the current reported position because those reports were known by the valuation date, but it was **excluded from development-factor estimation** because May 2026 was only partially observed.

The latest complete reporting month used for factor estimation was therefore **April 2026**.

## 6. Triangle construction

The incremental triangle aggregated the reported monetary amount by:

`Accident Month × Calendar-Month Reporting Delay`

Observed periods with no reported amount were kept as zero.

Future/unobserved cells were kept as `NaN`, not zero.

The cumulative triangle was obtained by cumulative summation across development months.

## 7. Chain Ladder factors

Volume-weighted link ratios were calculated as:

`f_j = sum_i C(i,j+1) / sum_i C(i,j)`

using only accident periods where both development ages were observed and where the transition ended no later than April 2026.

A mechanically calculated late factor at development **19→20** was unstable because it was driven by extremely sparse late-reporting experience. The selected base factor was set to **1.000000** rather than mechanically applying the unstable tail to every immature period.

## 8. Duplicate audit

Thirteen claim numbers appeared more than once.

Only two claim-number groups were exact business-record duplicates. Removing one excess copy from each exact duplicate reduced the modelled reported amount by **20,336.76**.

The other repeated claim numbers were not automatically removed because they contained different insureds, dates, or reserve amounts and could represent claim-number collisions, updates, or multiple claim components.

## 9. Date-repair audit

Excluded claims were tested against alternative date fields.

Automated date-pair generation was treated only as an audit tool: a mathematically valid date pair was not automatically accepted as the true business date.

Six records had sufficiently clear raw-text evidence to support documented date repairs. These restored **273,238.60** of previously excluded reported amount.

Ambiguous and unresolved records were not assigned invented dates.

## 10. Final repaired base model

After exact deduplication and the six defensible repairs:

- Reported amount as at 15 May 2026: **21,202,671.80**
- Estimated IBNR: **451,424.62**
- Estimated ultimate: **21,654,096.42**
- IBNR as a percentage of ultimate: **2.0847%**

The result was stable through the main cleaning stages:

- initial cleaned model IBNR: **445,975.73**
- after exact deduplication: **447,288.62**
- after deduplication and six defensible repairs: **451,424.62**

This stability supports the conclusion that exact duplicates and the repaired records were not driving the reserve estimate.

## 11. Unresolved-data sensitivity

After the defensible repairs, **41 unresolved claims** remained with reported monetary amounts totaling **1,283,825.63**.

These amounts are already reported and therefore were **not added directly to IBNR**.

A proportional sensitivity applied the base model's IBNR-to-reported ratio of **2.1291%** to the unresolved reported amount:

- indicative additional IBNR: **27,333.84**
- sensitivity IBNR: **478,758.46**
- sensitivity total reported amount: **22,486,497.43**
- sensitivity estimated ultimate: **22,965,255.89**

The proportional sensitivity is not a substitute for proper data remediation; it quantifies the possible reserve impact under a simple assumption that unresolved claims have the same average future reporting relationship as the clean portfolio.

## 12. Comparison with the earlier Excel model

The earlier Excel model produced an IBNR of approximately **5.84 million**, materially above the Python result.

The principal methodological differences identified were:

- the Excel triangle was effectively on a different valuation-date basis;
- the Excel delay field behaved like elapsed complete months rather than calendar development months;
- the source delay and derived date fields contained known data-quality problems;
- sparse late development generated an unstable late factor with a large effect on the Excel reserve; and
- the Python workflow explicitly distinguishes observed zero cells from future/unobserved cells and excludes the partial May 2026 diagonal from factor estimation.

The large difference was therefore primarily methodological rather than a simple arithmetic disagreement.

## 13. Interpretation

The preferred base estimate is **451,424.62** on the reported-amount basis, with **478,758.46** retained as a data-quality sensitivity.

This should be described as:

**“Reporting-delay Chain Ladder IBNR estimate based on the source workbook's reported/reserve amount field as at 15 May 2026.”**

It should not be described as a paid or incurred Chain Ladder result unless the accounting definition of the source `RESERVE` field is independently confirmed.

## 14. Governance recommendations

Before using the estimate for financial reporting:

- confirm the accounting definition of the `RESERVE` field;
- resolve the remaining date-quality exceptions from source systems;
- confirm whether repeated claim numbers represent updates, components, or data-entry errors;
- retain the selected-factor rationale in the reserving file;
- run sensitivity tests on early factors and tail selection; and
- independently review the model and reconciliation.
