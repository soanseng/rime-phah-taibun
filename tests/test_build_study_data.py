"""檢定練習資料 (docs/study/data/iongji.json): 推薦用字 700 的異用字 → 用字選擇題佮寫作檢查。"""

from scripts.build_study_data import build_iongji, build_yongji


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


def lkk(form, moe="", tl="", hoa="", examples=""):
    return {"建議用字": form, "音讀": tl, "教育部推薦漢字": moe, "對應華語": hoa, "用例": examples}


def test_yongji_classifies_each_700_word_by_how_lkk_writes_it():
    # LKK 建議 a̍h (羅馬字) 對應教育部「曷」; 「阿妗」LKK 照寫漢字; 「紅記記」LKK 寫做漢羅混
    moe = [row("曷", "a̍h", ""), row("阿妗", "a-kīm", ""), row("紅記記", "âng-kì-kì", "")]
    rows = [lkk("a̍h", moe="曷"), lkk("阿妗", tl="a-kīm"), lkk("紅kì-kì", moe="紅記記")]
    items = {i["word"]: i for i in build_yongji(moe, rows)}
    assert items["曷"]["lkk"] == [{"form": "a̍h", "kind": "lo"}]
    assert items["阿妗"]["lkk"] == [{"form": "阿妗", "kind": "han"}]
    assert items["紅記記"]["lkk"] == [{"form": "紅kì-kì", "kind": "mix"}]


def test_yongji_homographs_take_only_the_lkk_form_with_the_same_reading():
    # 700 有兩个「漚」(au 浸泡、àu 爛); LKK 兩个讀音攏寫羅馬字。逐个讀音干焦提家己彼个寫法,
    # 調符位置寫法無仝 (ngeh̍ / nge̍h) 嘛算仝音; LKK 無收的讀音 (落 lo̍h) 毋通借別个讀音的寫法
    moe = [
        row("漚", "au", ""),
        row("漚", "àu", ""),
        row("挾", "ngeh̍", ""),
        row("落", "lak", ""),
        row("落", "lo̍h", ""),
        row("家婆", "ke-pô", ""),
    ]
    rows = [
        lkk("au", moe="漚"),
        lkk("àu", moe="漚"),
        lkk("au", moe="漚"),
        lkk("gia̍p", moe="挾"),
        lkk("nge̍h", moe="挾"),
        lkk("lak", moe="落"),
    ]
    items = [(i["word"], i["tl"], [f["form"] for f in i["lkk"]]) for i in build_yongji(moe, rows)]
    assert items == [
        ("漚", "au", ["au"]),
        ("漚", "àu", ["àu"]),
        ("挾", "ngeh̍", ["nge̍h"]),
        ("落", "lak", ["lak"]),
        ("落", "lo̍h", []),
        ("家婆", "ke-pô", []),
    ]


def test_yongji_han_entries_match_despite_accent_and_self_mapping():
    # LKK「家己 ka-kī」對 700「家己 ka-tī」: 腔口無仝, 寫法仝款; 「囡仔」LKK 教育部欄寫家己本身;
    # 700 讀音用無點 i (U+0131) 嘛愛對會著 LKK 的 ji̍t 羅馬字寫法
    moe = [row("家己", "ka-tī", ""), row("囡仔", "gín-á", ""), row("日", "j\u0131\u030dt", "")]
    rows = [lkk("家己", tl="ka-kī"), lkk("囡仔", moe="囡仔", tl="gín-á"), lkk("ji̍t", moe="日")]
    items = [(i["word"], [f["form"] for f in i["lkk"]]) for i in build_yongji(moe, rows)]
    assert items == [("家己", ["家己"]), ("囡仔", ["囡仔"]), ("日", ["ji̍t"])]


def test_yongji_single_reading_word_takes_lkk_form_even_if_tones_differ_and_shifted_rows():
    # 700「連鞭 liâm-mi」干焦一个讀音; LKK 寫 liam-mi (無調符) 嘛是伊。
    # LKK 表「家婆」彼列欄位錯位 (建議用字 ke-pô、音讀欄是 家婆), 嘛愛對會著
    moe = [row("連鞭", "liâm-mi", ""), row("家婆", "ke-pô", "")]
    rows = [lkk("liam-mi", moe="連鞭"), lkk("ke-pô", tl="家婆")]
    items = [(i["word"], [f["form"] for f in i["lkk"]]) for i in build_yongji(moe, rows)]
    assert items == [("連鞭", ["liam-mi"]), ("家婆", ["ke-pô"])]


def test_yongji_does_not_borrow_an_lkk_spelling_with_another_reading():
    # 700 干焦一个讀音, 毋過 LKK 羅馬字寫法去調了嘛對袂著 → 無證據, 毋收
    moe = [row("遮", "jia", "")]
    rows = [lkk("tsia", moe="遮"), lkk("tsiah", moe="遮")]
    assert build_yongji(moe, rows)[0]["lkk"] == []
    # LKK 表本身有「遮 jia」照寫漢字彼列 (遮雨、遮日): 彼才是 jia 的寫法
    rows.append(lkk("遮", tl="jia"))
    assert build_yongji(moe, rows)[0]["lkk"] == [{"form": "遮", "kind": "han"}]
