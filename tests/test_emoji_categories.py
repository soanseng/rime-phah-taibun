from pathlib import Path

from scripts.build_emoji_categories import parse_emoji_test


def test_keeps_fully_qualified_skin_tone_emoji(tmp_path: Path) -> None:
    """Unicode's fully-qualified people entries retain their skin-tone glyphs."""
    source = tmp_path / "emoji-test.txt"
    source.write_text(
        "# group: People & Body\n"
        "1F44D 1F3FB ; fully-qualified # 👍🏻 E1.0 thumbs up: light skin tone\n",
        encoding="utf-8",
    )

    groups = parse_emoji_test(source)

    assert groups == [("People & Body", [("👍🏻", "thumbs up: light skin tone")])]
