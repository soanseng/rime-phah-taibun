"""寫作檢查的連字符詞表: 教典詞目, 例句內底教育部家己連字號寫的才收."""

from scripts.build_check_data import hyphen_words


def _row(han: str, roman: str, examples: str) -> dict[str, str]:
    return {"漢字": han, "羅馬字": roman, "例句": examples}


def test_keeps_headword_that_moe_examples_write_hyphenated():
    rows = [
        _row("身軀", "sin-khu", "1. 洗身軀。(Sé sin-khu.)"),
        _row("毋是", "m̄-sī", "1. 我毋是。(Guá m̄ sī.)\n2. 伊毋是。(I m̄ sī.)"),
    ]
    assert hyphen_words(rows, known={"身軀", "毋是"}) == ["身軀"]


def test_function_word_pair_spaced_in_other_entries_examples_is_dropped():
    # 毋是 本身的例句無出現, 毋過別條例句寫 m̄ sī (分開) → 算分開較濟, 毋收
    rows = [
        _row("毋是", "m̄-sī", ""),
        _row("外人", "guā-lâng", "1. 阿姨毋是外人。(A-î m̄ sī guā-lâng.)"),
    ]
    assert hyphen_words(rows, known={"毋是", "外人"}) == ["外人"]


def test_headword_never_seen_in_examples_is_kept_and_markers_stripped():
    rows = [_row("紅嬰仔(替)", "âng-enn-á", "")]
    assert hyphen_words(rows, known={"紅嬰仔"}) == ["紅嬰仔"]


def test_single_syllable_and_unknown_words_are_skipped():
    rows = [_row("一", "tsi̍t", ""), _row("無收", "bô-siu", "")]
    assert hyphen_words(rows, known={"一"}) == []
