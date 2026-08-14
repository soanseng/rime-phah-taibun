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


def test_schema_does_not_enable_unbundled_english_or_emoji_assets():
    """Every enabled schema component must be installable from the release payload."""
    schema = yaml.safe_load(Path("schema/phah_taibun.schema.yaml").read_text(encoding="utf-8"))

    assert "melt_eng" not in schema["schema"].get("dependencies", [])
    assert "table_translator@melt_eng" not in schema["engine"]["translators"]
    assert "simplifier@emoji" not in schema["engine"]["filters"]
    assert all(switch["name"] != "emoji" for switch in schema["switches"])
    assert "emoji" not in schema


def test_shortcut_docs_only_advertise_switches_enabled_by_the_schema():
    """F4/Ctrl+` documentation must not expose removed optional switches."""
    docs = [
        Path("README.md").read_text(encoding="utf-8"),
        Path("docs/quickstart-card.md").read_text(encoding="utf-8"),
        Path("docs/user-guide.md").read_text(encoding="utf-8"),
    ]
    shortcut_lines = [
        line
        for document in docs
        for line in document.splitlines()
        if line.startswith("|") and ("F4" in line or "Ctrl+`" in line)
    ]

    assert shortcut_lines
    assert all("emoji" not in line.lower() for line in shortcut_lines)
    assert "| ㄐ | j | l |" not in docs[2]
    assert "POJ 的點右音 `o͘` 請打 `ou`" in docs[1]
    assert "POJ 的點右音 `o͘` 請打 `ou`" in docs[2]



def test_documented_lua_module_count_matches_release_payload():
    """The public module count must track every Lua file shipped by installers."""
    module_count = len(list(Path("lua").glob("phah_taibun_*.lua")))
    readme = Path("README.md").read_text(encoding="utf-8")
    guide = Path("docs/user-guide.md").read_text(encoding="utf-8")

    assert f"lua-{module_count}%20modules" in readme
    assert any(
        "Lua 擴充模組" in line and f"{module_count} 個" in line
        for line in readme.splitlines()
    )
    assert any(
        "Lua 模組" in line and f"{module_count} 個" in line
        for line in guide.splitlines()
    )
