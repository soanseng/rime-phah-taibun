"""Tests for converting MOE KipSutian ODS data into flat CSV."""

from __future__ import annotations

import csv
import zipfile
from pathlib import Path

from scripts.convert_kautian_ods import convert_kautian_ods


def _make_ods(path: Path) -> None:
    content = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
  office:version="1.2">
  <office:body>
    <office:spreadsheet>
      <table:table table:name="詞目">
        <table:table-row>
          <table:table-cell office:value-type="string"><text:p>詞目id</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>詞目類型</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>漢字</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>羅馬字</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>分類</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>羅馬字音檔檔名</text:p></table:table-cell>
        </table:table-row>
        <table:table-row>
          <table:table-cell office:value-type="float" office:value="1"/>
          <table:table-cell office:value-type="string"><text:p>主詞目</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>一【替】</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>tsi̍t</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>數詞</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>1(1)</text:p></table:table-cell>
        </table:table-row>
      </table:table>
      <table:table table:name="義項">
        <table:table-row>
          <table:table-cell office:value-type="string"><text:p>詞目id</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>義項id</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>詞性</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>解說</text:p></table:table-cell>
        </table:table-row>
        <table:table-row>
          <table:table-cell office:value-type="float" office:value="1"/>
          <table:table-cell office:value-type="float" office:value="10"/>
          <table:table-cell office:value-type="string"><text:p>數詞</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>數目。</text:p></table:table-cell>
        </table:table-row>
      </table:table>
      <table:table table:name="例句">
        <table:table-row>
          <table:table-cell office:value-type="string"><text:p>詞目id</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>義項id</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>例句順序</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>漢字</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>羅馬字</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>華語</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>音檔檔名</text:p></table:table-cell>
        </table:table-row>
        <table:table-row>
          <table:table-cell office:value-type="float" office:value="1"/>
          <table:table-cell office:value-type="float" office:value="10"/>
          <table:table-cell office:value-type="float" office:value="1"/>
          <table:table-cell office:value-type="string"><text:p>一蕊花</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>tsi̍t luí hue</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>一朵花</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>1-1-1</text:p></table:table-cell>
        </table:table-row>
      </table:table>
      <table:table table:name="又唸作">
        <table:table-row>
          <table:table-cell office:value-type="string"><text:p>詞目id</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>漢字</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>羅馬字</text:p></table:table-cell>
        </table:table-row>
        <table:table-row>
          <table:table-cell office:value-type="float" office:value="1"/>
          <table:table-cell office:value-type="string"><text:p>一【替】</text:p></table:table-cell>
          <table:table-cell office:value-type="string"><text:p>tsit</text:p></table:table-cell>
        </table:table-row>
      </table:table>
    </office:spreadsheet>
  </office:body>
</office:document-content>
"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("content.xml", content)


def test_convert_kautian_ods_flattens_entries_definitions_and_relations(tmp_path):
    ods_path = tmp_path / "kautian.ods"
    csv_path = tmp_path / "kautian.csv"
    _make_ods(ods_path)

    count = convert_kautian_ods(ods_path, csv_path)

    with csv_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert count == 1
    assert rows[0]["詞目id"] == "1"
    assert rows[0]["漢字"] == "一(替)"
    assert rows[0]["羅馬字"] == "tsi̍t"
    assert rows[0]["解說"] == "1. (數詞) 數目。"
    assert rows[0]["例句"] == "1. 一蕊花 (tsi̍t luí hue)"
    assert rows[0]["例句-華語"] == "1. 一朵花"
    assert rows[0]["例句-音檔"] == "1. 1-1-1"
    assert '"羅馬字": "tsit"' in rows[0]["又唸作"]
