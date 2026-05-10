"""
Unit tests for Agent Theater chatbot grounding functionality.
Tests ensure responses are based on real analysis context, not generic text.
"""

from unittest.mock import patch, MagicMock
from dashboard.ui.agent_theater import _llm_operator_answer, _rule_based_operator_answer


class TestAgentTheaterGrounding:
    """Test suite for ensuring chatbot responses are grounded in analysis data."""

    def test_llm_answer_with_rich_context(self):
        """Test that LLM answers include issue names/severity when rich context provided."""
        rich_resp = {
            "issues": [
                {"name": "HVAC Drift", "severity": "high", "confidence": 0.85},
                {"name": "Lighting Waste", "severity": "medium", "confidence": 0.72}
            ],
            "actions": [
                {"title": "Calibrate HVAC sensors", "what": "Check thermostat settings", "when": "today"}
            ],
            "metrics": {"anomaly_count": 5},
            "issue_card": {"value": "HVAC Drift (confidence=85%)"},
            "cause_card": {"value": "Sensor calibration issue"},
            "action_card": {"value": "Calibrate HVAC sensors"}
        }

        with patch('dashboard.ui.agent_theater.generate') as mock_generate:
            mock_generate.return_value = "Check HVAC sensors today and calibrate them properly."
            result = _llm_operator_answer("what are the issues?", rich_resp)

            # Should use rule-based answer for this specific question
            assert "HVAC Drift" in result
            assert "85%" in result
            assert "Source: issues=2, actions=1, anomaly_count=5" in result

    def test_llm_answer_with_missing_context(self):
        """Test fallback behavior when no analysis context is available."""
        result = _llm_operator_answer("what should I do first?", None)
        assert "need current analysis data" in result.lower()
        assert "run/refresh analysis first" in result.lower()

    def test_llm_answer_with_empty_context(self):
        """Test fallback when context exists but has no useful analysis fields."""
        empty_resp = {"some_other_field": "value"}
        result = _llm_operator_answer("what are the issues?", empty_resp)
        assert "need current analysis data" in result.lower()

    def test_anomaly_question_with_metrics(self):
        """Test anomaly question includes anomaly_count from metrics."""
        resp_with_metrics = {
            "metrics": {"anomaly_count": 7},
            "issues": [{"name": "Test Issue"}],
            "actions": [{"title": "Test Action"}]
        }

        result = _llm_operator_answer("how many anomalies are there?", resp_with_metrics)
        assert "7 anomalies" in result
        assert "Source: issues=1, actions=1, anomaly_count=7" in result

    def test_echo_prevention(self):
        """Test that echo/paraphrase detection prevents low-quality responses."""
        resp = {
            "issues": [{"name": "Test Issue"}],
            "actions": [{"title": "Test Action"}],
            "metrics": {"anomaly_count": 1}
        }

        with patch('dashboard.ui.agent_theater.generate') as mock_generate:
            # Mock a response that would be detected as echo
            mock_generate.return_value = "What are the issues you are asking about?"
            result = _llm_operator_answer("what are the issues?", resp)

            # Should fall back to rule-based answer
            assert "Test Issue" in result
            assert "Source:" in result

    def test_provenance_marker_always_present(self):
        """Test that all responses include provenance markers."""
        resp = {
            "issues": [{"name": "Issue 1"}, {"name": "Issue 2"}],
            "actions": [{"title": "Action 1"}],
            "metrics": {"anomaly_count": 3}
        }

        # Test rule-based answer
        result = _llm_operator_answer("what are the issues?", resp)
        assert "Source: issues=2, actions=1, anomaly_count=3" in result

        # Test with LLM generation
        with patch('dashboard.ui.agent_theater.generate') as mock_generate:
            mock_generate.return_value = "Check the equipment settings carefully."
            result = _llm_operator_answer("what should I check?", resp)
            assert "Source: issues=2, actions=1, anomaly_count=3" in result

    def test_rule_based_answers_still_work(self):
        """Test that rule-based answers are still prioritized for known questions."""
        resp = {
            "issues": [{"name": "Test Issue"}],
            "actions": [{"title": "Test Action"}],
            "metrics": {"anomaly_count": 1}
        }

        result = _llm_operator_answer("what should I do first?", resp)
        assert "top action" in result.lower()
        assert "Source:" in result


if __name__ == "__main__":
    # Run basic smoke tests
    test_instance = TestAgentTheaterGrounding()

    print("Running Agent Theater grounding tests...")

    try:
        test_instance.test_llm_answer_with_rich_context()
        print("✓ Rich context test passed")
    except Exception as e:
        print(f"✗ Rich context test failed: {e}")

    try:
        test_instance.test_llm_answer_with_missing_context()
        print("✓ Missing context test passed")
    except Exception as e:
        print(f"✗ Missing context test failed: {e}")

    try:
        test_instance.test_anomaly_question_with_metrics()
        print("✓ Anomaly metrics test passed")
    except Exception as e:
        print(f"✗ Anomaly metrics test failed: {e}")

    try:
        test_instance.test_provenance_marker_always_present()
        print("✓ Provenance marker test passed")
    except Exception as e:
        print(f"✗ Provenance marker test failed: {e}")

    print("Basic tests completed. Run with pytest for full test suite.")