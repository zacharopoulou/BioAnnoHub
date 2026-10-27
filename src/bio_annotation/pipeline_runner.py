"""Backward compatible imports for the pipeline package.

New code should import from :mod:`bio_annotation.pipeline`; this module remains
available for existing callers and notebooks.
"""
from __future__ import annotations

import logging
from functools import wraps

from bio_annotation.pipeline import execution as _execution
from bio_annotation.pipeline import manifest as _manifest
from bio_annotation.pipeline import options as _options
from bio_annotation.pipeline import output as _output
from bio_annotation.pipeline import progress as _progress
from bio_annotation.pipeline import runner as _runner

# Preserve the historical module surface, including private helpers imported by
# the CLI, tests, and downstream scripts.
for _module in (_options, _execution, _output, _manifest, _progress, _runner):
    globals().update({name: value for name, value in vars(_module).items() if not name.startswith("__")})

# Monkeypatching these names was a supported testing seam in the original module.
logger = logging.getLogger(__name__)
_EXECUTION_COMPAT_NAMES = (
    "annotate_with_aioner", "annotate_with_apollo", "annotate_with_bent",
    "annotate_with_bern2", "annotate_with_clinicalbert", "annotate_with_d4data",
    "annotate_with_flair", "annotate_with_medcat", "annotate_with_pubtator3",
    "annotate_with_scispacy", "annotate_with_stanza", "_load_apollo_pipeline",
    "_load_clinicalbert_pipeline", "_load_d4data_pipeline", "_load_flair_linker",
    "_load_flair_tagger", "_load_scispacy_model", "reset_reported_endpoints", "logger",
)

def _sync_execution_compat() -> None:
    for name in _EXECUTION_COMPAT_NAMES:
        if name in globals():
            setattr(_execution, name, globals()[name])

def build_pipeline_output(*args, **kwargs):
    _sync_execution_compat()
    return _execution.build_pipeline_output(*args, **kwargs)

def run_selected_annotators(*args, **kwargs):
    _sync_execution_compat()
    return _execution.run_selected_annotators(*args, **kwargs)

def run_selected_annotators_with_status(*args, **kwargs):
    _sync_execution_compat()
    return _execution.run_selected_annotators_with_status(*args, **kwargs)

@wraps(_runner.run_pipeline_from_config)
def run_pipeline_from_config(*args, **kwargs):
    _sync_execution_compat()
    return _runner.run_pipeline_from_config(*args, **kwargs)
