# Daily aggregate quality and support feasibility

This exposed development analysis describes three USGS stations in Maine: 01013500, 01022500 and 01030500. The selection was the first three sorted identifiers in a captured CAMELS catalogue, before the multi-year discharge acquisition. It is not a representative or independent sample of river systems. No model performance, physical flood detection or operational warning result is established.

## Data and target

The captured USGS daily mean discharge records (`00060/00003`, ft³/s) contain 13,149 distinct dates per station during 1990–2025: 39,447 rows across nine responses totaling 26,360,847 bytes. Returned dates cover the requested period; the responses do not establish intraday monitoring completeness or provider-wide completeness. The series IDs are `aa8ac20eb72d4fa58ea9c0eaf61e10ee`, `02fec7bdbbe64d49a3d5414cabfa7ea8` and `b997d85e35254d278725c7506bf74fab`, respectively. Source: [USGS daily collection](https://api.waterdata.usgs.gov/ogcapi/v1/collections/daily).

Reference Q99 uses only 1990–2009, with exact Type 8 interpolation. Evaluation contains daily 12:00 UTC issues in 2010–2025 and elapsed 24/48/72-hour horizons. All these outcomes are development data. The two reference policies and two evaluation-truth policies independently retain approved estimated values or exclude them. Neither policy is error-free ground truth.

A usable daily mean strictly above Q99 completes an aggregate episode at its assigned day-window end, after three consecutive usable below-or-equal daily aggregates have armed the evaluator. A high disarms it; missing/unusable days interrupt recovery. Unknown or unarmed issues remain unknown, and negatives require all necessary future closures. This rule is a constructed daily-aggregate definition, not a physical flood threshold or a continuous 72-hour recession rule.

Day windows are conditionally assigned using America/New_York civil time. This mapping is an explicit assumption; historical series-specific time semantics and release/arrival times are not authenticated. The first evaluated daily aggregate has already elapsed for seven/eight hours at issue and closes 17/16 hours later. Time to that closure is verification lead; physical onset and warning lead remain unknown. Current final products may include later revisions.

## Complete quality matrix

The matrix can be regenerated from the exact captured pages with the standalone public runner. It performs no network requests and requires the nine caller-supplied raw response bodies whose filenames, byte counts and SHA-256 hashes are bound in [`daily_quality_source_manifest.json`](daily_quality_source_manifest.json):

```sh
python3 source/runners/replay_daily_quality.py \
  --manifest docs/daily_quality_source_manifest.json \
  --raw-dir /path/to/the/nine-captured-usgs-pages \
  --output-dir /path/to/a/new-replay-directory
```

The raw pages remain local and are not bundled with this repository. The runner derives the matrix, thresholds, issue ledger, support and transition tables from those pages; it also reports exact output hashes. It supports only the declared noon UTC schedule and unknown historical release/arrival, rejects raw-page symlinks, and binds outputs to the manifest bytes actually consumed. A manifest changed during the replay is rejected before output creation. The manifest and local raw-page hashes make this a reproducible replay of the captured bytes, not an independent authentication of USGS origin, historical release time, or scientific validity. Re-querying revised provider data may not reproduce the capture.

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

The [GAGES-II release](https://water.usgs.gov/catalog/datasets/2945b996-7636-4d71-89d2-137e984a8a77/) identifies historical reference/HCDN-2009 membership for these sites. Its original dictionary defines `STOR_NOR_2009` in megaliters per square kilometer, numerically identical to ML/km². The original archive’s CSV and worksheet XML now agree on all 29 HydroMod_Dams columns for each station at the CSV cell’s displayed precision. The [historical attribute extract](development_site_attributes.json) preserves the selected original values and source hashes. CSV normal storage is 0.77, 14.94 and 7.70 ML/km², respectively; NID storage is 0.81, 19.21 and 31.53. The inventory counts 3, 3 and 2 dams at these historically classified reference sites. Reference classification therefore does not mean dam-free. A proposed 50 ML/km² cutoff lacks a scientific rationale in the checked design materials and cannot currently admit a cohort. The attribute's 2009 basis cannot establish unchanged regulation through 2025.

Captured current route queries and catchment polygons show no pairwise links within the queried mainstem routes and no polygon overlaps. [NLDI documentation](https://api.water.usgs.gov/docs/nldi/) describes the indexed NHDPlusV2 network and its navigation. These observations do not establish statistical independence or historical network identity. Regional weather and other dependence remain possible.

Raw records, exact thresholds, the full matrix, both earlier diagonal panels, paired transitions and input/season tables were recomputed using separate software implementations; no differences were found in the stated checks. This is computational agreement on captured records, not external scientific certification. The public runner and capture manifest cover the captured raw-to-summary path, but the raw pages are not bundled. An original pre-acquisition test snapshot is unavailable, so exact replay of that original execution remains incomplete. Current software tests and raw arithmetic are separate evidence.

No learned model, empirical improvement, untouched confirmation, full-cohort eligibility, population inference or submission readiness follows from this feasibility analysis. Source rights and attribution remain provider-specific; no blanket data license is asserted.

## Day-assignment sensitivity

The preserved baseline assigns each source date to an `America/New_York` civil-day interval. A separate development diagnostic assigns the same date-only values to `Etc/GMT+5` (fixed UTC−05:00 all year). It keeps the three sites, 1990–2009 reference, 2010–2025 evaluation, four quality cells, noon UTC issues, elapsed 24/48/72-hour horizons, thresholds, recurrence, and input rules unchanged. It does **not** reaggregate daily means or replace the civil baseline.

The run compared 39,447 source-date windows and 210,384 issue/horizon/cell rows. Under each assignment, labels were 958 positive, 175,946 negative, and 33,480 unknown; all 176,904 common-known labels retained status (175,946 negative and 958 positive). Eligibility, issue state, arming and target IDs, required closure dates, reasons, and missing-future dates were unchanged. The independently recomputed checker found zero baseline or alternative matrix/trace mismatches against the captured bytes.

Timing did change. The UTC start and end of 24,129 site-date windows each differed, or 8,043 dates per site. Across the matrix, pre-issue overlap changed in 137,088 rows; 774 completion timestamps and their aggregate verification leads shifted by one hour. A positive example at 01013500 completes on 11 April 2010: the civil assignment is 04:00 UTC (64 hours after the 8 April 12:00 UTC issue), and fixed UTC−05:00 is 05:00 UTC (65 hours). These are aggregate verification boundaries, not physical onset or warning lead. The strict input ledger kept all 17,532 keys and source identities; interval-end timestamps changed in 11,424 rows and input ages in 10,662.

Boolean invariance follows for this specific grid, not as a universal property: the issue is at 12:00 UTC, each assignment supplies one interval per unchanged local-date value (civil intervals can span 23 or 25 hours), and the horizons end at 12:00 UTC after an integer number of days. Moving a daily closure between 04:00 and 05:00 UTC changes its elapsed lead and overlap, but not which daily closures fall before those noon endpoints. The same ordered dates, values, quality states, and recurrence therefore yield the same completion keys and labels. The proof requires the same date-indexed values and missingness in both assignments. Identical date gaps alone do not break it. Changing issue times, horizon lengths, date support or reaggregating from subdaily observations changes the comparison and requires a separate check.

Constructed boundary checks covered New York's pre-2007 rules (2 April 2006: 23 hours; 29 October 2006: 25 hours) and post-change examples (11 March 2007: 23 hours; 4 November 2007: 25 hours); the fixed-offset intervals remained 24 hours. Endpoint and missing head/tail cases were also exercised. The runtime's rule provenance was `2026e-rearguard`; its recorded zone-file hashes describe this host, not a universal time-zone database pin.

This sensitivity cannot identify which UTC interval the USGS provider used to calculate a supplied date mean. It cannot prove source-specific historical day semantics, intraday state, onset, warning lead, or historical release/revision time. Those remain unknown. The observed labels are conditional aggregate-completion development labels, not physical flood labels or forecast-performance evidence. Run receipts and independent arithmetic evidence remain in the retained local evidence and are not bundled with this public document.
