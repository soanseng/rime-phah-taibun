// 擴充功能按鍵邏輯（extension/keys.js）的純函式測試。用 node:vm 載入 classic script。
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const src = readFileSync(path.join(here, "../../extension/keys.js"), "utf8");
const ctx = vm.createContext({ console });
vm.runInContext(src, ctx);
const K = ctx.PhahKeys;

test("keyName: 佮 docs/try/index.html 的映射一致", () => {
  assert.equal(K.keyName({ key: "a" }), "a");
  assert.equal(K.keyName({ key: "5" }), "5");
  assert.equal(K.keyName({ key: "Backspace", shiftKey: true }), "{Shift+BackSpace}");
  assert.equal(K.keyName({ key: "Enter", ctrlKey: true }), "{Control+Return}");
  assert.equal(K.keyName({ key: "Backspace", ctrlKey: true }), "{Control+BackSpace}");
  assert.equal(K.keyName({ key: "c", ctrlKey: true }), null);
  assert.equal(K.keyName({ key: "a", metaKey: true }), null);
  assert.equal(K.keyName({ key: "a", altKey: true }), null);
  assert.equal(K.keyName({ key: "," }), "{comma}");
  assert.equal(K.keyName({ key: " " }), "{space}");
  assert.equal(K.keyName({ key: "Tab" }), "{Tab}");
  assert.equal(K.keyName({ key: "ArrowDown" }), "{Down}");
  assert.equal(K.keyName({ key: "Escape" }), "{Escape}");
});

test("isPrintable: 單字元且無修飾鍵", () => {
  assert.equal(K.isPrintable({ key: "a" }), true);
  assert.equal(K.isPrintable({ key: " " }), true);
  assert.equal(K.isPrintable({ key: "," }), true);
  assert.equal(K.isPrintable({ key: "Enter" }), false);
  assert.equal(K.isPrintable({ key: "a", ctrlKey: true }), false);
  assert.equal(K.isPrintable({ key: "a", metaKey: true }), false);
  assert.equal(K.isPrintable({ key: "a", altKey: true }), false);
});

test("shouldIntercept: 歇睏時干焦攔會印的字（標點愛經過引擎出全形）", () => {
  assert.equal(K.shouldIntercept({ key: "a" }, false), true);
  assert.equal(K.shouldIntercept({ key: "," }, false), true);
  assert.equal(K.shouldIntercept({ key: " " }, false), true);
  assert.equal(K.shouldIntercept({ key: "5" }, false), true);
  // 歇睏時非印字鍵留予網頁：Enter 送表單、Backspace 刪字、Tab 移焦點
  assert.equal(K.shouldIntercept({ key: "Backspace" }, false), false);
  assert.equal(K.shouldIntercept({ key: "Enter" }, false), false);
  assert.equal(K.shouldIntercept({ key: "Tab" }, false), false);
  assert.equal(K.shouldIntercept({ key: "ArrowLeft" }, false), false);
  assert.equal(K.shouldIntercept({ key: "F4" }, false), false);
});

test("shouldIntercept: 組字中所有引擎鍵攏愛攔", () => {
  assert.equal(K.shouldIntercept({ key: "Backspace" }, true), true);
  assert.equal(K.shouldIntercept({ key: "Escape" }, true), true);
  assert.equal(K.shouldIntercept({ key: "Tab" }, true), true);
  assert.equal(K.shouldIntercept({ key: "Enter" }, true), true);
  assert.equal(K.shouldIntercept({ key: "ArrowLeft" }, true), true);
  assert.equal(K.shouldIntercept({ key: "a" }, true), true);
});

test("shouldIntercept: IME 家己的組字佮無映射的鍵毋免插", () => {
  assert.equal(K.shouldIntercept({ key: "a", isComposing: true }, false), false);
  assert.equal(K.shouldIntercept({ key: "a", isComposing: true }, true), false);
  assert.equal(K.shouldIntercept({ key: "F13" }, true), false); // 無佇 SPECIAL 映射內
  assert.equal(K.shouldIntercept({ key: "c", ctrlKey: true }, true), false);
});
