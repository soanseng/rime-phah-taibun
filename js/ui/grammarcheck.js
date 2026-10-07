// 轉換頁輸入區的文法檢查佮教學（建議性質——規則比對，毋是語法解析）：
// ① 用字建議——比對 hints.calque（上長片語優先，覆蓋到的 span 袂重複列）
// ② 輕聲標記建議——hints.lighttone
// ③ 可能用著的文法點——照 grammar-notes 的 match（漢字子字串）／matchRe（正規）掃，
//    chip 點了 revealNote 跳去文法頁看彼篇。
// 子字串比對天然會拄著（親像「的」佇教典詞內底）——一律「建議檢查／可參考」口氣。

import { revealNote } from "./grammar.js?v=22";

const deaccent = (s) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// 純 ASCII 觸發詞（臺羅）＝詞界比對；包含漢字＝子字串比對
const isRoman = (s) => /^[\x21-\x7E]+$/.test(s);

export function initGrammarCheck(hints) {
  let notes = null; // grammar-notes.json（非同步載入；載好前 chips 段靜靜無出現）
  let lastText = null; // fetch 未轉好就拍字的 race：轉好補 render
  fetch("./data-public/grammar-notes.json")
    .then((r) => (r.ok ? r.json() : null))
    .then((j) => {
      notes = j ? j.notes : [];
      if (lastText !== null) render(lastText);
    })
    .catch(() => {});

  // —— ① calque：長片語先佔 span，「有沒有」著了，「沒」「不」予伊食掉 ——
  const findCalque = (text) => {
    const sorted = [...hints.calque].sort((a, b) => b.han.length - a.han.length);
    const taken = []; // [start, end)
    const covered = (s, e) => taken.some(([ts, te]) => s < te && ts < e);
    const out = [];
    for (const c of sorted) {
      let idx = text.indexOf(c.han), n = 0, first = -1;
      while (idx !== -1) {
        if (!covered(idx, idx + c.han.length)) {
          taken.push([idx, idx + c.han.length]);
          n += 1;
          if (first < 0) first = idx;
        }
        idx = text.indexOf(c.han, idx + 1);
      }
      if (n) out.push({ ...c, n, first });
    }
    return out.sort((a, b) => a.first - b.first);
  };

  // —— ③ 文法點觸發詞掃描：記頭一格位置，照出現順排 chip ——
  const scanNotes = (raw) => {
    if (!notes) return [];
    const text = deaccent(raw);
    const out = [];
    for (const n of notes) {
      const hits = new Map(); // word → first idx
      for (const w of n.match ?? []) {
        let idx = -1;
        if (isRoman(w)) {
          const m = new RegExp(`(?<![a-z0-9])${w}(?![a-z0-9])`, "u").exec(text);
          idx = m ? m.index : -1;
        } else {
          idx = raw.indexOf(w);
        }
        if (idx >= 0) hits.set(w, idx);
      }
      if (n.matchRe) {
        for (const m of raw.matchAll(new RegExp(n.matchRe, "gu"))) {
          if (!hits.has(m[0])) hits.set(m[0], m.index);
        }
      }
      if (hits.size) {
        out.push({
          id: n.id,
          title: n.title,
          words: [...hits.keys()],
          first: Math.min(...hits.values()),
        });
      }
    }
    return out.sort((a, b) => a.first - b.first);
  };

  function render(text) {
    const $g = $("#cv-gram");
    if (!text.trim()) {
      $g.hide().prop("hidden", true).empty();
      return;
    }
    $g.prop("hidden", false).show().empty();

    const issues = findCalque(text);
    if (issues.length) {
      $g.append(
        "<div class='hint-title'>建議檢查——拄著華語用字／直譯（規則比對，僅供參考，未必有錯）</div>" +
        "<ul class='chk-list'></ul>",
      );
      const $ul = $g.find(".chk-list").last();
      for (const c of issues) {
        const $li = $("<li></li>").html(
          `<b class='chk-han'>${esc(c.han)}</b>${c.n > 1 ? ` <span class='chk-n'>×${c.n}</span>` : ""}` +
          `：可參考 <code>${esc(c.suggest)}</code>`,
        );
        if (c.note && notes?.some((n) => n.id === c.note)) {
          $li.append(
            $("<button type='button' class='chk-note'>看文法</button>")
              .on("click", () => revealNote(c.note)),
          );
        }
        $ul.append($li);
      }
    }

    const lts = [];
    for (const lt of hints.lighttone) {
      if (text.includes(lt.han)) lts.push(lt);
      if (lts.length >= 8) break;
    }
    if (lts.length) {
      $g.append("<div class='hint-title'>輕聲標記建議（依用字偵測）</div><ul></ul>");
      const $ul = $g.find("ul").last();
      for (const lt of lts) {
        $ul.append($("<li></li>").html(`輕聲：<code>${esc(lt.marked)}</code>（${esc(lt.reading)}）`));
      }
    }

    const hits = scanNotes(text);
    if (hits.length) {
      $g.append(
        "<div class='hint-title'>可能用著的文法點（子字串比對，點 chip 去文法頁看說明）</div>" +
        "<div class='gram-chips'></div>",
      );
      const $chips = $g.find(".gram-chips").last();
      for (const h of hits) {
        const words = h.words.slice(0, 4).map(esc).join("、") + (h.words.length > 4 ? "…" : "");
        $("<button type='button' class='gram-chip'></button>")
          .html(`<b>${words}</b><span class='gram-chip-t'>${esc(h.title)}</span>`)
          .on("click", () => revealNote(h.id))
          .appendTo($chips);
      }
    }

    const rows = hints.calque
      .map((c) => `<li>「${esc(c.han)}」→ <code>${esc(c.suggest)}</code></li>`)
      .join("");
    $g.append(
      "<details class='calque'><summary>華語→台語 通用對照表（單字佮多字結構，點開看；參考用，毋是自動文法解析）</summary>" +
      `<ul>${rows}</ul></details>`,
    );
  }

  return (text) => {
    lastText = text;
    render(text);
  };
}
