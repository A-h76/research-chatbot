"""BaseExtractor — the one interface every extractor implements.

Signature matches the originating task's own literal spec: extract()
takes the shared DocumentIndex/ClassificationResult/AnalysisContext/
EntityRegistry (no extractor re-parses or re-derives anything Phase
1.1-1.3 already computed, and every entity registration goes through the
one shared EntityRegistry, never a private dict an extractor keeps to
itself). supports()/priority()/version()/capabilities() let
ExtractorRegistry (registry.py) filter, order, and introspect
extractors without importing any concrete extractor class directly.
"""

from abc import ABC, abstractmethod
from typing import Optional

from backend.analysis_context.models import AnalysisContext
from backend.classification.pass2.models import ClassificationResult

from .document_index import DocumentIndex
from .entity_registry import EntityRegistry
from .models import ExtractionError, RecoveryAction


class ExtractionResult:
    """One extractor's own output — a small, deliberately untyped-beyond-
    entities bag (see extractors/*.py, each of which returns whichever
    domain-model list/object is actually theirs to produce: populations.py
    returns `entities=[]` alongside its own `populations=[...]`, not the
    other way around) plus this extractor's own errors/recoveries/
    warnings, which post_processor.py folds into MedicalUnderstanding's
    top-level errors/recoveries/warnings lists."""

    def __init__(
        self,
        entities: Optional[list] = None,
        errors: Optional[list[ExtractionError]] = None,
        recoveries: Optional[list[RecoveryAction]] = None,
        warnings: Optional[list[str]] = None,
        **extras,
    ) -> None:
        self.entities = entities or []
        self.errors = errors or []
        self.recoveries = recoveries or []
        self.warnings = warnings or []
        self.extras = extras

    def get(self, name: str, default=None):
        return self.extras.get(name, default)


class BaseExtractor(ABC):
    """Base interface for all extractors."""

    @abstractmethod
    def extract(
        self,
        index: DocumentIndex,
        classification: ClassificationResult,
        context: AnalysisContext,
        registry: EntityRegistry,
    ) -> ExtractionResult:
        raise NotImplementedError

    @abstractmethod
    def supports(self, context: AnalysisContext) -> bool:
        """Whether this extractor should run at all for this document —
        checked by ExtractorRegistry.get_enabled() before extract() is
        ever called (see registry.py)."""
        raise NotImplementedError

    @abstractmethod
    def priority(self) -> int:
        """Higher priority runs first — see registry.py's ordering."""
        raise NotImplementedError

    @abstractmethod
    def version(self) -> str:
        """Extractor version for compatibility."""
        raise NotImplementedError

    @abstractmethod
    def capabilities(self) -> list[str]:
        """Capability names for feature detection (e.g. a future caller
        checking "does some enabled extractor produce populations?"
        without importing PopulationExtractor directly)."""
        raise NotImplementedError
