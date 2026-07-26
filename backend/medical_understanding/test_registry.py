from backend.medical_understanding.config import MedicalUnderstandingConfig
from backend.medical_understanding.entity_registry import EntityRegistry
from backend.medical_understanding.interfaces import BaseExtractor, ExtractionResult
from backend.medical_understanding.registry import ExtractorRegistry


class _StubExtractor(BaseExtractor):
    def __init__(self, name="stub", supports_result=True, priority_value=50, raises=False, entities=None):
        self.name = name
        self._supports_result = supports_result
        self._priority = priority_value
        self._raises = raises
        self._entities = entities or []
        self.called = False

    def extract(self, index, classification, context, registry):
        self.called = True
        if self._raises:
            raise RuntimeError("boom")
        return ExtractionResult(entities=self._entities)

    def supports(self, context):
        return self._supports_result

    def priority(self):
        return self._priority

    def version(self):
        return "1.0.0"

    def capabilities(self):
        return [self.name]


def _config(names):
    return MedicalUnderstandingConfig(enabled_extractors=names)


def test_get_enabled_filters_by_config_and_supports():
    registry = ExtractorRegistry(_config(["a", "b"]))
    registry.register("a", _StubExtractor(supports_result=True))
    registry.register("b", _StubExtractor(supports_result=False))
    registry.register("c", _StubExtractor(supports_result=True))  # not in enabled_extractors

    enabled = registry.get_enabled(context=None)
    assert [name for name, _ in enabled] == ["a"]


def test_get_enabled_sorts_by_priority_descending():
    registry = ExtractorRegistry(_config(["low", "high"]))
    registry.register("low", _StubExtractor(priority_value=10))
    registry.register("high", _StubExtractor(priority_value=90))

    enabled = registry.get_enabled(context=None)
    assert [name for name, _ in enabled] == ["high", "low"]


def test_unregister_removes_extractor():
    registry = ExtractorRegistry(_config(["a"]))
    registry.register("a", _StubExtractor())
    registry.unregister("a")
    assert registry.get_enabled(context=None) == []


def test_execute_parallel_runs_all_enabled_and_isolates_a_crash():
    registry = ExtractorRegistry(_config(["good", "bad"]))
    good = _StubExtractor(name="good", priority_value=100, entities=["e1"])
    bad = _StubExtractor(name="bad", priority_value=50, raises=True)
    registry.register("good", good)
    registry.register("bad", bad)

    enabled = registry.get_enabled(context=None)
    results = registry.execute_parallel(
        enabled, index=None, classification=None, context=None, registry=EntityRegistry()
    )

    assert results["good"].entities == ["e1"]
    assert results["bad"].errors[0].extractor == "bad"
    assert good.called and bad.called


def test_execute_parallel_respects_tier_order():
    """A lower-priority extractor must never see a registry state from
    before a strictly-higher-priority extractor has finished — see
    registry.py's own module docstring on why this matters."""
    order: list[str] = []

    class _RecordingExtractor(BaseExtractor):
        def __init__(self, name, priority_value):
            self.name = name
            self._priority = priority_value

        def extract(self, index, classification, context, registry):
            order.append(self.name)
            return ExtractionResult()

        def supports(self, context):
            return True

        def priority(self):
            return self._priority

        def version(self):
            return "1.0.0"

        def capabilities(self):
            return []

    registry = ExtractorRegistry(_config(["first", "second", "third"]))
    registry.register("first", _RecordingExtractor("first", 100))
    registry.register("second", _RecordingExtractor("second", 50))
    registry.register("third", _RecordingExtractor("third", 50))

    enabled = registry.get_enabled(context=None)
    registry.execute_parallel(enabled, index=None, classification=None, context=None, registry=EntityRegistry())

    assert order[0] == "first"
    assert set(order[1:]) == {"second", "third"}


def test_sequential_execution_when_parallel_disabled():
    config = MedicalUnderstandingConfig(enabled_extractors=["a", "b"], enable_parallel=False)
    registry = ExtractorRegistry(config)
    registry.register("a", _StubExtractor(name="a", entities=["x"]))
    registry.register("b", _StubExtractor(name="b", entities=["y"]))

    enabled = registry.get_enabled(context=None)
    results = registry.execute_parallel(
        enabled, index=None, classification=None, context=None, registry=EntityRegistry()
    )
    assert results["a"].entities == ["x"]
    assert results["b"].entities == ["y"]
