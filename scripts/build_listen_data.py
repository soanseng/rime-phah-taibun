"""聽寫資料建置 - 教典例句文字佮官方音檔 => docs/study/data/listen.json + docs/study/audio/.

來源: 教育部臺灣台語常用詞辭典 data mirror (kautian.csv) 佮 sutian.moe.edu.tw 的
leku-mp3.zip (用 HTTP Range 干焦讀著愛的成員, 毋下載規隻 zip). 授權 CC BY-ND 3.0 TW:
文字照原文引用, 音檔干焦做格式轉換 (單聲道 22.05 kHz 32 kbps MP3), 無改內容.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import posixpath
import re
import subprocess
import time
import unicodedata
import urllib.error
import urllib.request
import zipfile
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_GLOB = "data/KipSutianDataMirror/public/*/bunji/kautian.csv"
ZIP_URL = "https://sutian.moe.edu.tw/media/senn/leku-mp3.zip"
CACHE_DIR = REPO_ROOT / "data" / "leku-mp3-cache"
OUT_JSON = REPO_ROOT / "docs" / "study" / "data" / "listen.json"
OUT_AUDIO = REPO_ROOT / "docs" / "study" / "audio"
USER_AGENT = "rime-phah-taibun-build/1.0 (https://taigi.anatomind.com)"

DEFAULT_LIMIT = 900  # 1000 條會超過 15 MB 的目標, 900 條約 14.3 MB
MIN_SLOTS = 5
MAX_SLOTS = 16
SENT_END = ("。", "！", "？")  # noqa: RUF001 - 台文句尾是全形標點
FETCH_SLEEP = 0.2  # 每擺區塊下載中間歇睏, 袂傷沖伺服器

META = {
    "source": "教育部《臺灣台語常用詞辭典》例句文字佮音檔",
    "license": "CC BY-ND 3.0 TW",
    "url": "https://sutian.moe.edu.tw/",
    "note": "原文原音照引；音檔轉做單聲道 32 kbps MP3",  # noqa: RUF001 - 台文說明用全形分號
}

LABEL_RE = re.compile(r"^\s*(\d+(?:-\d+)?)\s*\.\s*")
TAIL_PAREN_RE = re.compile(r"^(.*)[（(]([^（）()]*)[)）]\s*$", re.DOTALL)  # noqa: RUF001 - 愛匹配全形括號
WORD_MARKER_RE = re.compile(r"[（(][^（）()]*[)）]$")  # noqa: RUF001 - 愛匹配全形括號
TONE_DIGIT_RE = re.compile(r"[1-8]+$")
_LATIN = "A-Za-z\u00c0-\u024f\u0300-\u036f\u0358\u207f\u0131·"
LATIN_RUN_RE = re.compile("[" + _LATIN + "]+(?:-+[" + _LATIN + "]+)*")


def label_key(label: str) -> tuple[int, int]:
    """標籤 '3-1' 排做 (3, 1), 予編號照數字大細排."""
    first, _, second = label.partition("-")
    return int(first), int(second or 0)


def parse_numbered(text: str) -> dict[str, str]:
    """共 '1. aa\\n2. bb\\n3-1. cc' 拆做 dict; 無編號的接續行歸入前一條."""
    out: dict[str, str] = {}
    label = None
    for line in text.splitlines():
        match = LABEL_RE.match(line)
        if match:
            label = match.group(1)
            body = line[match.end() :].strip()
            if label not in out:
                out[label] = body
            elif body:
                out[label] += " " + body
        elif label is not None and line.strip():
            out[label] += " " + line.strip()
    return out


def split_han_tl(text: str) -> tuple[str, str] | None:
    """'漢字 (羅馬字)' 提上尾一个括號內底的羅馬字; 括號愛有空, 羅馬字無字母就 None."""
    match = TAIL_PAREN_RE.match(text.strip())
    if match is None:
        return None
    han, tl = match.group(1).strip(), match.group(2).strip()
    if not han or len(re.findall(r"[A-Za-z]", tl)) < 2:
        return None
    return han, tl


def syl_key(syllable: str) -> str:
    """一音節的無調鍵 (佮 try/practice-core.js 的 sylKey 同規則)."""
    text = unicodedata.normalize("NFC", syllable).replace("ı", "i").replace("·", "\u0358")  # noqa: RUF001 - dotless i 佮中央點是愛替換的字元
    text = re.sub("[oO]\u0358", "oo", text)
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return TONE_DIGIT_RE.sub("", text.replace("-", "").lower())


def is_han(ch: str) -> bool:
    """佮 thak dict.js 的 isHan 相仝的漢字範圍。"""
    code = ord(ch)
    return 0x3400 <= code <= 0x9FFF or 0x20000 <= code <= 0x3FFFF


def _roman_syllables(text: str) -> list[str] | None:
    """拆羅馬字音節 (連字號嘛拆, 標點裁掉); 有一个 token 完全無字母就 None."""
    parts: list[str] = []
    for token in text.split():
        letters = 0
        for piece in re.split("-+", token):
            key = syl_key(piece)
            if key:
                parts.append(key)
                letters += 1
        if letters == 0:
            return None
    return parts


def align_slots(han: str, tl: str) -> int | None:
    """漢字數 + 漢字內底的羅馬字音節數 == 羅馬字音節數 => 拍數; 無對齊 None."""
    syllables = _roman_syllables(tl)
    if not syllables:
        return None
    count = sum(1 for ch in han if is_han(ch))
    for run in LATIN_RUN_RE.findall(han):
        count += sum(1 for piece in re.split("-+", run) if syl_key(piece))
    return count if count == len(syllables) else None


def row_candidates(row: dict[str, str]) -> list[dict]:
    """一列 kautian.csv => 候選列表 (照標籤順序); 詞目的 (替) 標記愛除掉."""
    try:
        word_id = int((row.get("詞目id") or "").strip())
    except ValueError:
        return []
    word = WORD_MARKER_RE.sub("", (row.get("漢字") or "").strip()).strip()
    examples = parse_numbered(row.get("例句") or "")
    hoa = parse_numbered(row.get("例句-華語") or "")
    audio = parse_numbered(row.get("例句-音檔") or "")
    out: list[dict] = []
    for label in sorted(set(examples) & set(hoa) & set(audio), key=label_key):
        pair = split_han_tl(examples[label])
        if pair is None:
            continue
        han, tl = pair
        audio_id = audio[label].strip().replace("\\", "/").split("/")[-1]
        if audio_id.lower().endswith(".mp3"):
            audio_id = audio_id[:-4]
        out.append(
            {
                "wordId": word_id,
                "word": word,
                "label": label,
                "han": han,
                "tl": tl,
                "hoa": hoa[label].strip(),
                "audioId": audio_id,
            }
        )
    return out


def spread_evenly(eligible: list[dict], limit: int) -> list[dict]:
    """對排好的合格列表均勻提 limit 條 (頭尾攏有份)."""
    if limit <= 0 or len(eligible) <= limit:
        return list(eligible)
    return [eligible[i * len(eligible) // limit] for i in range(limit)]


def select_items(candidates: list[dict], audio_names: set[str], limit: int) -> list[dict]:
    """揀聽寫題: 完整句, 拍數 5-16, 音檔佇 zip 內底, 一個詞目上多一句."""
    basenames = {name.replace("\\", "/").split("/")[-1] for name in audio_names}
    eligible: list[dict] = []
    seen: set[int] = set()
    for cand in sorted(candidates, key=lambda c: (c["wordId"], label_key(c["label"]))):
        if cand["wordId"] in seen:
            continue
        slots = align_slots(cand["han"], cand["tl"]) if cand["han"].endswith(SENT_END) else None
        if slots is None or not MIN_SLOTS <= slots <= MAX_SLOTS:
            continue
        if f"{cand['audioId']}.mp3" not in basenames:
            continue
        eligible.append(cand)
        seen.add(cand["wordId"])
    return spread_evenly(eligible, limit)


def zip_basename_map(names: list[str]) -> dict[str, str]:
    """mp3 成員的 basename (細寫) => 完整成員路徑; 頭一个贏, 排序了固定."""
    out: dict[str, str] = {}
    for name in sorted(names):
        norm = name.replace("\\", "/")
        if norm.lower().endswith(".mp3"):
            out.setdefault(posixpath.basename(norm).lower(), norm)
    return out


def probe_http_size(url: str, timeout: float = 60.0) -> int:
    """HEAD (袂得就用 Range bytes=0-0) 揣檔案大小."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            length = resp.headers.get("Content-Length")
            if length:
                return int(length)
    except (urllib.error.URLError, OSError):
        pass
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Range": "bytes=0-0"})
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        content_range = resp.headers.get("Content-Range", "") if resp.status == 206 else ""
        if "/" in content_range:
            return int(content_range.rsplit("/", 1)[1])
    raise RuntimeError(f"無法度取得 {url} 的檔案大小")


class HttpRangeFile(io.IOBase):
    """用 HTTP Range 的唯讀可 seek 檔案物件: 分塊下載 + LRU 區塊快取, 予 zipfile 直接開.

    fetch 會使注入 (測試用); 無注入就用 urllib, 附 User-Agent, 206 檢查佮暫時錯誤重試.
    """

    def __init__(
        self,
        url: str,
        fetch: Callable[[int, int], bytes] | None = None,
        size: int | None = None,
        block_size: int = 1 << 20,
        max_blocks: int = 64,
        delay: float = 0.0,
        retry_sleep: float = 1.0,
        timeout: float = 60.0,
    ):
        super().__init__()
        self.url = url
        self._fetch_fn = fetch
        self._size = size
        self.block_size = block_size
        self._max_blocks = max_blocks
        self._delay = delay
        self._retry_sleep = retry_sleep
        self._timeout = timeout
        self._pos = 0
        self._cache: OrderedDict[int, bytes] = OrderedDict()

    @property
    def size(self) -> int:
        if self._size is None:
            self._size = probe_http_size(self.url, timeout=self._timeout)
        return self._size

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            pos = offset
        elif whence == 1:
            pos = self._pos + offset
        elif whence == 2:
            pos = self.size + offset
        else:
            raise ValueError(f"非法 whence: {whence}")
        self._pos = max(0, min(pos, self.size))
        return self._pos

    def read(self, amount: int = -1) -> bytes:
        remaining = self.size - self._pos if amount is None or amount < 0 else min(amount, self.size - self._pos)
        chunks = bytearray()
        while remaining > 0:
            block = self._block(self._pos // self.block_size)
            offset = self._pos % self.block_size
            chunk = block[offset : offset + remaining]
            chunks += chunk
            self._pos += len(chunk)
            remaining -= len(chunk)
        return bytes(chunks)

    def readinto(self, buffer) -> int:  # type: ignore[override]
        data = self.read(len(buffer))
        buffer[: len(data)] = data
        return len(data)

    def _block(self, index: int) -> bytes:
        block = self._cache.get(index)
        if block is not None:
            self._cache.move_to_end(index)
            return block
        start = index * self.block_size
        end = min(start + self.block_size, self.size)
        block = self._fetch(start, end)
        self._cache[index] = block
        while len(self._cache) > self._max_blocks:
            self._cache.popitem(last=False)
        return block

    def _fetch(self, start: int, end: int) -> bytes:
        last_exc: Exception | None = None
        for attempt in range(4):
            if self._delay:
                time.sleep(self._delay)
            try:
                if self._fetch_fn is not None:
                    return self._fetch_fn(start, end)
                return self._fetch_http(start, end)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                if isinstance(exc, urllib.error.HTTPError) and exc.code in (403, 404):
                    raise
                last_exc = exc
                if attempt < 3 and self._retry_sleep:
                    time.sleep(self._retry_sleep * (2**attempt))
        raise RuntimeError(f"下載 {self.url} bytes {start}-{end - 1} 失敗") from last_exc

    def _fetch_http(self, start: int, end: int) -> bytes:
        request = urllib.request.Request(
            self.url,
            headers={"User-Agent": USER_AGENT, "Range": f"bytes={start}-{end - 1}"},
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as resp:
            if resp.status != 206:
                raise RuntimeError(f"HTTP {resp.status}: 伺服器無支援 Range 請求")
            return resp.read()


def newest_csv(repo_root: Path) -> Path:
    hits = sorted(repo_root.glob(CSV_GLOB))
    if not hits:
        raise FileNotFoundError(f"揣無 {CSV_GLOB}; 請先跑 scripts/download_resources.sh")
    return hits[-1]


def transcode(src: Path, dst: Path) -> None:
    """轉做單聲道 22.05 kHz 32 kbps MP3, metadata 攏除掉."""
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-map_metadata",
        "-1",
        "-ac",
        "1",
        "-ar",
        "22050",
        "-b:a",
        "32k",
        str(dst),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        dst.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg 轉檔失敗 {src.name}: {proc.stderr.strip()}")


def pull_item(archive: zipfile.ZipFile, base_map: dict[str, str], cand: dict) -> dict:
    """提一條: raw 進快取, 轉檔, 組 JSON item."""
    audio_id = cand["audioId"]
    cached = CACHE_DIR / f"{audio_id}.mp3"
    if not cached.exists():
        with archive.open(base_map[f"{audio_id}.mp3"]) as handle:
            cached.write_bytes(handle.read())
    dst = OUT_AUDIO / f"{audio_id}.mp3"
    if not dst.exists() or dst.stat().st_size == 0:
        transcode(cached, dst)
    return {
        "id": audio_id,
        "word": cand["word"],
        "wordId": cand["wordId"],
        "han": cand["han"],
        "tl": cand["tl"],
        "hoa": cand["hoa"],
        "audio": f"{audio_id}.mp3",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="起造聽寫資料 (教典例句 + 官方音檔)")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="提幾條例句 (默認 %(default)s)")
    args = parser.parse_args(argv)

    csv_path = newest_csv(REPO_ROOT)
    print(f"讀 {csv_path}")
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        candidates = [cand for row in csv.DictReader(handle) for cand in row_candidates(row)]

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_AUDIO.mkdir(parents=True, exist_ok=True)
    remote = HttpRangeFile(ZIP_URL, delay=FETCH_SLEEP)
    with zipfile.ZipFile(remote) as archive:
        base_map = zip_basename_map(archive.namelist())
        selected = select_items(candidates, set(base_map), args.limit)
        print(f"候選 {len(candidates)} 條, 選出 {len(selected)} 條")
        items = [pull_item(archive, base_map, cand) for cand in selected]
        for done, _ in enumerate(items, 1):
            if done % 50 == 0 or done == len(items):
                print(f"… {done}/{len(items)}")

    data = {"meta": META, "items": items}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    keep = {f"{cand['audioId']}.mp3" for cand in selected}
    for stale in OUT_AUDIO.glob("*.mp3"):
        if stale.name.lower() not in keep:
            stale.unlink()
    total = sum(path.stat().st_size for path in OUT_AUDIO.glob("*.mp3"))
    print(f"聽寫 {len(items)} 條 => {OUT_JSON}")
    print(f"音檔 {len(list(OUT_AUDIO.glob('*.mp3')))} 个, 計 {total / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
