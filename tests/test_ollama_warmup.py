import sys
import types
from unittest.mock import patch

from debug_assistant_latest import provenance
from debug_assistant_latest.ollama_warmup import warm_debug_model


MODEL_ID = "glm-4.7-flash:latest"
DIGEST = "a" * 64


class FakeClient:
    def __init__(self, *, digest=DIGEST, residents=None, after_digest=None, after_residents=None, response=None):
        self.digest = digest
        self.residents = list(residents or [])
        self.after_digest = after_digest
        self.after_residents = list(after_residents) if after_residents is not None else None
        self.response = response or {"response": "", "eval_count": 0, "load_duration": 1_000_000_000}
        self.generate_calls = []

    def list(self):
        digest = self.after_digest if self.generate_calls and self.after_digest is not None else self.digest
        return {"models": [{"model": MODEL_ID, "digest": digest}]}

    def ps(self):
        residents = (
            self.after_residents
            if self.generate_calls and self.after_residents is not None
            else self.residents
        )
        return {"models": [{"model": model} for model in residents]}

    def generate(self, **kwargs):
        self.generate_calls.append(kwargs)
        return self.response


class FakeModel:
    def __init__(self, client):
        self.client = client

    def get_client(self):
        return self.client


def _warm(client, *, allowed=None, digest=DIGEST):
    return warm_debug_model(
        model=FakeModel(client),
        model_id=MODEL_ID,
        expected_digest=digest,
        allowed_model_ids=allowed or [MODEL_ID],
        keep_alive="10m",
    )


def test_cold_candidate_uses_empty_zero_token_request_and_checks_residency():
    client = FakeClient(after_residents=[MODEL_ID])

    record = _warm(client)

    assert record["ready"] is True
    assert record["preloaded"] is True
    assert record["resident_models_before"] == []
    assert record["resident_models_after"] == [MODEL_ID]
    assert record["model_digest_after"] == DIGEST
    assert record["load_duration_s"] == 1.0
    assert "response" not in record
    assert client.generate_calls == [
        {
            "model": MODEL_ID,
            "prompt": "",
            "stream": False,
            "keep_alive": "10m",
            "options": {"num_predict": 0},
        }
    ]


def test_already_resident_candidate_still_refreshes_keep_alive():
    client = FakeClient(residents=[MODEL_ID], after_residents=[MODEL_ID])

    record = _warm(client)

    assert record["ready"] is True
    assert len(client.generate_calls) == 1
    assert client.generate_calls[0]["keep_alive"] == "10m"


def test_unrelated_resident_model_blocks_without_unloading_or_generating():
    unrelated = "researcher-model:latest"
    client = FakeClient(residents=[unrelated])

    record = _warm(client)

    assert record["ready"] is False
    assert record["reason"] == "unrelated_model_resident_before_warmup"
    assert client.generate_calls == []
    assert record["resident_models_before"] == [unrelated]


def test_digest_mismatch_blocks_before_generation():
    client = FakeClient(digest="b" * 64)

    record = _warm(client)

    assert record["ready"] is False
    assert record["reason"] == "candidate_digest_mismatch_before_warmup"
    assert client.generate_calls == []


def test_changed_digest_or_missing_residency_after_generation_fails_closed():
    changed_digest = FakeClient(after_residents=[MODEL_ID], after_digest="b" * 64)
    missing_residency = FakeClient(after_residents=[])

    digest_record = _warm(changed_digest)
    residency_record = _warm(missing_residency)

    assert digest_record["reason"] == "candidate_digest_mismatch_after_warmup"
    assert residency_record["reason"] == "candidate_not_resident_at_debug_entry"


def test_nonempty_warmup_response_is_not_used_and_fails_closed():
    client = FakeClient(
        after_residents=[MODEL_ID],
        response={"response": "unexpected output", "eval_count": 2},
    )

    record = _warm(client)

    assert record["ready"] is False
    assert record["reason"] == "warmup_generated_output"
    assert "response" not in record


def test_provenance_keeps_the_full_ollama_digest():
    client = FakeClient()
    ollama_module = types.SimpleNamespace(Client=lambda **_kwargs: client)

    with patch.dict(sys.modules, {"ollama": ollama_module}):
        revisions = provenance._ollama_model_revisions()

    assert revisions == [{"name": MODEL_ID, "digest": DIGEST}]
