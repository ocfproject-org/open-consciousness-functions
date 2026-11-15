"""Current narration is validated structurally and resolved from canonical YAML."""

import pytest
from tools.check_hplus_narration_integrity import check, narration_texts


@pytest.mark.integration
def test_all_current_function_and_shared_narration_resolves():
    assert check() == []
    texts = narration_texts()
    assert len(texts) > 58 * 3
    assert all(text.strip() and "{{" not in text for text in texts.values())
