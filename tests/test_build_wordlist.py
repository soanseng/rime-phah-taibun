"""Wordlist generation for whole-sentence romanization word boundaries."""

from scripts.build_wordlist import generate_wordlist


def test_generates_multi_syllable_cjk_words_only(tmp_path):
    dict_file = tmp_path / "dict.yaml"
    dict_file.write_text(
        "---\nname: phah_taibun\n...\n"
        "台語\ttai5 gi2\t100\n"  # multi-syllable CJK: keep
        "是按怎\tsi7 an2 tsuann2\t90\n"  # 3-syllable CJK: keep
        "人\tlang5\t80\n"  # single syllable: skip
        "做的\ttso3  e5\t70\n"  # lighttone double space: keep, normalized
        "sī-án\tlang5\t60\n"  # non-CJK text: skip
        "轉--來\ttng2  lai5\t50\n",  # lighttone-marked text: skip
        encoding="utf-8",
    )
    out = tmp_path / "phah_taibun.wordlist"
    generate_wordlist(dict_file, out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines == ["做的\ttso3 e5", "台語\ttai5 gi2", "是按怎\tsi7 an2 tsuann2"]


def test_multiple_readings_pipe_joined(tmp_path):
    dict_file = tmp_path / "dict.yaml"
    dict_file.write_text(
        "---\nname: phah_taibun\n...\n大志\ttai7 tsi3\t10\n代誌\ttai7 tsi3\t20\n代誌\tdai7 tsi3\t5\n",
        encoding="utf-8",
    )
    out = tmp_path / "phah_taibun.wordlist"
    generate_wordlist(dict_file, out)
    lines = out.read_text(encoding="utf-8").splitlines()
    # one row per word, readings deduped and pipe-joined
    assert lines == ["代誌\tdai7 tsi3|tai7 tsi3", "大志\ttai7 tsi3"]
