"""parse_moe_articles: 《讀文章蓋趣味》官方讀音 → 字典源 TSV 把關。

來源是 committed docs/read/data/roman.json 的 o:1 (詞, 讀音) 組合
(冊手冊括號註明的官方讀音); 輕聲 `--` 愛保全做兩格空白
(build_lighttone_entries kip_to_rime_key 慣例), 毋是 supplement 的塌做一格。
冊內英文夾註 (Edinburgh/Austronesian/rice noodle) 會使騙過字母+調號的
形狀, 愛用主字典的音節表 (syllabary) 擋 — 英文毋是台語讀音。
"""

from __future__ import annotations

import json

from scripts.parse_moe_articles import main, official_to_rime_code

_SYLLABARY = {"lak", "loh", "lai", "lan", "lang", "tshang", "a", "it", "u", "tsit", "e", "peh", "tsng", "khit"}


def test_official_to_rime_code_keeps_lighttone_double_space():
    assert official_to_rime_code("lak4 --loh4 lai5", _SYLLABARY) == "lak4  loh4 lai5"
    assert official_to_rime_code("tshang1 --a2", _SYLLABARY) == "tshang1  a2"
    assert official_to_rime_code("lan2 lang5", _SYLLABARY) == "lan2 lang5"


def test_official_to_rime_code_rejects_non_tl():
    # 冊內括號英文 (murphy's law) 予 roman.json 提著作官方讀音: 愛拒收。
    assert official_to_rime_code("murphy's law1", _SYLLABARY) is None
    # 免調 token 字典禁止 (validate_dict fatal gate): 愛拒收。
    assert official_to_rime_code("ah", _SYLLABARY) is None
    assert official_to_rime_code("jit8 si0", _SYLLABARY) is None


def test_official_to_rime_code_rejects_english_via_syllabary():
    # 英文夾註形成 + 調號 (Edinburgh4/austronesian1/rice1-noodle1):
    # 字母+數字過得到形狀檢查, 愛靠 syllabary 擋。
    assert official_to_rime_code("edinburgh4", _SYLLABARY) is None
    assert official_to_rime_code("austronesian1", _SYLLABARY) is None
    assert official_to_rime_code("rice1 noodle1", _SYLLABARY) is None
    # syllabary 內底的音節 (調剝掉) 愛過。
    assert official_to_rime_code("peh4", _SYLLABARY) == "peh4"


def test_official_to_rime_code_without_syllabary_only_shape_checks():
    # 無 syllabary (檔案缺席) 退做形狀檢查: 英文溜過去, build_all 一定愛傳。
    assert official_to_rime_code("edinburgh4") == "edinburgh4"


def _roman_sample(tmp_path):
    roman = {
        "articles": {
            "0401-06": [
                {
                    "w": [
                        {"h": "咱人", "r": "lan2 lang5", "o": 1},
                        {"h": "落落來", "r": "lak4 --loh4 lai5", "o": 1},
                        {"h": "天燈", "r": "thinn1 ting1"},  # 非官方: 毋收入
                        {"h": "定律", "r": "murphy's law1", "o": 1},  # 解析失敗: skip
                        {"h": "咱人", "r": "lan2 lang5", "o": 1},  # 重複: dedup
                        {"h": "一个詞", "r": "it4 u7", "o": 1},  # 仝詞第二个官方讀音: 愛收
                        {"h": "一个詞", "r": "tsit8 e5", "o": 1},
                        {"h": "堡", "r": "edinburgh4", "o": 1},  # 英文夾註: syllabary 擋
                    ]
                }
            ]
        }
    }
    src = tmp_path / "roman.json"
    src.write_text(json.dumps(roman), encoding="utf-8")
    return src


def _syllabary_file(tmp_path):
    path = tmp_path / "dict.yaml"
    path.write_text(
        "# header\n...\n"
        "天燈\tthinn1 ting1\t600\n"
        "落--落--來\tlak4  loh4 lai5\t600\n"
        "咱人\tlan2 lang5\t600\n"
        "一个詞\tit4 u7\t600\n"
        "一个詞\ttsit8 e5\t600\n",
        encoding="utf-8",
    )
    return path


def test_main_writes_entries_tsv(tmp_path, capsys):
    src = _roman_sample(tmp_path)
    out = tmp_path / "entries.tsv"
    main(["--input", str(src), "--output", str(out), "--syllabary", str(_syllabary_file(tmp_path))])
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines == [
        "讀文章蓋趣味\t一个詞\tit4 u7",
        "讀文章蓋趣味\t一个詞\ttsit8 e5",
        "讀文章蓋趣味\t咱人\tlan2 lang5",
        "讀文章蓋趣味\t落落來\tlak4  loh4 lai5",
    ]
    stats = capsys.readouterr().out
    assert "4 entries" in stats
    assert "2 skipped" in stats  # murphy's law1 + edinburgh4
    assert "syllabary=Y" in stats
