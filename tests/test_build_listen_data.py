"""build_listen_data 的單元測試: 欄位解析, 對齊, 選取, HTTP Range 檔案物件 (攏毋需網路)."""

import io
import zipfile

from scripts.build_listen_data import (
    HttpRangeFile,
    align_slots,
    label_key,
    parse_numbered,
    row_candidates,
    select_items,
    split_han_tl,
    zip_basename_map,
)

SENT6_HAN = "我欲去學校讀冊。"
SENT6_TL = "Guá beh khì ha̍k-hāu tha̍k tsheh."


def make_row(word_id, word, sentences, audio_ids):
    """拍一个 kautian.csv 檢測列. sentences: [(label, body)]; audio_ids: {label: id}."""
    ex = "\n".join(f"{lb}. {body}" for lb, body in sentences)
    ho = "\n".join(f"{lb}. 華語例句 {lb}" for lb, _ in sentences)
    au = "\n".join(f"{lb}. {audio_ids[lb]}" for lb, _ in sentences if lb in audio_ids)
    return {"詞目id": str(word_id), "漢字": word, "例句": ex, "例句-華語": ho, "例句-音檔": au}


# --- parse_numbered: 三个有編號的欄位 ---


def test_parse_numbered_reads_multiline_numbered_columns():
    text = (
        "1. 一蕊花 (tsi̍t luí hue)\n"
        "2. 紅嬰仔哭甲一身軀汗。 (Âng-enn-á khàu kah tsi̍t sin-khu kuānn.)\n"
        "3-1. 一睏仔 (tsi̍t-khùn-á)\n"
        "3-2. 一絲仔 (tsi̍t-si-á)"
    )
    got = parse_numbered(text)
    assert got["1"] == "一蕊花 (tsi̍t luí hue)"
    assert got["2"] == "紅嬰仔哭甲一身軀汗。 (Âng-enn-á khàu kah tsi̍t sin-khu kuānn.)"
    assert got["3-1"] == "一睏仔 (tsi̍t-khùn-á)"
    assert got["3-2"] == "一絲仔 (tsi̍t-si-á)"


def test_parse_numbered_appends_wrapped_lines_to_previous_entry():
    text = "1. 頭前一句\nkoh一个繼續\n2. 後壁一句"
    assert parse_numbered(text) == {"1": "頭前一句 koh一个繼續", "2": "後壁一句"}


def test_label_key_sorts_naturally():
    assert sorted(["10", "2", "3-1", "3-2"], key=label_key) == ["2", "3-1", "3-2", "10"]


# --- split_han_tl: 提上尾一个括號做羅馬字 ---


def test_split_han_tl_takes_last_paren_group():
    han, tl = split_han_tl("紅嬰仔哭甲一身軀汗。 (Âng-enn-á khàu kah tsi̍t sin-khu kuānn.)")
    assert han == "紅嬰仔哭甲一身軀汗。"
    assert tl == "Âng-enn-á khàu kah tsi̍t sin-khu kuānn."


def test_split_han_tl_keeps_fullwidth_parens_inside_han():
    han, tl = split_han_tl("有一工（好天時）(hó-thinn-sî)")  # noqa: RUF001 - 漢字內底有全形括號
    assert han == "有一工（好天時）"  # noqa: RUF001 - 漢字內底有全形括號
    assert tl == "hó-thinn-sî"


def test_split_han_tl_rejects_text_without_roman_tail():
    assert split_han_tl("伊是醫生。") is None
    assert split_han_tl("伊是醫生。 (華語註解)") is None


# --- align_slots: 漢字數 + 羅馬字音節數有對齊無 ---


def test_align_slots_counts_han_chars_plus_roman_runs():
    assert align_slots("一蕊花", "tsi̍t luí hue") == 3
    assert align_slots("紅嬰仔哭甲一身軀汗。", "Âng-enn-á khàu kah tsi̍t sin-khu kuānn.") == 9
    assert align_slots("我ê冊", "guá ê tsheh") == 3
    assert align_slots("chhó--ê 佇遮。", "tshó--ê tī tsia.") == 4


def test_align_slots_rejects_mismatch_and_broken_tl():
    assert align_slots("伊誠漂亮。", "I tsiânn súi.") is None
    assert align_slots("一蕊花", "tsi̍t luí hue chhim") is None
    assert align_slots("一蕊花", "：、；") is None  # noqa: RUF001 - 壞羅馬字欄
    assert align_slots("一蕊花", "") is None


# --- row_candidates + select_items: 共三欄照標籤接起來, 揀出題目 ---


def test_row_candidates_joins_three_columns_by_label_and_strips_word_marker():
    cands = row_candidates(
        make_row(
            1,
            "一(替)",
            [("2", "紅嬰仔哭甲一身軀汗。 (Âng-enn-á khàu kah tsi̍t sin-khu kuānn.)")],
            {"2": "1-2-1"},
        )
    )
    assert len(cands) == 1
    c = cands[0]
    assert c["wordId"] == 1 and c["word"] == "一"
    assert c["han"] == "紅嬰仔哭甲一身軀汗。"
    assert c["tl"].startswith("Âng-enn-á")
    assert c["hoa"] == "華語例句 2"
    assert c["label"] == "2"
    assert c["audioId"] == "1-2-1"


def eligible_rows(n):
    return [make_row(i, f"字{i}", [("1", f"{SENT6_HAN} ({SENT6_TL})")], {"1": f"{i}-1-1"}) for i in range(1, n + 1)]


def test_select_items_is_deterministic_one_per_word_and_evenly_spread():
    candidates = [c for row in eligible_rows(6) for c in row_candidates(row)]
    audio = {f"{i}-1-1.mp3" for i in range(1, 7)}
    first = select_items(candidates, audio, 4)
    assert first == select_items(candidates, audio, 4)
    assert [c["wordId"] for c in first] == [1, 2, 4, 5]
    assert len({c["wordId"] for c in select_items(candidates, audio, 100)}) == 6


def test_select_items_keeps_only_first_eligible_sentence_per_entry():
    row = make_row(
        7,
        "七",
        [("1", f"{SENT6_HAN} ({SENT6_TL})"), ("2", "媽媽佇咧煮飯。 (Má-má tī-leh tsú-pn̄g.)")],
        {"1": "7-1-1", "2": "7-2-1"},
    )
    picked = select_items(row_candidates(row), {"7-1-1.mp3", "7-2-1.mp3"}, 10)
    assert [c["label"] for c in picked] == ["1"]


def test_select_items_filters_phrases_misaligned_and_missing_audio():
    long17 = "一" * 17 + "。" + " (" + " ".join(["it"] * 17) + ".)"
    rows = [
        make_row(1, "一", [("1", "一蕊花 (tsi̍t luí hue)")], {"1": "1-1-1"}),  # 短語, 無句號
        make_row(2, "二", [("1", "伊誠漂亮。 (I tsiânn súi.)")], {"1": "2-1-1"}),  # 對毋齊
        make_row(3, "三", [("1", f"{SENT6_HAN} ({SENT6_TL})")], {}),  # 無音檔欄位
        make_row(4, "四", [("1", f"{SENT6_HAN} ({SENT6_TL})")], {"1": "4-1-1"}),  # 音檔無佇 zip 內底
        make_row(5, "五", [("1", long17)], {"1": "4-1-1"}),  # 超過 16 拍 (音檔有佇 zip)
    ]
    candidates = [c for row in rows for c in row_candidates(row)]
    picked = select_items(candidates, {"4-1-1.mp3"}, 10)
    assert [c["wordId"] for c in picked] == [4]


def test_zip_basename_map_matches_by_basename():
    got = zip_basename_map(sorted(["0/1-1-1.mp3", "29/29944-1-2.mp3", "readme.txt", "9/9-9-9.mp3", "8/8-8-8.MP3"]))
    assert got == {
        "1-1-1.mp3": "0/1-1-1.mp3",
        "29944-1-2.mp3": "29/29944-1-2.mp3",
        "9-9-9.mp3": "9/9-9-9.mp3",
        "8-8-8.mp3": "8/8-8-8.MP3",
    }


# --- HttpRangeFile: 假 fetch (無網路) ---


def build_zip_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("filler/pad.bin", bytes(600_000))
        zf.writestr("0/1-1-1.mp3", b"AAA" * 1365)  # 4095 bytes
        zf.writestr("29/29944-1-2.mp3", b"BBB" * 2730)  # 8190 bytes
    return buf.getvalue()


def range_fetch_factory(data, calls):
    def fetch(start, end):
        calls.append((start, end))
        return data[start:end]

    return fetch


def test_http_range_file_reads_only_needed_blocks_and_matches_zipfile():
    data = build_zip_bytes()
    calls = []
    rf = HttpRangeFile("mem://leku-mp3.zip", fetch=range_fetch_factory(data, calls), block_size=4096, size=len(data))
    with zipfile.ZipFile(rf) as zf:
        assert zf.namelist() == ["filler/pad.bin", "0/1-1-1.mp3", "29/29944-1-2.mp3"]
        assert zf.read("29/29944-1-2.mp3") == b"BBB" * 2730
        assert zf.read("0/1-1-1.mp3") == b"AAA" * 1365
    fetched = sum(end - start for start, end in calls)
    assert fetched < len(data) // 10  # 干焦讀需要的一段, 毋是整只 zip
    for start, end in calls:
        assert 0 <= start < end <= len(data)


def test_http_range_file_block_cache_avoids_refetch():
    data = build_zip_bytes()
    calls = []
    rf = HttpRangeFile("mem://x", fetch=range_fetch_factory(data, calls), block_size=1024, size=len(data))
    first = rf.read(64)
    n_calls = len(calls)
    rf.seek(0)
    assert rf.read(64) == first == data[:64]
    assert len(calls) == n_calls  # 第二擺讀仝一个區塊, 袂閣 Fetch
    assert calls[0][0] == 0


def test_http_range_file_seek_and_eof_short_read():
    data = build_zip_bytes()
    rf = HttpRangeFile("mem://x", fetch=range_fetch_factory(data, []), block_size=1024, size=len(data))
    rf.seek(0, 2)
    assert rf.tell() == len(data)
    rf.seek(-10, 2)
    assert rf.read(100) == data[-10:]  # 讀過 EOF, 愛裁短
    rf.seek(5)
    assert rf.tell() == 5
    assert rf.read(4) == data[5:9]


def test_http_range_file_retries_transient_fetch_errors():
    data = build_zip_bytes()
    calls = []

    def flaky(start, end):
        calls.append((start, end))
        if len(calls) == 1:
            raise TimeoutError("transient")
        return data[start:end]

    rf = HttpRangeFile("mem://x", fetch=flaky, block_size=1024, size=len(data), retry_sleep=0)
    assert rf.read(16) == data[:16]
    assert len(calls) == 2
