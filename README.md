# Flood Sentinel

Flood Sentinel is a research rebuild for evaluating hydrological flood-onset warning under explicit observation availability, uncertain onset timing and limited event labels.

**Research status:** the daily aggregate-completion benchmark is complete and reported with its limitations in [docs/initial_temporal_benchmark.md](docs/initial_temporal_benchmark.md). Results from the earlier legacy pilot are not admitted as validated evidence. There is no established operational warning service or validated Nepal deployment.

The prospective study compares future-trajectory self-supervision with reconstruction, recurrent models, causal tabular models and simple statistical baselines. Hydrological high-flow targets and official flood-stage/flow targets remain separate. Candidate sources include USGS hydrometry, NOAA threshold metadata and catchment-scale meteorological products; inclusion depends on actual coverage, units, source rights and historical availability.

The immediate work is to derive complete issue streams and labels from verified records, preserve unknown future coverage, handle onset intervals honestly, use train-only transformations, and compare methods on common eligible exposure. Hardcoded event labels, event-enriched sampling, missing-as-zero fallbacks and outcome-driven model selection are inadmissible. Source hashes identify bytes; they do not establish provider authenticity or scientific validity.

Any future results will report actual sample support, false-alert exposure, confirmed warning-time bounds, uncertainty, missing data, failed attempts and measured resource use. Current cohort sizes, compressed-storage estimates, power calculations and laptop execution schedules are prospective planning models, not empirical achievements. A small retrospective pilot cannot establish population generalization or operational access to revised historical data.

See [research status and scientific boundaries](docs/research_status.md), the [bounded daily quality/support analysis](docs/daily_quality_feasibility.md), and the [captured daily-source manifest](docs/daily_quality_source_manifest.json). The daily aggregate matrix has a standalone raw-page replay command; the nine exact response bodies remain local and are hash-checked by that runner.

## Installation and tests

Python 3.12 or later is required. From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[test]"
python3 -m pytest
```

`pyproject.toml` lists dependencies without version pins. The exact versions of the recorded environment are in [`source/requirements.lock`](source/requirements.lock); [`source/requirements.hashes.lock`](source/requirements.hashes.lock) holds hashes for Darwin arm64 with Python 3.12.8 only and is not a cross-platform lock.

Tests that need untracked private artifacts (cohort files, provider captures, run directories and release archives under `data/`, `project/` or a handoff archive) are skipped in a public checkout, and each skip reason names the missing path. The mapping is explicit in [`source/tests/conftest.py`](source/tests/conftest.py); no other failure is suppressed.

## Repository scope

- **Daily aggregate-completion benchmark and replay.** [`aggregate_completion.py`](source/flood_sentinel/aggregate_completion.py), [`daily_quality_replay.py`](source/flood_sentinel/daily_quality_replay.py), [`baselines.py`](source/flood_sentinel/baselines.py), [`model.py`](source/flood_sentinel/model.py), [`ea_lstm.py`](source/flood_sentinel/ea_lstm.py) and [`replay.py`](source/flood_sentinel/replay.py), documented in [`docs/initial_temporal_benchmark.md`](docs/initial_temporal_benchmark.md) and [`docs/REPLAY.md`](docs/REPLAY.md). The replay needs a processed local bundle that is not distributed here; the example manifest contains placeholder paths only.
- **Legacy P01–P14 pipeline modules** (for example `cohort/`, `events/`, `lead_time.py`, `statistical_analysis.py`, `reproducibility.py`, `release.py` and the corresponding runners). These belong to an earlier pilot on different stations and are retained as engineering primitives and forensic history. They do not produce the benchmark results above, and their outputs are not validated evidence.

Retain applicable code notices, including the [inherited engine notice](source/flood_sentinel/LICENSE). Provider data and newly written components require their own applicable rights; no blanket data license is asserted.
