"""Project configuration and path constants.

All paths are defined relative to the repository root using pathlib.Path.
Never hardcode absolute paths in this project (per INV-012, D-017).
"""

from pathlib import Path

# Repository root determined dynamically from this file's location
REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent

# Core source directories
SOURCE_DIR: Path = REPO_ROOT / "source"
ACQUISITION_DIR: Path = SOURCE_DIR / "acquisition"
GATE_DIR: Path = SOURCE_DIR / "gate"
FEATURES_DIR: Path = SOURCE_DIR / "features"
SPLIT_DIR: Path = SOURCE_DIR / "split"
ENCODER_DIR: Path = SOURCE_DIR / "encoder"
SCORER_DIR: Path = SOURCE_DIR / "scorer"
BASELINES_DIR: Path = SOURCE_DIR / "baselines"
EVALUATION_DIR: Path = SOURCE_DIR / "evaluation"
STATS_DIR: Path = SOURCE_DIR / "stats"
RELEASE_DIR: Path = SOURCE_DIR / "release"
UTILS_DIR: Path = SOURCE_DIR / "utils"

# Project artifact directories
PROJECT_DIR: Path = REPO_ROOT / "project"
CHUNKS_DIR: Path = PROJECT_DIR / "chunks"
CHUNK01_DIR: Path = CHUNKS_DIR / "chunk01"
CHUNK01_DATA_DIR: Path = CHUNK01_DIR / "data"
CHUNK01_MANIFESTS_DIR: Path = CHUNK01_DIR / "manifests"
CHUNK01_REPORTS_DIR: Path = CHUNK01_DIR / "reports"

CHUNK02_DIR: Path = CHUNKS_DIR / "chunk02"
CHUNK02_DATA_DIR: Path = CHUNK02_DIR / "data"
CHUNK02_MANIFESTS_DIR: Path = CHUNK02_DIR / "manifests"
CHUNK02_REPORTS_DIR: Path = CHUNK02_DIR / "reports"

CHUNK03_DIR: Path = CHUNKS_DIR / "chunk03"
CHUNK03_DATA_DIR: Path = CHUNK03_DIR / "data"
CHUNK03_MANIFESTS_DIR: Path = CHUNK03_DIR / "manifests"
CHUNK03_REPORTS_DIR: Path = CHUNK03_DIR / "reports"

CHUNK04_DIR: Path = CHUNKS_DIR / "chunk04"
CHUNK04_DATA_DIR: Path = CHUNK04_DIR / "data"
CHUNK04_MANIFESTS_DIR: Path = CHUNK04_DIR / "manifests"
CHUNK04_REPORTS_DIR: Path = CHUNK04_DIR / "reports"

CHUNK05_DIR: Path = CHUNKS_DIR / "chunk05"
CHUNK05_DATA_DIR: Path = CHUNK05_DIR / "data"
CHUNK05_MANIFESTS_DIR: Path = CHUNK05_DIR / "manifests"
CHUNK05_REPORTS_DIR: Path = CHUNK05_DIR / "reports"

CHUNK06_DIR: Path = CHUNKS_DIR / "chunk06"
CHUNK06_DATA_DIR: Path = CHUNK06_DIR / "data"
CHUNK06_MANIFESTS_DIR: Path = CHUNK06_DIR / "manifests"
CHUNK06_REPORTS_DIR: Path = CHUNK06_DIR / "reports"

CHUNK07_DIR: Path = CHUNKS_DIR / "chunk07"
CHUNK07_DATA_DIR: Path = CHUNK07_DIR / "data"
CHUNK07_MANIFESTS_DIR: Path = CHUNK07_DIR / "manifests"
CHUNK07_REPORTS_DIR: Path = CHUNK07_DIR / "reports"

CHUNK08_DIR: Path = CHUNKS_DIR / "chunk08"
CHUNK08_DATA_DIR: Path = CHUNK08_DIR / "data"
CHUNK08_MANIFESTS_DIR: Path = CHUNK08_DIR / "manifests"
CHUNK08_REPORTS_DIR: Path = CHUNK08_DIR / "reports"

CHUNK09_DIR: Path = CHUNKS_DIR / "chunk09"
CHUNK09_DATA_DIR: Path = CHUNK09_DIR / "data"
CHUNK09_MANIFESTS_DIR: Path = CHUNK09_DIR / "manifests"
CHUNK09_REPORTS_DIR: Path = CHUNK09_DIR / "reports"

# Factory directory
FACTORY_DIR: Path = REPO_ROOT / "factory"

# USGS parameter codes
USGS_PARAM_DISCHARGE: str = "00060"  # Streamflow, ft3/s
USGS_PARAM_GAGE_HEIGHT: str = "00065"  # Gage height, feet

# Default random seed
DEFAULT_RANDOM_SEED: int = 42


def get_chunk_dir(chunk_id: str) -> Path:
    """Return the base path for a specific chunk (e.g. 'chunk01')."""
    return CHUNKS_DIR / chunk_id


def get_chunk_data_dir(chunk_id: str) -> Path:
    """Return the data directory for a specific chunk."""
    return get_chunk_dir(chunk_id) / "data"


def get_chunk_manifests_dir(chunk_id: str) -> Path:
    """Return the manifests directory for a specific chunk."""
    return get_chunk_dir(chunk_id) / "manifests"


def get_chunk_reports_dir(chunk_id: str) -> Path:
    """Return the reports directory for a specific chunk."""
    return get_chunk_dir(chunk_id) / "reports"
