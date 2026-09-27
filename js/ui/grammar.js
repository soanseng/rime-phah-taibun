// 文法分頁：
// ① 文法筆記——本站原創整理（說明／例句自寫，分類自訂），參考資料逐篇標示。
// ② TGGL 語法點索引——依原站授權條款（語料不得移轉第三人）只收書目中繼資料，
//    語法說明佮例句一律連回原系統查閱；謹此致謝教育部。

const deaccent = (s) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();

const esc = (s) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");

async function fetchJson(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}

// —— ① 文法筆記（本站整理） ——
async function initNotes() {
  let data;
  try {
    data = await fetchJson("./data-public/grammar-notes.json");
  } catch {
    $("#gr-notes").html('<p class="hint">文法筆記載入失敗（grammar-notes.json）</p>');
    return;
  }
  const catTitle = new Map(data.categories.map((c) => [c.id, c.title]));

  $("#gr-note-cats").html(
    `<button type="button" class="seg-btn is-active" data-cat="">全部（${data.notes.length}）</button>` +
      data.categories
        .map(
          (c) =>
            `<button type="button" class="seg-btn" data-cat="${c.id}">${esc(c.title)}</button>`,
        )
        .join(""),
  );

  $("#gr-notes").html(
    data.notes
      .map((n) => {
        const body = n.body.map((p) => `<p>${p}</p>`).join("");
        const exs = n.examples
          .map((e) => {
            const hua = e.hua ? `<span class="hua">　${esc(e.hua)}</span>` : "";
            const note = e.note ? `<span class="hua">　〔註〕${esc(e.note)}</span>` : "";
            return (
              `<div class="gr-ex"><span class="han">${esc(e.han)}</span>` +
              `<span class="tl">　${esc(e.tl)}</span>${hua}${note}` +
              `<span class="gr-src-tag">${e.src === "moedict" ? "教典" : "自造"}</span></div>`
            );
          })
          .join("");
        const refs = n.refs
          .map(
            (r) =>
              `<a href="${r.url}" target="_blank" rel="noopener">${esc(r.label)}</a>`,
          )
          .join("・");
        return (
          `<article class="gr-note" data-cat="${n.cat}">` +
          `<span class="gr-cat">${esc(catTitle.get(n.cat) ?? "")}</span>` +
          `<h4>${esc(n.title)}</h4>${body}` +
          `<div class="gr-ex-list">${exs}</div>` +
          `<p class="gr-refs hint">參考：${refs}</p>` +
          `</article>`
        );
      })
      .join(""),
  );

  $("#gr-note-cats").on("click", ".seg-btn", (ev) => {
    const $b = $(ev.currentTarget);
    $("#gr-note-cats .seg-btn").removeClass("is-active");
    $b.addClass("is-active");
    const cat = String($b.data("cat"));
    $("#gr-notes .gr-note").each((_, el) => {
      el.hidden = !!cat && el.dataset.cat !== cat;
    });
  });
}

// —— ② TGGL 語法點索引（外連原文） ——
async function initIndex() {
  let data;
  try {
    data = await fetchJson("./data-public/grammars.json");
  } catch {
    $("#gr-count").text("文法索引載入失敗（grammars.json）");
    return;
  }
  const { entries, groups, snippets, search } = data;
  const gTitle = new Map(groups.map((g) => [g.no, g.title]));
  const srcUrl = (name) =>
    `${search.url}?n=20&type=word&${search.field}=${encodeURIComponent(name)}`;

  // 群組下拉：全部 ＋ 有標題的群組 ＋ 其他（無標題群組歸作一類）
  $("#gr-group").html(
    `<option value="">全部（${entries.length} 筆）</option>` +
      groups
        .map((g) => `<option value="${g.no}">${g.no}　${esc(g.title)}</option>`)
        .join("") +
      `<option value="_">其他（無群組標題）</option>`,
  );

  $("#gr-tbl tbody").html(
    entries
      .map((e) => {
        const k = esc(`${e.name} ${e.roman} ${e.id} ${gTitle.get(e.group) ?? ""}`);
        return (
          `<tr data-k="${k}" data-g="${e.groupTitle ? e.group : "_"}">` +
          `<td class="gr-id">${e.id}</td>` +
          `<td class="w">${esc(e.name)}</td>` +
          `<td class="roman">${esc(e.roman)}</td>` +
          `<td class="hint">${e.groupTitle ? esc(e.groupTitle) : "—"}</td>` +
          `<td><a class="dict-link" href="${srcUrl(e.name)}" target="_blank" rel="noopener">原文</a></td>` +
          `</tr>`
        );
      })
      .join(""),
  );

  const run = () => {
    const q = deaccent(String($("#gr-in").val() ?? ""));
    const g = String($("#gr-group").val() ?? "");
    let n = 0;
    $("#gr-tbl tbody tr").each((_, tr) => {
      const hit =
        (!q || deaccent(tr.dataset.k).includes(q)) && (!g || tr.dataset.g === g);
      tr.hidden = !hit;
      if (hit) n += 1;
    });
    $("#gr-count").text(n ? `${n} 筆` : "（這馬無半筆）");
  };
  $("#gr-in").on("input", run);
  $("#gr-group").on("change", run);
  run();

  $("#gr-snips").html(
    snippets
      .map(
        (s) =>
          `<li><a href="${s.url}" target="_blank" rel="noopener">${esc(s.title)}</a>` +
          `<span class="hint">　${s.date}</span></li>`,
      )
      .join(""),
  );
}

export function initGrammar() {
  initNotes(); // 各自 catch：一篇失敗嘛袂拖累另外一篇
  initIndex();
}
