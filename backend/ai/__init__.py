"""backend/ai package exports.

Four of the eight names this task asked for don't exist under those
names — same conflict already raised and resolved for backend/ai/models.py
itself (see that file's module docstring), applied here rather than
re-litigated:

  - PromptTemplate: no such table/class. Migration 0005 defines one flat
    prompt_versions table (rows grouped by a plain `name` column, not a
    parent/child pair) — there's nothing to export under this name.
  - AIUsageLog: not built. server.py's AIUsageLedger already does this
    job, live, wired into real code paths — a second one here would be
    the exact duplication that task explicitly decided against.
  - PromptVersion / ModelPipeline: not classes in .models — that module
    only has factory functions (create_prompt_version_model,
    create_pipeline_version_model), each needing a Base to produce a
    concrete class. PromptVersion IS exported below, but from
    .prompt_registry, where it's actually instantiated against that
    module's own Base — the closest real equivalent to what was asked,
    just not literally "from .models". ModelPipeline/PipelineVersion has
    no such instantiation anywhere yet, so it isn't exported at all.
"""

from .cost_ledger import CostLedger
from .model_registry import ModelError, ModelRegistry
from .models import create_pipeline_version_model, create_prompt_version_model
from .prompt_registry import Persona, PromptExecution, PromptRegistry, PromptVersion, TemplateError

__all__ = [
    "create_prompt_version_model",
    "create_pipeline_version_model",
    "PromptVersion",
    "Persona",
    "PromptExecution",
    "PromptRegistry",
    "TemplateError",
    "ModelRegistry",
    "ModelError",
    "CostLedger",
]
