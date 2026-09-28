from synlab.personas import generate_personas, personas_json


def test_personas_are_deterministic_for_a_seed():
    first = generate_personas(9182, 25)
    second = generate_personas(9182, 25)
    assert first == second
    assert personas_json(first).encode("utf-8") == personas_json(second).encode("utf-8")


def test_persona_fields_and_edge_case_tendencies_are_present():
    persona = generate_personas(3, 1)[0]
    assert {"persona_id", "name", "role", "skill_level", "goal", "patience", "communication_style", "tendencies"} <= set(persona)
    assert set(persona["tendencies"]) == {"typos", "vague_requests", "repeated_retries", "frustration_escalation"}
    assert all(0 <= score <= 100 for score in persona["tendencies"].values())
