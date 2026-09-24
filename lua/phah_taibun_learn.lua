-- phah_taibun_learn.lua
-- 學習濾波器：記錄使用者選過的（詞, 讀音），提升其候選排序。
--
-- 儲存：Rime 使用者目錄下單一 TSV（phah_taibun_learning.tsv），每行
--   <identity>\t<commits> <last_epoch>
-- identity = data.word_identity(text, reading)，本身含一個 tab
-- （漢羅\t讀音），所以兩個數值欄位用空白連接，解析用
--   line:match('^(.-)\t(%d+) (%d+)$')
-- （lazy match 對到最後一個 tab）；格式不良的行直接略過。
--
-- 排序加權（W3 學習設計）：
--   B = B_MAX * min(1, commits / C_SAT) * 0.5 ^ (age_days / H_DAYS)
-- 選 40 次飽和於 B_MAX；每 30 天減半。os.time 無法使用時（沙箱 feature
-- detect）時間戳記 0，0 代表停用衰減；時間戳在未來（時鐘偏移）箝制為 0 歲。
--
-- 過濾：兩段式重排——有學習紀錄的候選依 (quality or 0) + B 排在前面，
-- 其餘照原順序在後。store 空 = 完全原樣通過。

local M = {}

-- === 常數（調校集中在這裡） ===
local B_MAX = 2.0                       -- 飽和後的最大加權
local C_SAT = 40                        -- 達到飽和的選用次數
local H_DAYS = 30                       -- 半衰期（天）
local STORE_FILE = "phah_taibun_learning.tsv"
local DAY_SECONDS = 86400

-- Load shared data module (word_identity, extract_raw_code)
local data_mod = nil
do
  local ok, mod = pcall(require, "phah_taibun_data")
  if ok and mod then
    data_mod = mod
  end
end

local _store = nil      -- identity -> { commits, last }；nil = 尚未載入
local _disabled = false -- 無使用者目錄／無法寫入時停用學習（不影響過濾）

local function user_data_dir()
  if rime_api and rime_api.get_user_data_dir then
    local ok, dir = pcall(rime_api.get_user_data_dir)
    if ok and type(dir) == "string" and dir ~= "" then
      return dir
    end
  end
  return nil
end

local function now_epoch()
  -- Feature-detect：沙箱裡可能沒有 os.time；回 0 代表停用衰減
  if os and type(os.time) == "function" then
    local ok, t = pcall(os.time)
    if ok and type(t) == "number" then
      return t
    end
  end
  return 0
end

local function store_path()
  local dir = user_data_dir()
  if not dir then
    return nil
  end
  return dir .. "/" .. STORE_FILE
end

local function ensure_loaded()
  if _store or _disabled then
    return
  end
  _store = {}
  local path = store_path()
  if not path then
    _disabled = true
    return
  end
  local f = io.open(path, "r")
  if not f then
    return -- 首次使用：空 store
  end
  for line in f:lines() do
    local identity, commits, last = line:match("^(.-)\t(%d+) (%d+)$")
    if identity then
      _store[identity] = { commits = tonumber(commits), last = tonumber(last) }
    end
    -- 格式不良的行：略過
  end
  f:close()
end

local function persist()
  local path = store_path()
  if not path then
    return
  end
  local f = io.open(path, "w")
  if not f then
    _disabled = true
    return
  end
  for identity, e in pairs(_store) do
    f:write(string.format("%s\t%d %d\n", identity, e.commits, e.last))
  end
  f:close()
end

local function extract_raw_code(cand)
  if data_mod and data_mod.extract_raw_code then
    return data_mod.extract_raw_code(cand)
  end
  return nil
end

-- 使用者選了一個候選：commits +1、更新時間戳並寫回 store。
-- 原文候選與無讀音候選（句組、符號、說明等）不學習。
function M.observe(cand)
  ensure_loaded()
  if _disabled or not _store then
    return
  end
  if not cand or cand.type == "origin" then
    return
  end
  local code = extract_raw_code(cand)
  if not code or code == "" then
    return
  end
  if not (data_mod and data_mod.word_identity) then
    return
  end
  local identity = data_mod.word_identity(cand.text, code)
  local e = _store[identity]
  if not e then
    e = { commits = 0, last = 0 }
    _store[identity] = e
  end
  e.commits = e.commits + 1
  e.last = now_epoch()
  persist()
end

-- 詞的排序加權（saturation + wall-clock decay）
function M.boost(commits, last)
  commits = tonumber(commits) or 0
  local saturation = math.min(1, commits / C_SAT)
  local decay = 1
  last = tonumber(last) or 0
  if last > 0 then
    local now = now_epoch()
    if now > 0 then
      local age = now - last
      if age < 0 then
        age = 0 -- 時鐘偏移：箝制為 0 歲
      end
      decay = 0.5 ^ (age / (DAY_SECONDS * H_DAYS))
    end
  end
  return B_MAX * saturation * decay
end

-- 查詢一個詞的學習紀錄（無紀錄回 nil）
function M.get(identity)
  ensure_loaded()
  if not _store then
    return nil
  end
  return _store[identity]
end

function M.init(env)
  ensure_loaded()
end

-- 有界位移：字典順序為主，已學習的候選往前挪至多 3 格（格數 =
-- floor(B)，飽和時 B=2.0 → 2 格…上限 3）。詞典候選的 quality 實務上
-- 全是 nil，任何加法排序都會退化成「學習全置頂」而淹沒候選區；位移
-- 保證單次學習只往前一格、不會越過多個更常見的詞。
function M.func(input, env)
  ensure_loaded()
  if _disabled or not _store or next(_store) == nil then
    for cand in input:iter() do
      yield(cand)
    end
    return
  end

  local all = {}
  local pos = 0
  for cand in input:iter() do
    pos = pos + 1
    local identity = nil
    local code = extract_raw_code(cand)
    if code and data_mod and data_mod.word_identity then
      identity = data_mod.word_identity(cand.text, code)
    end
    local e = identity and _store[identity] or nil
    local nudge = 0
    if e then
      local b = M.boost(e.commits, e.last)
      nudge = math.min(3, math.floor(b))
    end
    table.insert(all, {
      cand = cand,
      pos = pos,
      slot = pos - nudge,
    })
  end

  table.sort(all, function(a, b)
    if a.slot ~= b.slot then
      return a.slot < b.slot
    end
    return a.pos < b.pos -- 同 slot：保持原有相對順序
  end)

  for _, item in ipairs(all) do
    yield(item.cand)
  end
end

return M
