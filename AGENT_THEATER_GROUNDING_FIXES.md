# Agent Theater Grounding Fixes

## Overview
Fixed the Agent Theater chatbot to ensure responses are reliably based on real analysis context rather than generic text.

## Issues Fixed

### 1. Context Wiring
- **Problem**: `render_agent_theater` was called without passing analysis context (`resp`)
- **Solution**: Store latest analysis result in `st.session_state["latest_analysis_result"]` and pass it to `render_agent_theater`

### 2. Response Logic Strengthening
- **Problem**: `_llm_operator_answer` could produce generic output when context was missing
- **Solution**: Added explicit fallback behavior when context is unavailable
- **Fallback message**: "I need current analysis data. Run/refresh analysis first, then ask again."

### 3. Echo Prevention
- **Problem**: LLM could generate low-quality echo/paraphrase responses
- **Solution**: Enhanced echo detection and fallback to rule-based answers

### 4. Provenance Markers
- **Problem**: No indication of response source
- **Solution**: Added source notes like: "Source: issues=2, actions=1, anomaly_count=5"

## Files Modified

### `dashboard/app.py`
- Store analysis result in session state: `st.session_state["latest_analysis_result"] = result`
- Pass result to render_agent_theater: `render_agent_theater(real_messages, resp=latest_result)`

### `dashboard/ui/agent_theater.py`
- Enhanced `_llm_operator_answer` with context validation
- Added provenance markers to all responses
- Improved fallback logic

## Testing

### Unit Tests Created
- `tests/test_agent_theater_grounding.py`: Comprehensive test suite
- `scripts/run_grounding_tests.py`: Simple test runner

### Test Coverage
- Rich context responses include issue names/severity
- Missing context triggers appropriate fallback
- Anomaly questions include metrics
- Echo prevention works
- Provenance markers always present
- Rule-based answers prioritized

## Manual Verification Checklist

1. **Start live analysis**: Begin simulation in dashboard
2. **Ask "What are the issues?"**: Should list actual issues with severity/confidence
3. **Ask "What should I do first?"**: Should reference top action from analysis
4. **Ask with no active analysis**: Should show "need current analysis data" message
5. **Confirm responses change**: Different analysis data produces different responses

## Running Tests

```bash
# Run all grounding tests
python scripts/run_grounding_tests.py

# Run individual test
python -c "from tests.test_agent_theater_grounding import TestAgentTheaterGrounding; t = TestAgentTheaterGrounding(); t.test_llm_answer_with_missing_context(); print('Test passed')"
```

## Validation Results

✅ **Context Wiring**: Analysis results now passed to chatbot
✅ **Fallback Logic**: Clear messages when no context available
✅ **Provenance**: All responses include source markers
✅ **Echo Prevention**: Low-quality responses rejected
✅ **Rule-based Priority**: Known questions use structured answers
✅ **Test Coverage**: Unit tests verify all scenarios