# CAMELS–GAGES-II metadata candidate-frame crosswalk

**Status:** exposed development metadata, 22 October 2026. This is not an observational cohort, current-natural-flow screen, train/test split, or population-inference result.

## Sources and exact joins

The captured CAMELS-US names and topography tables contain 671 rows each, with 671 unique valid eight-character gauge IDs in each table and an exact one-to-one overlap. Leading zeros were preserved. Each CAMELS ID was matched by exact string to `STAID` in the existing GAGES-II September 2011 basin-ID, basin-classification, dam-modification, and other-modification tables. Each source table has 9,067 keyed data records and 9,067 unique source IDs; all 671 candidate IDs have exactly one match in every table. No candidate row was silently dropped or ambiguously selected.

The dictionaries and source-specific comments were retained with the extracted strings. For example, CAMELS `01013500` (“Fish River near Fort Kent, Maine”, HUC string `01`) joins to GAGES-II `CLASS=Ref`, `HCDN-2009=yes`, GAGES-II `HUC02=01`, `NDAMS_2009=3`, `STOR_NOR_2009=0.77`, and `STOR_NID_2009=0.81`. The same exact join gives 01022500 storage values 14.94 and 19.21 ML/km² with three inventoried dams, and 01030500 values 7.70 and 31.53 ML/km² with two. These three examples were selected as the lexicographically first CAMELS IDs before inspecting the label panel.

The attributed source collections are the [CAMELS-US catalogue](https://ral.ucar.edu/dataset/camels-catchment-attributes-and-meteorology-large-sample-studies-dataset-downloads) and [USGS GAGES-II data release](https://water.usgs.gov/catalog/datasets/2945b996-7636-4d71-89d2-137e984a8a77/), with the source publications by [Addor et al. (2017)](https://doi.org/10.5194/hess-21-5293-2017) and [Falcone (2011)](https://doi.org/10.5066/P96CPHOT). GAGES-II fields are historical inventory/classification attributes: its dam variables are based on an enhanced 2009 National Inventory of Dams and a 2010 location update. They do not establish present-day operations or unchanged natural flow. Historical `Ref` and HCDN-2009 membership do not mean dam-free; all 671 candidates are recorded as `Ref` and HCDN-2009 `yes` in these captured tables.

## Descriptive coverage and source caveats

The dictionary defines both `STOR_NOR_2009` and `STOR_NID_2009` in megaliters per square kilometer, numerically ML/km². Across 671 matched rows, normal storage has minimum 0.00, median 0.16, maximum 1,213.46, and 308 raw `0.00` values. NID storage has minimum 0.00, median 0.30, maximum 1,323.84, and 296 raw `0.00` values. The source warns that NID storage may contain errors and was used because normal storage can incorrectly be zero for large reservoirs. Zero is retained as the source value; it is not evidence of no regulation. `NDAMS_2009` has 295 raw zeros and ranges from 0 to 475.

CAMELS' raw HUC02 counts are:

| HUC02 | n | HUC02 | n |
|---|---:|---|---:|
| 01 | 27 | 10 | 70 |
| 02 | 75 | 11 | 31 |
| 03 | 92 | 12 | 37 |
| 04 | 31 | 13 | 7 |
| 05 | 45 | 14 | 17 |
| 06 | 17 | 15 | 19 |
| 07 | 33 | 16 | 18 |
| 08 | 12 | 17 | 91 |
| 09 | 9 | 18 | 40 |

GAGES-II has exact matching HUC strings for 601 candidates. The other 70 have CAMELS `10` and GAGES-II `10L` (34) or `10U` (36); raw codes remain distinct. GAGES-II aggregate ecoregion counts are CntlPlains 71, EastHghlnds 107, MxWdShld 19, NorthEast 68, SECstPlain 29, SEPlains 99, WestMnts 179, WestPlains 63, and WestXeric 36. These are descriptive concentrations only; neither HUC nor ecoregion establishes independent river-network groups.

The dam-distance dictionary assigns `-999` to “no dam in basin” for its documented dam-distance fields; it must not be converted to zero distance. The separate `HydroMod_Other::RAW_DIS_NEAREST_CANAL` field contains raw `-999.0` for 615 of 671 candidates, but its own dictionary does not explain that code. It is preserved as an unresolved sentinel, not interpreted as a measured distance or proof that no canal exists.

An independent stdlib parser compared the nested CSVs with the original workbook worksheet XML and separately recomputed the candidate ID joins. All 671 crosswalk IDs/cardinalities and exact per-table candidate joins were reproduced. The comparison made 625,163 field-comparison events across the four complete national tables, their dictionary and the candidate joins. The overall comparison **failed** with 15 disagreement events: 14 distinct national text/comment cells, with one compared again in the candidate join. Only one distinct conflict belongs to the 671 candidates: `04221000 / SCREENING_COMMENTS`, whose CSV text contains surrounding quote characters absent from the worksheet text. The other source conflicts include literal `?` versus Unicode minus characters. Both original representations are retained; no text was normalized to force equality. The CSV and worksheet XML are two representations inside one archive, not independent measurements. Thus the check supports ID/cardinality and selected numeric join claims, not exact equivalence of every source text field.

The crosswalk describes a historical metadata candidate frame only. It supplies no current regulation status, verified physical network components, temporal discharge coverage, publication/arrival time, or learner-input authorization. The 2011 GAGES-II inventory cannot become an issue-time predictor for earlier dates. No candidate was selected or excluded by outcome, storage threshold, or favorable rank, and no new source data were acquired for this crosswalk. Detailed tables, raw source bytes, review records, and reproduction receipts remain local rather than being included here.
