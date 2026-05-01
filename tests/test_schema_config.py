"""Tests for Rime schema settings that affect candidate generation."""

from pathlib import Path

import yaml


def test_main_translator_does_not_generate_sentence_candidates():
    """Main translator should prefer explicit dictionary words over ad hoc phrases."""
    schema = yaml.safe_load(Path("schema/phah_taibun.schema.yaml").read_text(encoding="utf-8"))

    translator = schema["translator"]

    assert translator["enable_sentence"] is False
    assert translator["enable_user_dict"] is False
