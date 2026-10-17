"""《讀文章蓋趣味》文章語料 真 librime 驗收: 零「找不到」+ top-1 棘輪。

語料 = docs/read/data/roman.json 分詞 (w) 內底每一个有讀音的 (漢字詞, 讀音) 組合:
- 官方讀音 (o:1, 冊手冊括號註明的) 一詞一列, 拍伊的官方鍵就愛揣著伊;
- 非官方詞較寬容: 伊佇 docs/thak/data-public/dict.json 的任何一个讀音揣著就算
  (加發 artx_ 寬容列, 予引擎逐个讀音都試一擺)。

拍字鍵列照 sentence_corpus.tsv 慣例: 音節用 - 接; 輕聲音節的 -- 做連接
(README: 輕聲會當直接拍 --), 所以 "lak4 --loh4 lai5" 拍 "lak4--loh4-lai5"。

有非漢字/非羅馬字字符 (私用區、注音、標點) 抑 IME 字典無這个詞面的詞拍袂出來,
排除、納入報告, 免驗 (assignment: Words containing non-Han letters …)。

Requirement A: 逐个語料詞, 拍伊的鍵, 候選清單 (全部頁, 非 page 1 干焦) 內底
一定有字面仝款的上尾 (rime_smoke corpus 模式第 4 欄 allpages 掠全頁, cap 50 頁)。
Requirement B: 語料 top-1 命中率不得低於 tests/fixtures/article_baseline.json
(棘輪, sentence ratchet 仝款自舉; 基線干焦佇零「找不到」的日子起基)。
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import defaultdict

import pytest

from tests.test_real_rime import ROOT, _build_and_run, _find_runtime

pytestmark = pytest.mark.real_rime

ROMAN_JSON = ROOT / "docs" / "read" / "data" / "roman.json"
THAK_DICT_JSON = ROOT / "docs" / "thak" / "data-public" / "dict.json"
IME_DICT_YAML = ROOT / "schema" / "phah_taibun.dict.yaml"
ARTICLE_BASELINE_JSON = ROOT / "tests" / "fixtures" / "article_baseline.json"

# 一个音節 (的 e5、我 gua2 這種熱門讀音) 的候選可能幾百个, 50 頁是綽綽有餘的 sane cap。
MAX_PAGES = 50

# 已知例外 (使用者 2026-10-16 決定: 排除, 毋改字典)。30 个是轉換詞典 src="rime" 未驗證延伸層的
# 切詞碎片 (「是民」「甲的」…, 毋是詞); 啊若 ah-nā、矣 ah、九九 是 IME 字典欠的讀音。
KNOWN_MISSES = frozenset(
    [
        "九九",
        "做甲",
        "到欲",
        "化的",
        "啊若",
        "徙來",
        "房的",
        "挽的",
        "擔的",
        "是世",
        "是民",
        "是野",
        "有果",
        "有鬼",
        "民來",
        "無咧",
        "甲無",
        "甲的",
        "的便",
        "的刺",
        "的民",
        "聽甲",
        "聽的",
        "講甲",
        "賞的",
        "較有",
        "野鬼",
        "限的",
        "是好",
        "無共",
        "矣",
        "行的",
        "講欲",
    ]
)

# 讀音 token: 數字調音節, 輕聲前置 --。(官方讀音解析檢查用)
_SYLLABLE_RE = re.compile(r"(?:--)?[a-z]+[0-9]?")


def _typed_keys(reading: str) -> str:
    """讀音 (空白隔音節) → 拍字鍵列: 輕聲 -- 兼做連接, 其餘音節 - 接。"""
    parts: list[str] = []
    for token in reading.split(" "):
        if token.startswith("--") or not parts:
            parts.append(token)
        else:
            parts.append("-" + token)
    return "".join(parts)


def _word_is_typeable(word: str) -> bool:
    """詞面干焦有漢字抑羅馬字母 (Unicode 類別 L*) 才有可能拍得出來。"""
    return all(unicodedata.category(ch).startswith("L") for ch in word)


def _row_label(prefix: str, word: str, reading: str) -> str:
    """內容雜湊標籤: 語料成毋過 (新增文章) 舊標籤嘛袂變意思, 棘輪基線穩定。"""
    digest = hashlib.sha1(f"{word}\t{reading}".encode()).hexdigest()[:10]
    return f"{prefix}_{digest}"


def _reading_is_typeable(reading: str, syllabary: set[str] | None = None) -> bool:
    """讀音逐音節是 TL 拼式 (調可省、0 輕聲標記、-- 前綴) 才拍得出鍵列。

    syllabary = 主字典音節 stem 表: 冊內英文夾註 (Edinburgh4) 過得了
    形狀檢查, 愛靠音節表擋。
    """
    for token in reading.split(" "):
        match = _SYLLABLE_RE.fullmatch(token)
        if not match:
            return False
        if syllabary is not None and re.sub(r"[0-9]+$", "", token.removeprefix("--")) not in syllabary:
            return False
    return True


def _build_article_corpus(
    ime_texts: set[str], syllabary: set[str] | None = None
) -> tuple[list[dict], dict[str, list[str]]]:
    """roman.json 分詞 → 穩定排序的語料列 + 排除報告 (拍袂出來的詞/讀音)。"""
    roman = json.loads(ROMAN_JSON.read_text(encoding="utf-8"))
    thak = json.loads(THAK_DICT_JSON.read_text(encoding="utf-8"))

    pairs: dict[tuple[str, str], bool] = {}  # (詞, 讀音) → 有官方讀音?
    for paragraphs in roman["articles"].values():
        for para in paragraphs:
            for w in para["w"]:
                reading = w.get("r")
                if not reading:
                    continue  # miss:1: 轉換詞典欠這个詞的讀音, 無鍵好拍
                key = (w["h"], reading)
                pairs[key] = pairs.get(key, False) or bool(w.get("o"))

    rows: list[dict] = []
    for word, reading in sorted(pairs):
        official = pairs[(word, reading)]
        rows.append(
            {
                "label": _row_label("art" if official else "art2", word, reading),
                "word": word,
                "reading": reading,
                "keys": _typed_keys(reading),
                "official": official,
                "extra": False,
            }
        )
    official_words = {word for word, reading in pairs if pairs[(word, reading)]}

    # 非官方詞寬容: 詞佇 dict.json 的逐个讀音攏加發一列 (Requirement A 任一讀音算找著)。
    for word in sorted(w for (w, _) in pairs if w not in official_words):
        for reading in thak.get(word, {}).get("r", []):
            if (word, reading) in pairs:
                continue
            rows.append(
                {
                    "label": _row_label("artx", word, reading),
                    "word": word,
                    "reading": reading,
                    "keys": _typed_keys(reading),
                    "official": False,
                    "extra": True,
                }
            )

    # 讀音解析失敗 (親像冊內括號英文 "murphy's law1"/"edinburgh4" 予
    # officialNumeric 提著): 毋是 TL 拼式, 拍袂出鍵列 — 排除、報告,
    # 予讀音管線的 owner 追。
    artifacts = sorted(f"{word}\t{reading}" for word, reading in pairs if not _reading_is_typeable(reading, syllabary))
    rows = [row for row in rows if _reading_is_typeable(row["reading"], syllabary)]

    # 拍袂出來的詞面 (非漢字/羅馬字符閣 IME 字典無詞面): 排除、報告。
    excluded = sorted({word for (word, _) in pairs if not _word_is_typeable(word) and word not in ime_texts})
    known = sorted({word for (word, _) in pairs if word in KNOWN_MISSES})
    rows = [row for row in rows if row["word"] not in set(excluded) | KNOWN_MISSES]
    return rows, {"parse": artifacts, "nonhan": excluded, "known": known}


@pytest.fixture(scope="session")
def ime_dict_entries() -> tuple[set[str], set[tuple[str, str]]]:
    """主字典的 (詞面) 與 (詞面, 讀音碼) 集 — 缺啥物分類用。"""
    texts: set[str] = set()
    code_pairs: set[tuple[str, str]] = set()
    in_header = True
    for line in IME_DICT_YAML.read_text(encoding="utf-8").splitlines():
        if in_header:
            if line.startswith("..."):
                in_header = False
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            texts.add(parts[0])
            code_pairs.add((parts[0], parts[1]))
    return texts, code_pairs


@pytest.fixture(scope="session")
def article_corpus(ime_dict_entries) -> tuple[list[dict], dict[str, list[str]]]:
    texts, code_pairs = ime_dict_entries
    syllabary = {
        re.sub(r"[0-9]+$", "", token.removeprefix("--")) for text, code in code_pairs for token in code.split()
    }
    return _build_article_corpus(texts, syllabary)


@pytest.fixture(scope="session")
def real_rime_articles(tmp_path_factory, article_corpus):
    """共語料寫做 TSV (第 4 欄 allpages = 掠全頁候選), 一个部署行到尾。"""
    rows, _ = article_corpus
    tsv = tmp_path_factory.mktemp("article-corpus") / "article_corpus.tsv"
    lines = [f"{row['label']}\t{row['word']}\t{row['keys']}\tallpages" for row in rows]
    tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return _build_and_run(_find_runtime(), tmp_path_factory, smoke_args=(str(tsv),))


def _paged_candidate_texts(states: dict[str, dict], label: str) -> list[str]:
    """一列的全部候選字面: page 1 + 續頁 (#p2..), NFC 正規化 (librime 出 NFD)。"""
    texts = [c["text"] for c in states.get(label, {}).get("candidates", [])]
    for page in range(2, MAX_PAGES + 1):
        state = states.get(f"{label}#p{page}")
        if state is None:
            break
        texts.extend(c["text"] for c in state["candidates"])
    return [unicodedata.normalize("NFC", text) for text in texts]


def _flattened_rank(states: dict[str, dict], label: str, word: str) -> int:
    """字面佇全頁候選的位 (1 起算); 0 = 全頁攏無。"""
    texts = _paged_candidate_texts(states, label)
    return texts.index(word) + 1 if word in texts else 0


def _classify_miss(row: dict, ime_texts: set[str], ime_pairs: set[tuple[str, str]]) -> str:
    """找不到的分類: 官方讀音解析 / 詞無佇字典 / 讀音無佇字典 / 猶原揣無。"""
    if not all(_SYLLABLE_RE.fullmatch(token) for token in row["reading"].split(" ")):
        return "官方讀音解析(音節格式)"
    if row["word"] not in ime_texts:
        return "詞無佇IME字典"
    # 字典輕聲碼用兩格空白 ("lak4  loh4 lai5"), 讀音用 -- ("lak4 --loh4 lai5"): 正規化再比。
    flat = " ".join(row["reading"].replace("--", " ").split())
    if not any(t == row["word"] and " ".join(k.split()) == flat for t, k in ime_pairs):
        return "讀音無佇IME字典"
    return "詞佇讀音嘛有猶原揣無(部署/權重)"


def test_article_corpus_builder_shapes(article_corpus):
    """語料產生器把關 (免部署, 愛先擋: 語料破病就免浪費 15 分鐘部署)。"""
    rows, report = article_corpus
    primary = [row for row in rows if not row["extra"]]
    official = [row for row in rows if row["official"]]
    assert len(primary) >= 5000, f"語料傷少: {len(primary)}"
    assert len(official) >= 700, f"官方讀音列傷少: {len(official)}"
    for row in rows:
        assert row["keys"] and "---" not in row["keys"], row
        assert _reading_is_typeable(row["reading"]), row
    print(
        f"article corpus: {len(primary)} 語料列 (官方 {len(official)}), "
        f"寬容列 {len(rows) - len(primary)}, "
        f"排除 nonhan {len(report['nonhan'])} {report['nonhan'][:10]}, "
        f"解析 {len(report['parse'])} {report['parse'][:10]}"
    )


def test_article_corpus_zero_not_found(real_rime_articles, article_corpus, ime_dict_entries):
    """Requirement A: 逐个語料詞拍伊的鍵, 全頁候選內底一定有仝字面的詞。

    官方詞: 官方讀音列逐列愛中。非官方詞: 任何一列 (roman.json 抑 dict.json
    讀音) 中就算。找不到 → 分類 (解析/詞無/讀音無/其他) 徛證據補資料。
    """
    states = real_rime_articles
    rows, report = article_corpus
    ime_texts, ime_pairs = ime_dict_entries

    misses = [
        (word, row["keys"], _classify_miss(row, ime_texts, ime_pairs)) for word, row in _word_misses(states, rows)
    ]

    print(
        f"Requirement A: {len({row['word'] for row in rows})} 詞 / {len(rows)} 列, 找不到 {len(misses)}, "
        f"排除 nonhan {len(report['nonhan'])} + 解析 {len(report['parse'])} (免驗)"
    )
    if misses:
        by_class: dict[str, int] = defaultdict(int)
        for _, _, reason in misses:
            by_class[reason] += 1
        print("分類:", dict(by_class))
        for word, keys, reason in misses:
            print(f"  MISS\t{word}\t{keys}\t{reason}")
    assert not misses, f"零「找不到」未達: {len(misses)} 詞拍袂著 (分類佇頂懋輸出); 頭 10: {misses[:10]}"


def _word_misses(states: dict, rows: list[dict]) -> list[tuple[str, dict]]:
    """Requirement A 判定: 官方詞逐官方讀音列愛中; 非官方詞任何一列中就算。回 (詞, 無中的必要列)。"""
    by_word: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_word[row["word"]].append(row)
    misses: list[tuple[str, dict]] = []
    for word in sorted(by_word):
        official_rows = [row for row in by_word[word] if row["official"]]
        required = official_rows or by_word[word]
        ranks = [_flattened_rank(states, row["label"], word) for row in required]
        ok = all(rank > 0 for rank in ranks) if official_rows else any(rank > 0 for rank in ranks)
        if not ok:
            misses.extend((word, row) for row, rank in zip(required, ranks, strict=True) if rank == 0)
    return misses


def _top1_rate(rows: dict[str, dict]) -> float:
    return sum(1 for row in rows.values() if row["rank"] == 1) / len(rows)


def test_article_corpus_first_candidate_ratchet(real_rime_articles, article_corpus):
    """Requirement B 棘輪: 逐詞首選命中率 (每詞佇文章的讀音列, 無算 dict.json 別讀音列) 不得低於基線。

    sentence ratchet 仝款自舉: 基線檔缺席就共這擺的逐列 rank 寫入基線。
    起基有條件: 這擺 Requirement A 零「找不到」才寫 (非官方詞的別讀音列無中無要緊)
    — 免共一个猶佇補字典的起步率釘死 (欲重新起基: 刪 tests/fixtures/article_baseline.json)。
    """
    states = real_rime_articles
    rows, _ = article_corpus
    results: dict[str, dict] = {}
    for row in rows:
        if not row["extra"]:
            results[row["label"]] = {"rank": _flattened_rank(states, row["label"], row["word"])}
    not_found = len(_word_misses(states, rows))

    if ARTICLE_BASELINE_JSON.exists():
        baseline = json.loads(ARTICLE_BASELINE_JSON.read_text(encoding="utf-8"))
        missing = set(baseline) - set(results)
        assert not missing, f"corpus rows disappeared: {sorted(missing)[:10]}"
        base_rate = _top1_rate(baseline)
        assert _top1_rate(results) >= base_rate, (
            f"top-1 rate regressed: {_top1_rate(results):.4f} < baseline {base_rate:.4f}"
        )
    elif not_found == 0:
        ARTICLE_BASELINE_JSON.write_text(
            json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        pytest.fail(
            f"not-found {not_found}/{len(rows)}, top-1 rate {_top1_rate(results):.4f} — "
            "基線干焦佇零「找不到」的日子起基, 這擺無寫 article_baseline.json"
        )
