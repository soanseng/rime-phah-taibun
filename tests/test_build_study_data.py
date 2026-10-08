"""檢定練習資料 (docs/study/data/iongji.json): 推薦用字 700 的異用字 → 用字選擇題佮寫作檢查。"""

from scripts.build_study_data import build_iongji


def row(word, tl, alts, examples="", hoa="", also=""):
    return {"建議用字": word, "音讀": tl, "又音": also, "對應華語": hoa, "用例": examples, "異用字": alts}


LEKU = {
    "001": {"例句漢字": "我袂曉講英語。", "例句臺羅": "Guá bē-hiáu kóng Ing-gí."},
    "002": {"例句漢字": "伊欲去台北。", "例句臺羅": "I beh khì Tâi-pak."},
}


def test_item_keeps_word_reading_alternates_and_examples_that_contain_the_word():
    items = build_iongji([row("袂", "bē", "𣍐", "袂食袂睏、袂行、毋知", "不、不會")], LEKU)
    assert items == [
        {
            "word": "袂",
            "tl": "bē",
            "hoa": "不、不會",
            "alts": ["𣍐"],
            "recAlts": [],
            "examples": ["袂食袂睏", "袂行"],
            "sentences": [["我袂曉講英語。", "Guá bē-hiáu kóng Ing-gí."]],
        }
    ]


def test_rows_without_alternates_or_with_optional_parts_are_not_questions():
    items = build_iongji(
        [
            row("阿", "a", "", "阿母"),
            row("尾蝶(仔)/(尾)蝶仔", "bué-ia̍h(-á)", "尾蛾(仔)", "掠尾蝶仔"),
            row("欲", "beh", "要、卜、(欲)", "欲食飯"),
        ],
        LEKU,
    )
    assert [i["word"] for i in items] == ["欲"]
    assert items[0]["alts"] == ["要", "卜"]


def test_alternate_that_is_itself_a_recommended_word_is_marked_so_checkers_do_not_flag_it():
    # 「密」是「峇」的異用字, 毋過「密 ba̍t」本身嘛是推薦用字——寫作檢查袂當共「密」當錯字
    items = build_iongji([row("峇", "bā", "密", "門關無峇"), row("密", "ba̍t", "", "密密")], LEKU)
    assert items[0]["alts"] == ["密"] and items[0]["recAlts"] == ["密"]


def test_sentence_whose_romanization_does_not_line_up_with_its_hanji_is_dropped():
    # 900 例句原始檔有一寡斷去的臺羅 (頭字母無去、換行吞字); 對袂齊的句毋通做題目
    leku = {
        "1": {"例句漢字": "𪜶阿珠仔會當來上班。", "例句臺羅": "In -tsu--á ē-tàng lâi siōng- an."},
        "2": {"例句漢字": "我會當去。", "例句臺羅": "Guá ē-tàng khì."},
    }
    items = build_iongji([row("會當", "ē-tàng", "會凍", "")], leku)
    assert items[0]["sentences"] == [["我會當去。", "Guá ē-tàng khì."]]


def test_variant_reading_keeps_only_the_first_and_question_needs_some_context():
    items = build_iongji([row("覕", "bih/phih", "匿", ""), row("某", "bóo", "姥", "翁仔某")], LEKU)
    assert [(i["word"], i["tl"]) for i in items] == [("某", "bóo")]
