"""拼音發音教學資料建置 - 教育部《學拼音有撇步》=> docs/pronounce/data/lessons.json.

來源: 教育部「咱來學臺灣台語」本土語文系列 0101-01《學拼音有撇步》(refs/moe-jts-01-pinyin.pdf,
無 commit: 教育部語文成果網「版權所有」, 揣無再散布授權; 無佇本機就對官方下載)
佮手冊內藍字連結的官方音檔. 音檔無轉存, 網頁直接對官方 https 網址播放; 建置時逐个 HEAD 檢查.
課文照手冊章節轉錄 (發音說明照原文, 發音提示用家己的話重寫).

音節表 (附錄一 韻母) 的有調拼法: 文字對 pdftotext 讀; 第 8 調的「̍」佇 PDF 是畫的細直線
(無文字), 用連結框內底的細 rect 判斷 (tests 用畫面看會著的例驗證).

    uv run --with pdfplumber python scripts/build_pronounce_data.py
"""

# ruff: noqa: RUF001, RUF003 - 課文是台文/華文原文, 全形標點照手冊

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from tl_poj_convert import tl_to_poj  # noqa: E402

PDF = REPO_ROOT / "refs" / "moe-jts-01-pinyin.pdf"
PDF_URL = "https://language.moe.gov.tw/upload/download/jts/01%E6%8B%BC%E9%9F%B3.pdf"
AUDIO_BASE = "https://language.moe.gov.tw/upload/download/jts/01%E6%8B%BC%E9%9F%B3(%E9%9F%B3%E6%AA%94)/"
OUT_JSON = REPO_ROOT / "docs" / "pronounce" / "data" / "lessons.json"
USER_AGENT = "rime-phah-taibun-build/1.0 (https://taigi.anatomind.com)"

SOURCE = {
    "title": "咱來學臺灣台語：學拼音有撇步（本土語文系列 0101-01）",
    "publisher": "教育部",
    "pdf": PDF_URL,
    "note": "課文照手冊原文引用，音檔直接對教育部官方網址播放，無轉存；著作權屬教育部。",
    "tailo": "https://tailo.moe.edu.tw/",
}

INITIALS = ["p", "ph", "m", "b", "t", "th", "n", "l", "k", "kh", "h", "ng", "g", "ts", "tsh", "s", "j"]
TONE8 = "\u030d"


def a(name: str) -> str:
    return f"0101-{name}.mp3"


def strip_tone(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


def put_mark(syl: str, mark: str) -> str:
    """TL 標調位置: a > oo > e,o > i,u (iu/ui 標後一个); 無元音標 m/n."""
    low = syl
    if "a" in low:
        i = low.index("a")
    elif "oo" in low:
        i = low.index("oo")
    elif "e" in low:
        i = low.index("e")
    elif "o" in low:
        i = low.index("o")
    elif "iu" in low:
        i = low.index("iu") + 1
    elif "ui" in low:
        i = low.index("ui") + 1
    elif "i" in low:
        i = low.index("i")
    elif "u" in low:
        i = low.index("u")
    else:
        i = syl.index("m") if "m" in syl else syl.index("n")  # 聲化韻 hm̍h、n̍gh: 標佇 m／n
    return unicodedata.normalize("NFC", syl[: i + 1] + mark + syl[i + 1 :])


def split_initial(syl: str) -> tuple[str, str]:
    for ini in sorted(INITIALS, key=len, reverse=True):
        if syl.startswith(ini) and len(syl) > len(ini):
            rest = syl[len(ini) :]
            if ini == "ng" and rest in ("h",):  # ngh 是韻母
                continue
            return ini, rest
    return "", syl


def ex(text: str, prefix: str, mark8: dict[str, str] | None = None) -> list[dict]:
    """「tsai 知、tshai 猜」=> 例字 (無音檔, 音檔是規列一个)."""
    out = []
    for part in text.split("、"):
        bits = part.split()
        tl = bits[0]
        out.append({"tl": tl, "han": bits[1] if len(bits) > 1 else ""})
    return out


# ---------------------------------------------------------------- 課文 (照手冊)

VOWELS = [
    ("a", "04-01", "口張開較大，舌面下降，舌尖自然微離開下齒。", "類似「ㄚ」", "類似〔a〕"),
    ("i", "04-02", "雙脣扁平微開，上下齒也稍微分開，嘴角往後拉，呼出聲音。", "類似「ㄧ」", "類似〔i〕"),
    ("u", "04-03", "雙脣縮合成圓形，舌後抵近軟顎，舌尖不接觸下齒，聲音從合脣的小孔中呼出。", "類似「ㄨ」", "類似〔u〕"),
    ("e", "04-04", "脣扁平，舌前部介於半升半降之間，自然發音。", "類似「ㄝ」", "類似〔e〕"),
    ("o", "04-05", "嘴脣半開似橢圓形。舌面平放，不用力，不捲舌，使聲音自然呼出。", "類似「ㄜ」", "類似〔ə〕"),
    ("oo", "04-06", "嘴脣成圓形，舌葉後縮，舌後升起，舌面介於半升半降之間。", "類似「ㄛ」", "類似〔ɔ〕"),
]

DIPHTHONGS = [
    ("ai", "tsai 知、tshai 猜、sai 獅"),
    ("au", "pau 包、kau 交、thau 偷"),
    ("ia", "tsia 遮、tshia 車、hia 遐"),
    ("iu", "liu 溜、tsiu 周、tshiu 秋"),
    ("io", "io 腰、tsio 招、sio 燒"),
    ("iau", "piau 標、kiau 嬌、siau 消"),
    ("ua", "thua 拖、kua 歌、sua 沙"),
    ("ui", "tui 堆、thui 梯、sui 雖"),
    ("ue", "pue 飛、phue 批、kue 瓜"),
    ("uai", "kuai 乖、uai 歪"),
]

NASALIZED = [
    ("ann", "tann 擔、thann 他、sann 三"),
    ("inn", "phinn 篇、tinn 甜、thinn 天"),
    ("enn", "penn 繃、tsenn 爭、tshenn 星"),
    ("onn", "honn 齁、honn 呼、onn 嗚"),
    ("ainn", "kainn 喈、khainn 掮、hainn 哼"),
    ("iann", "phiann 骿、thiann 聽、siann 聲"),
    ("iunn", "tiunn 張、siunn 箱、kiunn 薑"),
    ("iaunn", "iaunn 喓"),
    ("uann", "puann 搬、kuann 肝、suann 山"),
    ("uainn", "kuainn 關"),
]

SYLLABIC = [
    ("m", "08-11-B", "ḿ 姆、m 莓、m 毋、hm 茅"),
    ("ng", "08-12-B", "png 方、kng 光、thng 湯、sng 酸"),
]

NASAL_FINALS = [
    ("am", "kam 甘、kham 堪、sam 三"),
    ("an", "pan 班、kan 奸、san 山"),
    ("ang", "pang 幫、tang 當、sang 鬆"),
    ("im", "kim 金、khim 欽、sim 心"),
    ("in", "pin 賓、tin 津、sin 身"),
    ("ing", "ling 奶、ting 丁、sing 生"),
    ("iam", "tiam 砧、thiam 添、liam 拈"),
    ("ian", "phian 偏、kian 堅、sian 仙"),
    ("iang", "liang 喨、tsiang 漳、siang 雙"),
    ("iong", "tiong 中、tsiong 將、siong 傷"),
    ("un", "un 溫、pun 分、kun 君"),
    ("uan", "tuan 端、suan 宣、tsuan 專"),
    ("uang", "uang 嚾"),
    ("om", "som 參、om 掩"),
    ("ong", "bong 摸、thong 通、song 桑"),
]

CHECKED_10 = [
    ("ap", "tap 答、tshap 插、ap 壓"),
    ("at", "pat 八、tshat 擦、at 遏"),
    ("ak", "pak 北、tak 觸、ak 沃"),
    ("ah", "pah 百、lah 啦、ah 鴨"),
    ("ip", "kip 急、khip 吸、hip 翕"),
    ("it", "tshit 七、sit 失、tit 得"),
    ("ik", "pik 逼、tik 德、sik 色"),
    ("ih", "bih 覕、thih 鐵、tih 滴"),
    ("ut", "tsut 卒、tshut 出、kut 骨"),
    ("uh", "tuh 盹、tshuh 焠、suh 欶"),
    ("eh", "peh、beh 欲、leh 咧"),
    ("oh", "phoh 粕、toh 桌、koh 閣"),
    ("ok", "kok 國、sok 速、hok 福"),
    ("ooh", "mooh、ooh 喔"),
    ("aih", "haih 唉、aih 噯、aih 哎"),
    ("auh", "kauh、mauh 卯、nauh 喃"),
    ("iuh", "tiuh 搐、tsiuh 喌"),
    ("ueh", "kueh 郭、hueh 血、sueh 說"),
]

CHECKED_11 = [  # 01-10: B=韻母 C=例; 11-17: A=韻母 B=例
    ("iap", "thiap 貼、giap 鋏、liap 攝"),
    ("iat", "phiat 撇、kiat 吉、siat 設"),
    ("iak", "piak 煏、siak 摔、siak 鑠"),
    ("iah", "iah 搤、phiah 僻、thiah 拆"),
    ("iok", "kiok 菊、siok 淑、jiok 逐"),
    ("ioh", "hioh 歇、sioh 惜、ioh 臆"),
    ("iauh", "hiauh 藃"),
    ("uat", "thuat 脫、kuat 決、suat 雪"),
    ("uah", "buah 抹、kuah 割、suah 煞"),
    ("uaih", "uaih"),
    ("mh", "hmh 噷"),
    ("ngh", "phngh 嗙、khngh 吭、hngh 哼"),
    ("annh", "hannh 唅、sannh 啥"),
    ("aunnh", "haunnh 澩"),
    ("iannh", "hiannh 嚇"),
    ("ennh", "khennh 喀"),
    ("onnh", "honnh 乎"),
]

# 聲母: 手冊聲母篇 (發音部位、方法、華語注音、英語音標照原文)
INITIAL_INFO = {
    "p": ("雙脣", "不送氣、清音、塞音", "類似「ㄅ」", "與英語 sport 的 p 發音相同"),
    "ph": ("雙脣", "送氣、清音、塞音", "類似「ㄆ」", "與英語 pie 的 p 發音相同"),
    "m": ("雙脣", "濁音、鼻音", "類似「ㄇ」", "類似〔m〕"),
    "b": ("雙脣", "濁音、塞音", "", "類似〔b〕"),
    "t": ("舌尖＋上齒齦", "不送氣、清音、塞音", "類似「ㄉ」", "與英語 stone 的 t 發音相同"),
    "th": ("舌尖＋上齒齦", "送氣、清音、塞音", "類似「ㄊ」", "與英語 tone 的 t 發音相同"),
    "n": ("舌尖＋上齒齦", "濁音、鼻音", "類似「ㄋ」", "類似〔n〕"),
    "l": ("舌尖＋上齒齦後端", "濁音、塞音", "類似「ㄌ」", "類似〔l〕"),
    "k": ("舌根＋軟顎", "不送氣、清音、塞音", "類似「ㄍ」", "與英語 sky 的 k 發音相同"),
    "kh": ("舌根＋軟顎", "送氣、清音、塞音", "類似「ㄎ」", "與英語 key 的 k 發音相同"),
    "h": ("聲門", "清音、擦音", "", "類似〔h〕"),
    "ng": ("舌根＋軟顎", "濁音、鼻音", "", ""),
    "g": ("舌根＋軟顎", "濁音、塞音", "", "類似〔g〕"),
    "ts": ("舌尖＋上齒齦", "不送氣、清音、塞擦音", "類似「ㄗ」", ""),
    "tsh": ("舌尖＋上齒齦", "送氣、清音、塞擦音", "類似「ㄘ」", ""),
    "s": ("舌尖＋上齒齦", "清音、擦音", "類似「ㄙ」", "類似〔s〕"),
    "j": ("舌尖＋上齒齦", "濁音、塞擦音", "", ""),
}
PLACE_KEY = {
    "雙脣": "lips",
    "舌尖＋上齒齦": "alveolar",
    "舌尖＋上齒齦後端": "alveolar",
    "舌根＋軟顎": "velar",
    "聲門": "glottis",
}

# 附錄一 聲母拼音練習 (第 8 調「̍」照畫面補, PDF 文字層無)
INITIAL_WORDS = {
    "23": [
        (
            "p",
            "pî-pê 琵琶|pó-puè 寶貝|pài-pài 拜拜|pâi-pan 排班|puànn-poo 半晡|pan-pòo 頒布|píng-pak 反腹|pak-pîng 北爿|pah-puann 百般",  # noqa: E501
        ),
        (
            "ph",
            "phú-phú 殕殕|phue-phîng 批評|phiau-phiat 飄撇|phun-pho 奔波|phīnn-phang 鼻芳|phian-phiah 偏僻|phòng-phā 膨疱|phong-phài 豐沛|phah-pháinn 拍歹",  # noqa: E501
        ),
        (
            "m",
            "má-mah 媽媽|má-siōng 馬上|mî-á 棉仔|mī-hún 麵粉|môo-pit 毛筆|moo-hui 摸飛|miâ-tuann 名單|muá-ì 滿意|muâ-iû 麻油",  # noqa: E501
        ),
        (
            "b",
            "bí-buán 美滿|bia̍t-bông 滅亡|bán-bīn 挽面|bān-bu̍t 萬物|bān-bān 慢慢|bîn-bāng 眠夢|bûn-bîng 文明|būn-būn 悶悶|bông-bū 雺霧",  # noqa: E501
        ),
    ],
    "24": [
        (
            "t",
            "tē-tiám 地點|ti-tu 蜘蛛|tàu-té 到底|tiū-tiânn 稻埕|tiau-tî 刁持|tng-té 長短|tan-to̍k 單獨|tan-tiân 丹田|tian-tò 顛倒",  # noqa: E501
        ),
        (
            "th",
            "thé-thiap 體貼|thó-thàn 討趁|thôo-thuànn 塗炭|thau-the̍h 偷提|thàu-thinn 透天|thâu-the 頭胎|thuî-thuî 槌槌|thiànn-thàng 疼痛|thih-tháng 鐵桶",  # noqa: E501
        ),
        (
            "n",
            "nuā-nuā 爛爛|nê-sann 晾衫|nóo-huà 老化|nāi-iōng 耐用|nāi-hô 奈何|niá-tsînn 領錢|niū-pōo 讓步|niau-á 貓仔|nńg-sim 軟心",  # noqa: E501
        ),
        (
            "l",
            "lâ-lí 鯪鯉|lô-li̍k 勞力|lōo-lê 露螺|lāi-lí 內裡|lāu-lâng 老人|liû-lōng 流浪|lûn-liû 輪流|lông-lîm 農林|li̍k-liōng 力量",  # noqa: E501
        ),
    ],
    "25": [
        (
            "k",
            "ki-kim 基金|kî-kuài 奇怪|ke-kuè 雞髻|kai-kip 階級|kāu-kang 厚工|kuân-kē 懸低|kīng-ki 競技|kiông-khuân 強權|kiat-kó 結果",  # noqa: E501
        ),
        (
            "kh",
            "khi-khiau 蹊蹺|khe-kháu 溪口|khòo-kha 褲跤|khai-khún 開墾|khuì-kháu 氣口|khám-khiat 坎坷|khong-khì 空氣|khuànn-kìnn 看見|kheh-khì 客氣",  # noqa: E501
        ),
        (
            "h",
            "hi-hua 虛華|hô-hâi 和諧|hô-hóng 何況|hue-hng 花園|hue-hún 花粉|hng-hng 遠遠|hīng-hok 幸福|ha̍p-huat 合法|ha̍k-hāu 學校",  # noqa: E501
        ),
        (
            "g",
            "gí-giân 語言|gông-gông 楞楞|gōng-gōng 戇戇|gôo-lo̍k 娛樂|guā-kháu 外口|guî-ki 危機|gán-kong 眼光|giâm-tiōng 嚴重|gia̍p-tsiá 業者",  # noqa: E501
        ),
        (
            "ng",
            "ngiauh-ngiauh-sô 蟯蟯趖|ngá-tì 雅緻|ng-sng 黃酸|ngôo-khî 蜈蜞|ngôo-kueh-hî 吳郭魚|ngóo-gi̍k 忤逆|ngôo-tông 梧桐|ngiâ-sîn 迎神|ngeh-á 夾仔",  # noqa: E501
        ),
    ],
    "26": [
        (
            "ts",
            "tsá-tsá 早早|tsiù-tsuā 咒誓|tsik-tsuí 積水|tsáu-tsông 走傱|tsuí-tsuânn 水泉|tsip-tsiàu 執照|tsuá-tsînn 紙錢|tsing-tsong 精裝|Tsuân-tsiu 泉州",  # noqa: E501
        ),
        (
            "tsh",
            "tsha-tshò 差錯|tshi-tshám 悽慘|tshì-tshia 試車|tshoo-tshīng 粗穿|tshiú-tsheh 手冊|tshin-tshiat 親切|tshìn-tshái 凊彩|tshing-tshun 青春|tshuh-tshuh",  # noqa: E501
        ),
        (
            "s",
            "si-sû 詩詞|su-siá 書寫|só-sî 鎖匙|siu-sîng 收成|sua-sua 沙沙|siann-sàu 聲嗽|sàm-su 三思|sîng-sim 誠心|sún-si 筍絲",  # noqa: E501
        ),
        (
            "j",
            "jiâu-jiâu 皺皺|jû-hô 如何|jiá-sū 惹事|jím-nāi 忍耐|jūn-gue̍h 閏月|jiân-āu 然後|jia̍t-tsîng 熱情|jio̍k-tiám 弱點|jua̍h-thinn 熱天",  # noqa: E501
        ),
    ],
}

INITIAL_LESSONS = [
    ("lips", "脣音 p、ph、m、b", "23", ["p", "ph", "m", "b"], "【p／ph 不送氣／送氣】【m／b 鼻音／塞音】"),
    ("tip", "舌尖音 t、th、n、l", "24", ["t", "th", "n", "l"], "【t／th 不送氣／送氣】【n／l】"),
    (
        "back",
        "舌根音 k、kh、ng、g；喉音 h",
        "25",
        ["k", "kh", "h", "g", "ng"],
        "【k／kh 不送氣／送氣】【ng／g 鼻音／塞音】【h 擦音】",
    ),
    (
        "teeth",
        "齒音 ts、tsh、s、j",
        "26",
        ["ts", "tsh", "s", "j"],
        "【ts／tsh 不送氣／送氣】【s／j】說明：部分地區「j」與「l」合流。",
    ),
]

TONES = [  # 調序, 例字, 調符, 調值描述 (第 6 調學習時以第 2 調代之)
    (1, "東", "tong", "高平"),
    (2, "黨", "tóng", "高降"),
    (3, "棟", "tòng", "低降"),
    (4, "督", "tok", "中入"),
    (5, "同", "tông", "低升"),
    (6, "黨（動）", "tóng", ""),
    (7, "洞", "tōng", "中平"),
    (8, "毒", "to̍k", "高入"),
]
TONE_RHYMES = [
    ("18-01", "東 黨 棟 督 同 黨 洞 毒", "tong tóng tòng tok tông tóng tōng to̍k"),
    ("18-02", "衫 短 褲 闊 人 矮 鼻 直", "sann té khòo khuah lâng é phīnn ti̍t"),
    ("18-03", "獅 虎 豹 鱉 猴 狗 象 鹿", "sai hóo pà pih kâu káu tshiūnn lo̍k"),
]
TONE_MARK_RULES = [
    "調符優先順序為：a > oo > e、o > i、u。",
    "若 i、u 同時出現，前者是介音，後者為主要元音，則標記在後者上，如 iū 標在 u 上，uī 標在 i 上。",
    "合音及三連音的第一音節有第 9 聲者，可用「 ̋ 」標記，如 ang-âng-âng（紅紅紅）、tsa̋ng（昨昏，tsa-hng 之合音）。",
    "輕聲符號「--」應標記在本調與輕聲之間，輕聲符之前唸本調，輕聲符之後為輕聲。如：āu--ji̍t 後日、tsáu--tshut-khì 走出去。",  # noqa: E501
]

SANDHI = [  # (檔名, 本調, 變調, 條件, [(A/B/C 字, 拼音)])
    ("21-01", 1, 7, "", [("甜", "tinn"), ("甜甜", "tinn-tinn"), ("西瓜甜甜", "si-kue tinn-tinn")]),
    ("21-02", 2, 1, "", [("汫", "tsiánn"), ("汫汫", "tsiánn-tsiánn"), ("井水汫汫", "tsénn-tsuí tsiánn-tsiánn")]),
    ("21-03", 3, 2, "", [("脆", "tshè"), ("脆脆", "tshè-tshè"), ("蕹菜脆脆", "ìng-tshài tshè-tshè")]),
    ("21-04|1", 5, 7, "偏漳", [("鹹", "kiâm"), ("鹹鹹", "kiâm-kiâm"), ("蝦膎鹹鹹", "hê-kê kiâm-kiâm")]),
    ("21-04|2", 5, 3, "偏泉", [("鹹", "kiâm"), ("鹹鹹", "kiâm-kiâm"), ("蝦膎鹹鹹", "hê-kê kiâm-kiâm")]),
    ("21-05", 7, 3, "", [("𩚨", "khiū"), ("𩚨𩚨", "khiū-khiū"), ("壽麵𩚨𩚨", "siū-mī khiū-khiū")]),
    ("22-01", 4, 8, "-p、-t、-k", [("澀", "siap"), ("澀澀", "siap-siap"), ("菝仔澀澀", "pua̍t-á siap-siap")]),
    ("22-02", 4, 2, "-h", [("粕", "phoh"), ("粕粕", "phoh-phoh"), ("菝仔粕粕", "pua̍t-á phoh-phoh")]),
    ("22-03", 8, 4, "-p、-t、-k", [("滑", "ku̍t"), ("滑滑", "ku̍t-ku̍t"), ("墨賊滑滑", "ba̍k-tsa̍t ku̍t-ku̍t")]),
    ("22-04", 8, 3, "-h", [("白", "pe̍h"), ("白白", "pe̍h-pe̍h"), ("墨賊白白", "ba̍k-tsa̍t pe̍h-pe̍h")]),
]

# 附錄一 韻母音節表: 檔名前綴 => (表名, PDF 頁 (1 起算), 韻母欄順序)
TABLES = [
    ("單元音、聲化韻母", ["27"], 15, "a i u e o oo m ng"),
    ("複元音", ["28"], 16, "ai au ia iu io iau ua ui ue uai"),
    ("鼻化元音", ["29"], 16, "ann inn enn onn ainn iann iunn iaunn uann uainn"),
    ("鼻音韻母", ["30", "31"], 17, "am an ang im in ing iam ian iang iong un uan uang om ong"),
    ("入聲韻母（一）", ["32", "33"], 18, "ap at ak ah ip it ik ih ut uh eh oh ok ooh mh"),
    ("入聲韻母（二）", ["34", "35"], 19, "ngh aih auh iuh ueh iap iat iak iah iok ioh iauh uat uah uaih"),
    ("入聲韻母（三）", ["36"], 20, "annh aunnh iannh ennh onnh"),
]

# 進階: 白話字 POJ 對照 (拼法用 scripts/tl_poj_convert.py 轉, 音檔借手冊的例)
POJ_ROWS = [
    ("ts → ch", "tsia", "07-03-C", "遮"),
    ("tsh → chh", "tshia", "07-03-C", "車"),
    ("oo → o͘", "oo", "04-06", ""),
    ("nn → ⁿ", "sann", "08-01-B", "三"),
    ("ua → oa", "kua", "07-07-C", "歌"),
    ("ue → oe", "pue", "07-09-C", "飛"),
    ("ing → eng", "sing", "09-06-B", "生"),
    ("ik → ek", "sik", "10-07-B", "色"),
    ("uan → oan", "suan", "09-12-B", "宣"),
]


# ---------------------------------------------------------------- 音節表


def table_tokens(page: int) -> list[str]:
    txt = subprocess.run(
        ["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(PDF), "-"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return re.findall(r"[a-zA-Z\u00c0-\u024f\u0300-\u036f\u1e00-\u1eff]+", unicodedata.normalize("NFC", txt))


# 附錄一 入聲音節表 (PDF 第 18-20 頁) 第 8 調: 調符佇 PDF 是畫的線, 文字層無, 照渲染頁面逐格對.
TONE8_SEEN = set(
    """
    bit bik tap tit thak lat lah lip lik kik khah hap hat hak hah gak gik tsip tsik tshak sah sip sit jip jit
    put poh but boh tut theh loh kut khok hoh hmh gok
    phauh phueh bueh piat biat tiap thiap lauh lueh liat hiap gueh giat tshauh jiap jiat
    khiak tshiak tioh liok lioh giah gioh siok ngiauh puat buat luat guat juah uah luaih
    khaunnh haunnh khennh
    """.split()  # noqa: SIM905
)
# 書面看袂清 (jih 的 i 印做無點, 調符無清楚) 的格先跳過
UNCLEAR = {"jih"}


def build_tables(audio_names: set[str]) -> list[dict]:
    tables = []
    for title, prefixes, page, rimes in TABLES:
        files = sorted(n for n in audio_names if any(n.startswith(f"0101-{p}-") for p in prefixes))
        toned: dict[str, str] = {}
        for tok in table_tokens(page):
            key = strip_tone(tok).lower()
            if tok != key and key not in toned:
                toned[key] = tok.lower()
        cells = []
        for f in files:
            syl = f.rsplit("-", 1)[1].removesuffix(".mp3")
            if syl in UNCLEAR:
                continue
            tl = toned.get(syl, syl)
            if syl in TONE8_SEEN:
                if tl != syl:
                    raise SystemExit(f"{f}: 有調符 {tl} 閣列佇第 8 調")
                tl = put_mark(syl, TONE8)
            ini, rime = split_initial(syl)
            cells.append({"ini": ini, "rime": rime, "tl": tl, "audio": f})
        tables.append({"title": title, "rimes": rimes.split(), "cells": cells})
    return tables


# ---------------------------------------------------------------- 課程


def build_lessons() -> list[dict]:
    L: list[dict] = []

    def choose(pool):  # 練習: 聽音檔, 揀答案
        return {"kind": "listen", "pool": pool}

    v_items = [
        {"tl": v, "audio": a(f), "mouth": v, "info": {"發音方法": d, "華語注音": z, "英語音標": e}}
        for v, f, d, z, e in VOWELS
    ]
    L.append(
        {
            "id": "vowels",
            "part": "韻母",
            "title": "單元音 a、i、u、e、o、oo",
            "intro": ["台語有六個單元音。先看嘴形，聽音檔，跟咧唸。o 佮 oo 無仝：o 嘴脣半開、oo 嘴脣較圓。"],
            "sections": [{"title": "單元音", "items": v_items}],
            "quiz": choose([{"audio": i["audio"], "answer": i["tl"]} for i in v_items]),
        }
    )

    def rime_lesson(lid, title, rows, prefix, rime_tag, ex_tag, intro, extra=None, notes=()):
        items = []
        for n, (rime, examples) in enumerate(rows, 1):
            items.append(
                {
                    "tl": rime,
                    "audio": a(f"{prefix}-{n:02d}-{rime_tag}"),
                    "examples": ex(examples, prefix),
                    "examplesAudio": a(f"{prefix}-{n:02d}-{ex_tag}"),
                }
            )
        sections = [{"title": title, "items": items, "notes": list(notes)}]
        if extra:
            sections.append(extra)
        pool = [{"audio": i["audio"], "answer": i["tl"]} for s in sections for i in s["items"]]
        L.append(
            {"id": lid, "part": "韻母", "title": title, "intro": intro, "sections": sections, "quiz": choose(pool)}
        )

    rime_lesson(
        "diphthongs", "複元音", DIPHTHONGS, "07", "B", "C", ["兩個抑三個元音連做伙唸，嘴形對頭一个滑去後一个。"]
    )
    syl_items = [{"tl": r, "audio": a(f), "examples": ex(e, "08")} for r, f, e in SYLLABIC]
    rime_lesson(
        "nasalized",
        "鼻化元音",
        NASALIZED,
        "08",
        "A",
        "B",
        ["韻母後壁加 nn，表示聲音對鼻空出來（鼻化）。nn 毋是一个音，是鼻化的記號。"],
        extra={"title": "聲化韻母 m、ng", "items": syl_items, "notes": []},
        notes=["onn 為 oonn 的簡省，因為該音節不存在 onn 與 oonn 的區別。"],
    )
    rime_lesson(
        "nasal",
        "鼻音韻母",
        NASAL_FINALS,
        "09",
        "A",
        "B",
        ["韻尾 -m 雙脣合起來、-n 舌尖頂上齒齦、-ng 舌根頂軟顎。"],
        notes=[
            "om 為 oom 的簡省，因為該音節不存在 om 與 oom 的區別。",
            "ong 為 oong 的簡省，因為該音節不存在 ong 與 oong 的區別。",
        ],
    )
    checked_items = [
        {"tl": r, "audio": a(f"10-{n:02d}-A"), "examples": ex(e, "10"), "examplesAudio": a(f"10-{n:02d}-B")}
        for n, (r, e) in enumerate(CHECKED_10, 1)
    ]
    for n, (r, e) in enumerate(CHECKED_11, 1):
        rt, et = ("B", "C") if n <= 10 else ("A", "B")
        checked_items.append(
            {"tl": r, "audio": a(f"11-{n:02d}-{rt}"), "examples": ex(e, "11"), "examplesAudio": a(f"11-{n:02d}-{et}")}
        )
    L.append(
        {
            "id": "checked",
            "part": "韻母",
            "title": "入聲韻母 -p、-t、-k、-h",
            "intro": [
                "入聲字短短、緊緊，唸到尾嘴就停咧，無共聲放出來。",
                "-p：雙脣合起來停咧；-t：舌尖頂上齒齦停咧；-k：舌根頂軟顎停咧；-h：喉嚨頓一下（喉塞音），佮聲母 h 無仝。",  # noqa: E501
            ],
            "sections": [
                {
                    "title": "入聲韻母",
                    "items": checked_items,
                    "notes": ["ok 為 ook 的簡省，因為該音節不存在 ok 與 ook 的區別。"],
                }
            ],
            "quiz": choose([{"audio": i["audio"], "answer": i["tl"]} for i in checked_items]),
        }
    )

    order = {ini: n for n, ini in enumerate(INITIALS, 1)}
    for lid, title, wprefix, inis, note in INITIAL_LESSONS:
        items = []
        for ini in inis:
            place, method, zhuyin, eng = INITIAL_INFO[ini]
            info = {"發音部位": place, "發音方法": method}
            if zhuyin:
                info["華語注音"] = zhuyin
            if eng:
                info["英語音標"] = eng
            items.append({"tl": ini, "audio": a(f"03-{order[ini]:02d}"), "place": PLACE_KEY[place], "info": info})
        words = []
        for g, (ini, row) in enumerate(INITIAL_WORDS[wprefix], 1):
            for n, w in enumerate(row.split("|"), 1):
                tl, _, han = w.partition(" ")
                words.append({"tl": tl, "han": han, "ini": ini, "audio": a(f"{wprefix}-{g:02d}-{n:02d}")})
        L.append(
            {
                "id": f"initials-{lid}",
                "part": "聲母",
                "title": title,
                "intro": [note, "「送氣」：唸的時有一口氣衝出來，手囥喙前會感覺著風；「不送氣」就無。"],
                "sections": [{"title": "聲母", "items": items}, {"title": "拼音練習（附錄一）", "items": words}],
                "quiz": choose([{"audio": w["audio"], "answer": f"{w['tl']} {w['han']}".strip()} for w in words]),
            }
        )

    tone_items = [{"tl": tl, "han": han, "tone": n, "desc": d, "audio": a(f"05-{n:02d}")} for n, han, tl, d in TONES]
    rhymes = [{"tl": tl, "han": han, "audio": a(f)} for f, han, tl in TONE_RHYMES]
    L.append(
        {
            "id": "tones",
            "part": "聲調",
            "title": "八聲調",
            "intro": [
                "台語本調有八個聲調（調序 1–8）。用「東 黨 棟 督 同 黨 洞 毒」口訣記，逐家做伙唸。",
                "學習時，第 6 調以第 2 調代之。第 1、4 調無標調符；第 4、8 調是入聲（-p、-t、-k、-h 尾）。",
            ],
            "sections": [
                {"title": "基本聲調", "items": tone_items},
                {"title": "口訣", "items": rhymes},
                {"title": "調符標記位置", "items": [], "notes": TONE_MARK_RULES},
            ],
            "quiz": {
                "kind": "listen",
                "prompt": "這是第幾調？",
                "pool": [{"audio": i["audio"], "answer": f"第 {i['tone']} 調"} for i in tone_items if i["tone"] != 6],
            },
        }
    )

    s_items, s_pool = [], []
    for fn, base, out, cond, words in SANDHI:
        f, _, var = fn.partition("|")
        suf = f"-{var}" if var else ""
        group = [{"tl": tl, "han": han, "audio": a(f"{f}-{k}{suf}")} for k, (han, tl) in zip("ABC", words, strict=True)]
        label = f"第 {base} 調 → 第 {out} 調" + (f"（{cond}）" if cond else "")
        s_items.append({"title": label, "items": group})
        s_pool.append(
            {
                "audio": group[1]["audio"],
                "show": f"{group[1]['han']} {group[1]['tl']}",
                "answer": f"第 {out} 調",
                "base": base,
                "cond": cond,
            }
        )
    L.append(
        {
            "id": "sandhi",
            "part": "變調",
            "title": "連續變調",
            "intro": [
                "臺灣台語的本調有八個聲調，單獨一個字出現或出現在最後一個字時，大部分讀本調。",
                "如果不在最後一個字，兩字連讀，通常前面的字都要變調，這就是所謂的「連續變調」。",
                "手冊用〈8調ê滋味〉（詞／李勤岸，曲／陳昆仁）的食物滋味做例。",
            ],
            "sections": s_items,
            "quiz": {
                "kind": "listen",
                "prompt": "連讀的時，頭一字變做第幾調？",
                "pool": s_pool,
                "options": [f"第 {n} 調" for n in (1, 2, 3, 4, 7, 8)],
            },
        }
    )
    return L


def build_poj() -> dict:
    items = []
    for label, tl, f, han in POJ_ROWS:
        items.append({"tl": tl, "poj": tl_to_poj(tl), "han": han, "rule": label, "audio": a(f)})
    return {
        "id": "poj",
        "part": "進階",
        "title": "進階：白話字（POJ）對照",
        "intro": [
            "白話字（POJ）是較早的台語羅馬字，教會公報、舊冊攏用伊。發音仝款，干焦寫法無仝。",
            "會台羅（TL）了後，記下面幾條就會曉讀白話字。聲調符號仝款，o͘ 是 o 加一點、ⁿ 是細細的 n。",
        ],
        "sections": [{"title": "台羅 → 白話字", "items": items}],
        "quiz": {
            "kind": "listen",
            "prompt": "這个音，白話字按怎寫？",
            "pool": [{"audio": i["audio"], "show": i["tl"], "answer": i["poj"]} for i in items],
        },
    }


def referenced(data: dict) -> set[str]:
    out: set[str] = set()

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("audio", "examplesAudio") and isinstance(v, str):
                    out.add(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(data)
    return out


def url_ok(name: str) -> bool:
    req = urllib.request.Request(
        AUDIO_BASE + urllib.parse.quote(name), method="HEAD", headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status == 200 and r.headers.get("Content-Type", "").startswith("audio/")
    except urllib.error.URLError:
        return False


def ensure_pdf() -> None:
    if PDF.exists():
        return
    PDF.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(PDF_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as r:
        PDF.write_bytes(r.read())


def pdf_audio_names() -> set[str]:
    import pdfplumber

    names = set()
    with pdfplumber.open(str(PDF)) as pdf:
        for p in pdf.pages:
            for annot in p.annots:
                uri = annot.get("uri") or ""
                if uri.endswith(".mp3"):
                    names.add(urllib.parse.unquote(uri).rsplit("/", 1)[1])
    return names


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skip-url-check", action="store_true", help="毋 HEAD 檢查官方音檔網址 (離線用)")
    args = ap.parse_args()
    ensure_pdf()
    names = pdf_audio_names()
    lessons = build_lessons()
    tables = build_tables(names)
    lessons.append(
        {
            "id": "tables",
            "part": "練習",
            "title": "拼音練習：音節表",
            "intro": [
                "先看縱列聲母，再對應到橫列韻母，試著拼出音節，再想想看這個羅馬字可以是什麼意思。",
                "點表格內底的音節就會唸。",
            ],
            "tables": tables,
            "sections": [],
            "quiz": {
                "kind": "listen",
                "pool": [
                    {"audio": c["audio"], "answer": c["tl"], "group": t["title"]} for t in tables for c in t["cells"]
                ],
            },
        }
    )
    lessons.append(build_poj())
    data = {"source": SOURCE, "audioBase": AUDIO_BASE, "lessons": lessons}
    used = referenced(data)
    missing = used - names
    if missing:
        raise SystemExit(f"手冊無這寡音檔: {sorted(missing)[:10]}")
    if not args.skip_url_check:
        with ThreadPoolExecutor(8) as pool:
            bad = [n for n, ok in zip(sorted(used), pool.map(url_ok, sorted(used)), strict=True) if not ok]
        if bad:
            raise SystemExit(f"官方音檔網址無效 {len(bad)} 个: {bad[:10]}")
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(lessons)} 課, {len(used)}/{len(names)} 音檔 (官方網址) → {OUT_JSON.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
