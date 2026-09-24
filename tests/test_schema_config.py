"""Tests for Rime schema settings that affect candidate generation."""

from pathlib import Path

import yaml


def test_main_translator_learns_and_composes_without_inventing_user_words():
    """The IME must personalise, compose unknown phrases, but never memorise junk.

    Users type out-of-dictionary phrases (e.g. kio-tiann) and short sentences
    and select each syllable's word one by one. Notes on the three flags:

    - enable_user_dict True  -> picked words rise in ranking over time (learning)
    - enable_encoder  False  -> commits are NOT encoded into new user phrases
    - enable_sentence True   -> intent flag: keep composition enabled. librime's
      script_translator composes unknown phrases unconditionally since 1.6
      (verified in 1.6.0/1.7.3/1.8.5/1.9.0/1.11.2/1.13.1 sources; the flag is
      only consulted by table_translator), so the behavioural contract is
      pinned by the real-engine tests, not this YAML value.
    """
    schema = yaml.safe_load(Path("schema/phah_taibun.schema.yaml").read_text(encoding="utf-8"))

    translator = schema["translator"]

    assert translator["enable_user_dict"] is True
    assert translator["enable_encoder"] is False
    assert translator["enable_sentence"] is True


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
    assert any("Lua 擴充模組" in line and f"{module_count} 個" in line for line in readme.splitlines())
    assert any("Lua 模組" in line and f"{module_count} 個" in line for line in guide.splitlines())


def test_docs_describe_unbundled_optional_assets_as_not_enabled():
    """Release docs must not present rime-ice assets as built-in features."""
    readme = Path("README.md").read_text(encoding="utf-8")
    quickstart = Path("docs/quickstart-card.md").read_text(encoding="utf-8")
    guide = Path("docs/user-guide.md").read_text(encoding="utf-8")
    docs = "\n".join((readme, quickstart, guide))

    assert "| **英文混打** | 內建" not in docs
    assert "直接打英文單字" not in docs
    assert "正式安裝包沒有綁定 rime-ice" in guide
    assert any("未內建" in line and "Ctrl+Space" in line for line in readme.splitlines())
    # Emoji stance (0.10): bundled from rime-emoji (LGPL-3.0) with an F4
    # toggle; docs must present it as bundled, not as an unbundled asset.
    assert any(line.startswith("| **Emoji** | 內建") for line in readme.splitlines())
    assert any(line.startswith("| **Emoji** | 內建") for line in guide.splitlines())


def test_output_mode_choices_persist_across_sessions_and_restarts():
    """F4-selected output modes (TL/POJ, Han/Lo, auto/manual mix) persist.

    The schema must not set reset on these switches (that would force the
    default every time the schema is activated), and default.custom.yaml must
    list them under switcher/save_options so librime stores the state in
    user.yaml and restores it on new sessions.
    """
    schema = yaml.safe_load(Path("schema/phah_taibun.schema.yaml").read_text(encoding="utf-8"))
    switches = {s["name"]: s for s in schema["switches"]}

    for option in ("poj_mode", "full_romanization", "hanlo_manual"):
        assert option in switches
        assert "reset" not in switches[option]

    custom = yaml.safe_load(Path("schema/default.custom.yaml").read_text(encoding="utf-8"))
    saved = {value for key, value in custom["patch"].items() if key.startswith("switcher/save_options/")}
    assert saved == {"poj_mode", "full_romanization", "hanlo_manual", "emoji_conversion"}


def test_telex_schema_shares_main_dictionary_and_normalizes_input():
    """拍台文(Telex) is an input-layer variant: same dict, Telex spellings in.

    The Telex schema must reuse the main dictionary (one canonical numeric-TL
    source of truth, one user dict) and must normalize input through the
    phah_taibun_telex Lua processor before the speller sees it. The ph→f
    fuzzy derive is forbidden here: f is the Telex syllable-hyphen key.
    """
    schema = yaml.safe_load(Path("schema/phah_taibun_telex.schema.yaml").read_text(encoding="utf-8"))

    assert schema["schema"]["schema_id"] == "phah_taibun_telex"
    assert schema["translator"]["dictionary"] == "phah_taibun"
    assert schema["translator"]["prism"] == "phah_taibun_telex"

    algebra = "\n".join(schema["speller"]["algebra"])
    assert "derive/ph/f/" not in algebra
    assert "derive/^tsh/zh/" in algebra
    assert "derive/^ts/z/" in algebra
    assert algebra.index("derive/^tsh/zh/") < algebra.index("derive/^ts/z/")

    processors = schema["engine"]["processors"]
    assert processors[0] == "lua_processor@*phah_taibun_telex"


def test_telex_schema_is_registered_alongside_the_main_schema():
    """Fresh installs get both schemas from default.custom.yaml and rime.lua."""
    custom = yaml.safe_load(Path("schema/default.custom.yaml").read_text(encoding="utf-8"))
    patch = custom["patch"]
    schemas = [entry["schema"] for key, entry in patch.items() if key.startswith("schema_list/")]

    assert "phah_taibun" in schemas
    assert "phah_taibun_telex" in schemas

    rime_lua = Path("rime.lua").read_text(encoding="utf-8")
    assert 'phah_taibun_telex = require("phah_taibun_telex")' in rime_lua


def test_main_schema_does_not_load_the_telex_processor():
    """The 拍台文(台) schema keeps its exact current input behavior."""
    schema = yaml.safe_load(Path("schema/phah_taibun.schema.yaml").read_text(encoding="utf-8"))

    assert all("telex" not in p for p in schema["engine"]["processors"])


def test_emoji_conversion_is_wired_and_default_on():
    """Emoji (rime-emoji, LGPL-3.0): 兩方案都掛 simplifier@emoji_conversion,
    開關預設開, 資產在 opencc/ 且附授權標示."""
    for schema_name in ("phah_taibun", "phah_taibun_telex"):
        schema = yaml.safe_load(Path(f"schema/{schema_name}.schema.yaml").read_text(encoding="utf-8"))
        filters = schema["engine"]["filters"]
        assert "simplifier@emoji_conversion" in filters, schema_name
        assert filters.index("simplifier@emoji_conversion") < filters.index(
            "lua_filter@*phah_taibun_origin"
        ), schema_name
        emoji_switch = next(
            (s for s in schema["switches"] if s["name"] == "emoji_conversion"), None
        )
        assert emoji_switch is not None and emoji_switch.get("reset") == 1, schema_name

    custom = yaml.safe_load(Path("schema/default.custom.yaml").read_text(encoding="utf-8"))
    saved = [
        value
        for key, value in custom["patch"].items()
        if key.startswith("switcher/save_options")
    ]
    assert saved and "emoji_conversion" in saved


def test_emoji_opencc_assets_are_vendored_with_attribution():
    """opencc/ 內含 rime-emoji 三檔 + LGPL 授權與作者標示."""
    opencc = Path("opencc")
    for name in ("emoji.json", "emoji_word.txt", "emoji_category.txt"):
        assert (opencc / name).is_file(), name
    attribution = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (opencc.glob("*LICENSE*") or []) if p.is_file()
    )
    assert "LESSER GENERAL PUBLIC LICENSE" in attribution
    assert "雪齋" in attribution or "rime-emoji" in attribution
