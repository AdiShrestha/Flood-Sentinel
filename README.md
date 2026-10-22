# Flood Sentinel

Flood Sentinel is a research rebuild for evaluating hydrological flood-onset warning under explicit observation availability, uncertain onset timing and limited event labels.

**Research status: not submission ready.** No prior reported performance is admitted as validated evidence. Existing data, labels, models and analyses require independent source verification and methodological review before supporting a new claim. There is no established operational warning service or validated Nepal deployment.

The prospective study compares future-trajectory self-supervision with reconstruction, recurrent models, causal tabular models and simple statistical baselines. Hydrological high-flow targets and official flood-stage/flow targets remain separate. Candidate sources include USGS hydrometry, NOAA threshold metadata and catchment-scale meteorological products; inclusion depends on actual coverage, units, source rights and historical availability.

The immediate work is to derive complete issue streams and labels from verified records, preserve unknown future coverage, handle onset intervals honestly, use train-only transformations, and compare methods on common eligible exposure. Hardcoded event labels, event-enriched sampling, missing-as-zero fallbacks and outcome-driven model selection are inadmissible. Source hashes identify bytes; they do not establish provider authenticity or scientific validity.

Any future results will report actual sample support, false-alert exposure, confirmed warning-time bounds, uncertainty, missing data, failed attempts and measured resource use. Current cohort sizes, compressed-storage estimates, power calculations and laptop execution schedules are prospective planning models, not empirical achievements. A small retrospective pilot cannot establish population generalization or operational access to revised historical data.

See [research status and scientific boundaries](docs/research_status.md), the [bounded daily quality/support analysis](docs/daily_quality_feasibility.md), and the [captured daily-source manifest](docs/daily_quality_source_manifest.json). The daily aggregate matrix has a standalone raw-page replay command; the nine exact response bodies remain local and are hash-checked by that runner. No manuscript submission or acceptance is claimed.

Retain applicable code notices, including the [inherited engine notice](source/flood_sentinel/LICENSE). Provider data and newly written components require their own applicable rights; no blanket data license is asserted.
