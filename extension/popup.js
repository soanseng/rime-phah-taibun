// 寫台文擴充功能 popup：干焦寫 storage.local；應用佇 controller（背景）做。
(function () {
'use strict';
const api = globalThis.browser ?? globalThis.chrome;
const $ = (id) => document.getElementById(id);

const KEYS = ['enabled', 'scheme', 'full_romanization', 'poj_mode'];
const DEFAULTS = { enabled: false, scheme: 'phah_taibun', full_romanization: 0, poj_mode: 0 };

async function refresh() {
  const s = { ...DEFAULTS, ...(await api.storage.local.get(KEYS)) };
  $('state').textContent = s.enabled ? '啟用中（拍台文）' : '關起來';
  const t = $('toggle');
  t.classList.toggle('on', s.enabled);
  t.setAttribute('aria-checked', String(s.enabled));
  $('scheme').value = s.scheme;
  $('full_romanization').value = String(s.full_romanization);
  $('poj_mode').value = String(s.poj_mode);
}

$('toggle').addEventListener('click', async () => {
  const { enabled } = await api.storage.local.get('enabled');
  await api.storage.local.set({ enabled: !enabled });
});
$('scheme').addEventListener('change', (ev) => api.storage.local.set({ scheme: ev.target.value }));
$('full_romanization').addEventListener('change', (ev) =>
  api.storage.local.set({ full_romanization: Number(ev.target.value) }));
$('poj_mode').addEventListener('change', (ev) =>
  api.storage.local.set({ poj_mode: Number(ev.target.value) }));

api.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && KEYS.some((k) => k in changes)) refresh();
});

api.commands?.getAll?.().then((cmds) => {
  const c = (cmds || []).find((x) => x.name === 'toggle-ime');
  if (c?.shortcut) $('shortcut').textContent = c.shortcut;
}).catch(() => {});

refresh().catch(console.error);
})();
