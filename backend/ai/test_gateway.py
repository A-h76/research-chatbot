from backend.ai.gateway import AIGateway
from backend.ai.model_router import ModelRouter


class _StubRegistry:
    def __init__(self):
        self.calls = []

    def call(self, model, messages, **kwargs):
        self.calls.append((model, messages, kwargs))
        return {
            "content": "ok",
            "model": model,
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
            "cost": 0.001,
        }


def _gateway():
    router = ModelRouter(
        {
            "paper_analysis": "gpt-4o",
            "rag": "gpt-4o-mini",
            "_default": "gpt-4o-mini",
        }
    )
    return AIGateway(router)


def test_resolve_model_by_mode_from_policy():
    gw = _gateway()
    assert gw.resolve_model("paper_analysis", mode="fast").startswith("gpt-")
    assert gw.resolve_model("paper_analysis", mode="publication").startswith("gpt-")


def test_confidence_routing_escalates_to_publication():
    gw = _gateway()
    m1 = gw.resolve_model("paper_analysis", mode="fast", confidence=0.5)
    m2 = gw.resolve_model("paper_analysis", mode="publication")
    assert m1 == m2


def test_fallback_to_model_router_for_unknown_task():
    gw = _gateway()
    assert gw.resolve_model("unknown_task", mode="balanced") == "gpt-4o-mini"


def test_call_uses_resolved_model():
    gw = _gateway()
    reg = _StubRegistry()
    out = gw.call(
        model_registry=reg,
        task="paper_analysis",
        mode="balanced",
        messages=[{"role": "user", "content": "hello"}],
        user_id=1,
    )
    assert out["content"] == "ok"
    assert reg.calls
