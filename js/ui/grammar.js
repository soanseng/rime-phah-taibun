// 文法分頁：TGGL（臺灣台語語料庫應用檢索系統，國家教育研究院）語法點索引。
// 依原站授權條款（語料不得移轉第三人），本頁只收書目中繼資料
// （編號／語法點／臺羅／群組），語法說明佮例句一律連回原系統查閱；謹此致謝教育部。

const deaccent = (s) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();

const esc = (s) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");

export async function initGrammar() {
  let data;
  try {
    data = await (await fetch("./data-public/grammars.json")).json();
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
