# ruff: noqa: RUF001, RUF002 - 測試資料是台文原文, 全形標點是本字
"""讀文章蓋趣味 文章資料建置: OpenTaigi 整理好的版面行 → 文章、詞彙、文法、出處、音檔對應."""

import pytest

from scripts import build_article_data as bad


def _line(text, column="right", role="note", size=10.63):
    return {"text": text, "column": column, "role": role, "size": size}


def test_pua_glyphs_map_to_moe_standard_characters():
    """手冊字型的私用區字 (𪜶/𬦰/𫞼/𫝏/𫝛) 愛換做 Unicode 標準字, 輸入法佮字典才揣會著."""
    assert bad.fix_pua("共\ue701醫治，\ue705山，\ue703佇，跤\uf5e9，相\ue35c") == "共𪜶醫治，𬦰山，𫞼佇，跤𫝏，相𫝛"


def test_unknown_pua_glyph_is_an_error_not_silently_kept():
    with pytest.raises(ValueError, match="U\\+E999"):
        bad.fix_pua("毋知\ue999")


def test_strip_annotations_removes_inline_romanization_and_its_trailing_space():
    raw = "逐年咱人(lán-lâng) 正月十五，毋通「閹雞趁鳳飛」(iam-ke thàn hong pue)，萬一"
    assert bad.strip_annotations(raw) == "逐年咱人正月十五，毋通「閹雞趁鳳飛」，萬一"


def test_strip_annotations_keeps_parentheses_that_are_not_romanization():
    raw = "馬偕牧師(Rev. George Leslie MacKay，1844～1901)，覆菜「pug` coi（四縣腔）」"
    assert bad.strip_annotations(raw) == raw


def test_annotations_pair_romanization_with_the_han_characters_before_it():
    """括號羅馬字是官方讀音: 音節數 = 前面連續漢字數 (跳過引號), 才算一組詞; at = 佇清本文的位置."""
    raw = "逐年咱人(lán-lâng) 正月，「閹雞趁鳳飛」(iam-ke thàn hong pue)，做下(hē) 願，Detroit(Tí-thù)"
    assert bad.strip_annotations(raw) == "逐年咱人正月，「閹雞趁鳳飛」，做下願，Detroit"
    assert bad.annotations(raw) == [
        {"han": "咱人", "tl": "lán-lâng", "at": 2},
        {"han": "閹雞趁鳳飛", "tl": "iam-ke thàn hong pue", "at": 8},
        {"han": "下", "tl": "hē", "at": 16},
    ]


def test_annotations_keep_light_tone_double_hyphen_as_one_word():
    assert bad.annotations("放(pàng) 過落落來(lak--loh-lâi)") == [
        {"han": "放", "tl": "pàng", "at": 0},
        {"han": "落落來", "tl": "lak--loh-lâi", "at": 2},
    ]


def test_annotations_reject_english_glosses_that_are_not_tl_syllables():
    """「愛丁堡(Edinburgh)」「米麵(rice noodle)」是英文夾註, 毋是讀音: 音節袂佇台羅音節表就毋算."""
    syllables = {"lan", "lang", "bi", "mi"}
    raw = "愛丁堡(Edinburgh)，米麵(rice noodle)，咱人(lán-lâng)"
    assert bad.annotations(raw, syllables) == [{"han": "咱人", "tl": "lán-lâng", "at": 7}]
    assert bad.strip_annotations(raw) == "愛丁堡，米麵，咱人"


def test_join_paragraphs_merges_blocks_cut_mid_sentence():
    """OpenTaigi 有時共續行當做新段 (標做 title): 無句尾標點的段愛佮後一段接做伙."""
    blocks = ["囡仔無教毋成人。」是講囡仔著", "愛教示。漚鹹菜。", "第二段。"]
    assert bad.join_paragraphs(blocks) == ["囡仔無教毋成人。」是講囡仔著愛教示。漚鹹菜。", "第二段。"]


def test_parse_side_notes_reads_vocab_grammar_and_source():
    lines = [
        _line("詞彙學習", role="body", size=11.34),
        _line("1.【咱人】lán-lâng：即農曆之意"),
        _line("2.【閹雞趁鳳飛】iam-ke thàn hong pue：不自量力地模仿別"),
        _line("人", role="body"),
        _line("文法學習", role="body", size=11.34),
        _line("【落落來】(lak--loh-lâi)：lak、loh都是「落」字的音讀，代表不"),
        _line("同的字義。", role="body"),
        _line("※本文出處：教育部電子報—閱讀越懂閩客語571期（2013-07-11）：平溪", size=9.92),
        _line("放天燈", role="body", size=9.92),
    ]
    notes = bad.parse_side_notes(lines)
    assert notes["vocab"] == [
        {"n": 1, "han": "咱人", "tl": "lán-lâng", "hoa": "即農曆之意"},
        {"n": 2, "han": "閹雞趁鳳飛", "tl": "iam-ke thàn hong pue", "hoa": "不自量力地模仿別人"},
    ]
    assert notes["grammar"] == [
        {"han": "落落來", "tl": "lak--loh-lâi", "text": "lak、loh都是「落」字的音讀，代表不同的字義。"}
    ]
    assert notes["source"] == {
        "text": "教育部電子報—閱讀越懂閩客語571期（2013-07-11）：平溪放天燈",
        "paper": "閱讀越懂閩客語",
        "issue": 571,
        "date": "2013-07-11",
        "title": "平溪放天燈",
    }


def test_source_without_date_still_parses():
    notes = bad.parse_side_notes([_line("※本文出處：教育部電子報—臺灣閩南語我嘛會133期：澎湖臺灣味")])
    assert notes["source"]["issue"] == 133 and notes["source"]["date"] is None
    assert notes["source"]["title"] == "澎湖臺灣味"


def test_audio_files_split_into_article_vocab_and_grammar():
    names = ["0401-06.mp3", "0401-07-01.mp3", "0401-07-02.mp3", "0401-07-A.mp3"]
    assert bad.split_audio(names) == {
        "article": "0401-06.mp3",
        "vocab": {1: "0401-07-01.mp3", 2: "0401-07-02.mp3"},
        "grammar": ["0401-07-A.mp3"],
    }


def test_upstream_star_filename_is_kept_for_download_but_dropped_locally():
    """上游有一个檔名 0402-21-01＊.mp3: 下載愛用原名, 網站檔名提掉 ＊."""
    audio = bad.split_audio(["0402-20.mp3", "0402-21-01＊.mp3"])
    assert audio["vocab"] == {1: "0402-21-01＊.mp3"}
    assert bad.local_name("0402-21-01＊.mp3") == "0402-21-01.mp3"


def _block(text, role="body"):
    return {"role": role, "text": text}


def test_body_continues_into_right_column_until_the_vocab_heading():
    """長文的尾段會續去右爿欄 (詞彙學習頭前), 作者黏佇段尾嘛愛拆出來."""
    left = [_block("鹿港八郊", "title"), _block("頭一段。"), _block("二十年前去參觀，是欲倒欲倒的古早厝，後來")]
    right = [
        _block("政府出大筆錢整修，真值得逐家好好仔參觀。作者：邱文錫"),
        _block("詞彙學習"),
        _block("1.【糖籠】thng-láng：裝糖的竹簍", "note"),
    ]
    body = bad.assemble_body(left, right)
    assert body["title"] == "鹿港八郊"
    assert body["author"] == "邱文錫"
    assert body["paragraphs"] == [
        "頭一段。",
        "二十年前去參觀，是欲倒欲倒的古早厝，後來政府出大筆錢整修，真值得逐家好好仔參觀。",
    ]


def test_spaced_author_label_and_footnote_are_not_body_text():
    left = [
        _block("王爺祭", "title"),
        _block("香火猶原佇咧。作 者：陳憲國"),
        _block("註　：現為新北市平溪區。", "note"),
    ]
    body = bad.assemble_body(left, [])
    assert body["paragraphs"] == ["香火猶原佇咧。"]
    assert body["author"] == "陳憲國"
    assert body["notes"] == ["現為新北市平溪區。"]


def test_vocab_without_romanization_and_combined_grammar_heads_parse():
    """山球的詞彙無台羅 (【Tee台】：…); 文法標題會是「【9月】與【9月初】」."""
    notes = bad.parse_side_notes(
        [
            _line("詞彙學習", role="body"),
            _line("1.【Tee台】：高爾夫發球台"),
            _line("文法學習", role="body"),
            _line("【9月】與【9月初】：閩南語有許多詞彙都需「輕讀」"),
        ]
    )
    assert notes["vocab"] == [{"n": 1, "han": "Tee台", "tl": "", "hoa": "高爾夫發球台"}]
    assert notes["grammar"] == [{"han": "9月與9月初", "tl": "", "text": "台語有許多詞彙都需「輕讀」"}]


def test_grammar_clips_spread_over_entries_and_extra_clips_stay_with_the_last():
    assert bad.grammar_audio(1, ["0401-55-A.mp3", "0401-55-B.mp3"]) == [["0401-55-A.mp3", "0401-55-B.mp3"]]
    assert bad.grammar_audio(2, ["x-A.mp3", "x-B.mp3"]) == [["x-A.mp3"], ["x-B.mp3"]]
    assert bad.grammar_audio(1, []) == [[]]


def test_grammar_head_without_colon_still_parses():
    """生查埔佮生查某: 「【啊……】閩南語中…」標題後無冒號."""
    notes = bad.parse_side_notes([_line("文法學習", role="body"), _line("【啊……】閩南語中會以ah來表示")])
    assert notes["grammar"] == [{"han": "啊……", "tl": "", "text": "台語中會以ah來表示"}]


def test_book_explanations_call_the_language_taigi_but_citations_stay_verbatim():
    """語言名統一叫「台語」: 文法說明、華語釋義改; 電子報刊名 (臺灣閩南語我嘛會) 是專名, 照原文."""
    notes = bad.parse_side_notes(
        [
            _line("詞彙學習", role="body"),
            _line("1.【久久久】kú-kú-kú：叫聲音近閩南語「久久久」"),
            _line("文法學習", role="body"),
            _line("【厚】kāu：閩南語的「厚」也表示常常"),
            _line("※本文出處：教育部電子報—臺灣閩南語我嘛會133期：澎湖臺灣味"),
        ]
    )
    assert notes["vocab"][0]["hoa"] == "叫聲音近台語「久久久」"
    assert notes["grammar"][0]["text"] == "台語的「厚」也表示常常"
    assert notes["source"]["paper"] == "臺灣閩南語我嘛會"


# ---- 產出的 docs/read/data/articles.json ----

ARTICLES_JSON = bad.OUT_JSON

# 照兩冊 PDF【目錄】點算 (每冊每分類幾篇).
TOC_COUNTS = {
    (1, "臺灣好𨑨迌"): 7,
    (1, "臺灣好食物"): 8,
    (1, "臺灣人情味"): 3,
    (1, "臺灣文史古"): 4,
    (1, "臺灣心適代"): 8,
    (2, "臺灣好𨑨迌"): 13,
    (2, "臺灣人情味"): 5,
    (2, "臺灣文史古"): 7,
    (2, "臺灣心適代"): 4,
}


def _articles():
    import json

    return json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))["articles"]


def test_every_toc_article_is_built_under_its_category():
    from collections import Counter

    assert Counter((a["book"], a["category"]) for a in _articles()) == TOC_COUNTS


def test_articles_are_complete_and_clean():
    """每篇有作者、出處期數、詞彙; 段落完整 (句尾標點收), 無私用區字、無漏入的欄位標題."""
    for art in _articles():
        assert art["author"] and art["source"]["issue"] > 0 and art["vocab"], art["id"]
        for para in art["paragraphs"]:
            assert para["text"].endswith(("。", "！", "？", "」", "』", "…")), (art["id"], para["text"][-10:])
            assert not bad.PUA_RE.search(para["raw"]), art["id"]
            assert "作者" not in para["text"] and "詞彙學習" not in para["text"], art["id"]
            for r in para["readings"]:
                assert para["text"][r["at"] : r["at"] + len(r["han"])] == r["han"], (art["id"], r)


def test_every_referenced_clip_is_shipped_and_nothing_else():
    clips = set()
    for art in _articles():
        clips.add(art["audio"])
        clips.update(v["audio"] for v in art["vocab"] if v["audio"])
        clips.update(c for g in art["grammar"] for c in g["audio"])
    shipped = {f"audio/{p.name}" for p in bad.OUT_AUDIO.glob("*.mp3")}
    assert clips == shipped
    assert all(v["audio"] is not None for a in _articles() for v in a["vocab"])
