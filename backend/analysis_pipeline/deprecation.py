"""Deprecation markers for legacy analysis paths (do not delete yet)."""

import warnings

_LEGACY_MESSAGE = (
    "Legacy analysis path is deprecated. Prefer AnalysisPipelineService "
    "(backend.analysis_pipeline) and persisted analysis_pipeline_results."
)


def warn_legacy(path_name: str) -> None:
    warnings.warn(f"{path_name}: {_LEGACY_MESSAGE}", DeprecationWarning, stacklevel=2)
