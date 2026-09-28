from synlab.clustering import cluster_sessions
from synlab.personas import generate_personas
from synlab.reporting import build_report_data, render_html, render_markdown
from synlab.simulation import simulate_sessions


def _sample():
    personas = generate_personas(0, 30)
    sessions = simulate_sessions(0, "defects", personas)
    return personas, sessions, cluster_sessions(sessions)


def test_planted_patterns_form_linked_expected_themes():
    personas, sessions, clusters = _sample()
    by_theme = {cluster["theme"]: cluster for cluster in clusters}
    assert "Requests exceed the wait budget" in by_theme
    assert "Repeated questions receive conflicting answers" in by_theme
    assert "Requests receive no answer" in by_theme
    assert "Repeated failures trigger frustration" in by_theme

    real_ids = {session["session_id"] for session in sessions}
    for cluster in clusters:
        assert cluster["session_ids"]
        assert set(cluster["session_ids"]) <= real_ids
        assert all(item["session_id"] in real_ids for item in cluster["evidence"])
        assert cluster["failure_signatures"]
        assert cluster["target_behavior_codes"]
        assert cluster["transcript_ngrams"]


def test_report_header_has_honesty_boundary_and_evidence():
    personas, sessions, clusters = _sample()
    data = build_report_data(clusters, sessions, len(personas))
    markdown = render_markdown(data, 0, "defects", len(personas))
    page = render_html(data, 0, "defects", len(personas))
    for report in (markdown, page):
        assert "HONESTY BOUNDARY" in report
        assert "All users are simulated" in report
        assert "All complaints are synthetic" in report
        assert "not user research" in report
    assert "Evidence pointer" in markdown
    assert "session-" in page


def test_report_rendering_is_deterministic():
    personas, sessions, clusters = _sample()
    data = build_report_data(clusters, sessions, len(personas))
    assert render_markdown(data, 0, "defects", len(personas)) == render_markdown(data, 0, "defects", len(personas))
    assert render_html(data, 0, "defects", len(personas)) == render_html(data, 0, "defects", len(personas))
