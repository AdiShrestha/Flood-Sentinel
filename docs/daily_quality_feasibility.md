# Daily aggregate quality and support feasibility

This exposed development analysis describes three USGS stations in Maine: 01013500, 01022500 and 01030500. The selection was the first three sorted identifiers in a captured CAMELS catalogue, before the multi-year discharge acquisition. It is not a representative or independent sample of river systems. No model performance, physical flood detection or operational warning result is established.

## Data and target

The captured USGS daily mean discharge records (`00060/00003`, ft³/s) contain 13,149 distinct dates per station during 1990–2025: 39,447 rows across nine responses totaling 26,360,847 bytes. Returned dates cover the requested period; the responses do not establish intraday monitoring completeness or provider-wide completeness. The series IDs are `aa8ac20eb72d4fa58ea9c0eaf61e10ee`, `02fec7bdbbe64d49a3d5414cabfa7ea8` and `b997d85e35254d278725c7506bf74fab`, respectively. Source: [USGS daily collection](https://api.waterdata.usgs.gov/ogcapi/v1/collections/daily).

Reference Q99 uses only 1990–2009, with exact Type 8 interpolation. Evaluation contains daily 12:00 UTC issues in 2010–2025 and elapsed 24/48/72-hour horizons. All these outcomes are development data. The two reference policies and two evaluation-truth policies independently retain approved estimated values or exclude them. Neither policy is error-free ground truth.

A usable daily mean strictly above Q99 completes an aggregate episode at its assigned day-window end, after three consecutive usable below-or-equal daily aggregates have armed the evaluator. A high disarms it; missing/unusable days interrupt recovery. Unknown or unarmed issues remain unknown, and negatives require all necessary future closures. This rule is a constructed daily-aggregate definition, not a physical flood threshold or a continuous 72-hour recession rule.

Day windows are conditionally assigned using America/New_York civil time. This mapping is an explicit assumption; historical series-specific time semantics and release/arrival times are not authenticated. The first evaluated daily aggregate has already elapsed for seven/eight hours at issue and closes 17/16 hours later. Time to that closure is verification lead; physical onset and warning lead remain unknown. Current final products may include later revisions.

## Complete quality matrix

Each cell retains 17,532 station/issues at 24 hours, including unknowns. Across three horizons and four cells there are 210,384 rows. Repeated station/dates, overlapping horizons and policy alternatives share observations.

| Reference quality | Evaluation truth quality | Positive at 24 h | Negative at 24 h | Unknown at 24 h | Distinct completion records represented across horizons |
|---|---|---:|---:|---:|---:|
| Estimated retained | Estimated retained | 46 | 17,123 | 363 | 46 |
| Estimated retained | Unflagged only | 42 | 12,349 | 5,141 | 42 |
| Unflagged only | Estimated retained | 40 | 17,173 | 319 | 40 |
| Unflagged only | Unflagged only | 37 | 12,397 | 5,098 | 37 |

These counts are conditional on the stated definitions. They are not independent floods, forecast scores or estimates of measurement accuracy. At fixed reference thresholds, excluding estimated evaluation truth changes monitoring/state support. Changing reference quality changes the threshold as well as which aggregate completes an episode. For example, at station 01022500, 2,910 ft³/s on 2010-03-30 exceeds the estimated-retaining Q99 (43,292/15) but is below the unflagged-reference Q99 (8,981/3). The next day is 4,510 ft³/s. The completing aggregate moves from March 30 to March 31 under the higher threshold (assigned closures March 31 and April 1 at 04:00 UTC); this does not establish a different physical storm. Across the full panel those two cells have 35 shared completion IDs, 11 unique to the former and five unique to the latter.

The strict previous-closed-day input policy has 13,063 scored station/issues and 4,469 unavailable. It uses only the latest expected approved/unflagged day, with no search for older data. It measures input support, and has not been approved as the sole comparator to a model with longer history or other channels. Missing scores stay unavailable; unknown targets stay unknown. Comparisons on common known labels are conditional and need not represent excluded periods. Issue and target seasons use different dates and must remain separately reported.

## Catchment metadata and limits

The [GAGES-II release](https://water.usgs.gov/catalog/datasets/2945b996-7636-4d71-89d2-137e984a8a77/) identifies historical reference/HCDN-2009 membership for these sites. Its original dictionary defines `STOR_NOR_2009` in megaliters per square kilometer, numerically identical to ML/km². Exact values have not been extracted for these stations. A proposed 50 ML/km² cutoff lacks a scientific rationale in the checked design materials and cannot currently admit a cohort. The attribute's 2009 basis cannot establish unchanged regulation through 2025.

Captured current route queries and catchment polygons show no pairwise links within the queried mainstem routes and no polygon overlaps. [NLDI documentation](https://api.water.usgs.gov/docs/nldi/) describes the indexed NHDPlusV2 network and its navigation. These observations do not establish statistical independence or historical network identity. Regional weather and other dependence remain possible.

Raw records, exact thresholds, the full matrix, both earlier diagonal panels, paired transitions and input/season tables were recomputed using separate software implementations; no differences were found in the stated checks. This is computational agreement on captured records, not external scientific certification. A standalone public raw-to-summary command and complete capture manifest are not yet available; this note is not a complete reproduction package. Re-querying revised provider data need not reproduce the captured hashes. An original pre-acquisition test snapshot is unavailable, so exact replay of that original execution remains incomplete. Current software tests and raw arithmetic are separate evidence.

No learned model, empirical improvement, untouched confirmation, full-cohort eligibility, population inference or submission readiness follows from this feasibility analysis. Source rights and attribution remain provider-specific; no blanket data license is asserted.
