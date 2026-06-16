"""Tests for Rime schema settings that affect candidate generation."""

from pathlib import Path

import yaml


def test_main_translator_learns_user_preferences_without_ad_hoc_phrases():
    """The IME must personalise to the user's own picks, but never invent phrases.

    A daily-use input method is expected to learn: words you select should rank
    higher next time. That is exactly what a user dictionary provides.

    The original "no ad hoc candidates" guarantee (commit c6110d5) must survive,
    so it is pinned to the two flags that actually cause ad hoc output:

    - enable_user_dict True  -> picked words rise in ranking over time (learning)
    - enable_encoder  False  -> commits are NOT encoded into new user phrases
    - enable_sentence False  -> no ad hoc multi-word sentence candidates

    Re-enabling the encoder or sentence flag would regress c6110d5; disabling the
    user dict would strip the personalisation a daily IME needs. Pin all three.
    """
    schema = yaml.safe_load(Path("schema/phah_taibun.schema.yaml").read_text(encoding="utf-8"))

    translator = schema["translator"]

    assert translator["enable_user_dict"] is True
    assert translator["enable_encoder"] is False
    assert translator["enable_sentence"] is False


def test_origin_filter_runs_last_before_uniquifier():
    """The raw-romanization fallback candidate must land at the very end of the list.

    It is appended by phah_taibun_origin, which therefore has to sit after the
    candidate-transforming filters and immediately before the uniquifier (so a
    duplicate of an existing candidate is still de-duped).
    """
    schema = yaml.safe_load(Path("schema/phah_taibun.schema.yaml").read_text(encoding="utf-8"))

    filters = schema["engine"]["filters"]
    origin = "lua_filter@*phah_taibun_origin"

    assert origin in filters
    assert filters.index(origin) == filters.index("uniquifier") - 1


def test_speller_accepts_hyphen_for_romanization_input():
    """Hyphen must be accepted for multi-syllable and light-tone input."""
    schema = yaml.safe_load(Path("schema/phah_taibun.schema.yaml").read_text(encoding="utf-8"))

    speller = schema["speller"]

    assert "-" in speller["alphabet"]
    assert "-" in speller["delimiter"]
