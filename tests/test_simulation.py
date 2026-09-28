import json

from synlab.personas import generate_personas
from synlab.simulation import simulate_sessions
from synlab.storage import encode_json


def test_simulation_transcripts_are_byte_identical_for_same_seed():
    personas_a = generate_personas(771, 20)
    personas_b = generate_personas(771, 20)
    first = simulate_sessions(771, "defects", personas_a)
    second = simulate_sessions(771, "defects", personas_b)
    assert encode_json(first).encode("utf-8") == encode_json(second).encode("utf-8")
    assert json.loads(encode_json(first)) == second


def test_planted_fixture_detects_required_failure_types():
    personas = generate_personas(0, 40)
    sessions = simulate_sessions(0, "planted-defects", personas)
    codes = {failure["code"] for session in sessions for failure in session["failures"]}
    assert {"TIMEOUT", "CONTRADICTION", "UNANSWERED", "FRUSTRATION_TRIGGER"} <= codes

    for session in sessions:
        interactions = session["interactions"]
        assert all("user_input" in item and "target_response" in item and "latency_ms" in item for item in interactions)
        assert all(failure["interaction_id"] in {item["interaction_id"] for item in interactions} for failure in session["failures"])


def test_happy_and_slow_fixtures_have_distinct_scripted_behaviors():
    personas = generate_personas(12, 40)
    happy = simulate_sessions(12, "happy-path", personas)
    slow = simulate_sessions(12, "slow-confusing", personas)
    assert all(not session["failures"] for session in happy)
    slow_codes = {failure["code"] for session in slow for failure in session["failures"]}
    assert "CONFUSING_RESPONSE" in slow_codes
    assert "SLOW_RESPONSE" in slow_codes
