"""Tests for the bare-syllable dict repair logic.

Bare syllables in codes (e.g. `khi3 ah`) create exact prism edges that
shadow the abbrev edges digitless lookup relies on; the repair appends a
tone digit ONLY from character-level evidence in the same dictionary and
must preserve the double-space `--` boundary encoding.
"""

from __future__ import annotations

from pathlib import Path

from scripts.repair_bare_syllables import build_attestation, repair


def test_majority_tone_wins_within_same_base():
    entries = [
        ["嚇呢", "hann1 nih4", "100"],
        ["欲相拍呢", "beh4 sio1 phah4 nih4", "100"],
        ["稀有呢", "hi1 siu1 nih8", "100"],
    ]
    att = build_attestation(entries)
    assert att["呢"]["nih"] == "nih4"


def test_construction_evidence_overrides_word_final():
    entries = [
        ["唯--啊", "hann5 ah4", "100"],
        ["好啊", "ho2 a1", "100"],
        ["去--啊", "khi3 ah", "100"],
    ]
    att = build_attestation(entries)
    assert att["啊"]["ah"] == "ah4"
    out, repaired, dropped = repair(entries, att)
    assert repaired == 1 and not dropped
    assert out[-1] == "去--啊\tkhi3 ah4\t100"


def test_double_space_boundary_preserved():
    """The double space encodes the `--` light-tone boundary (kip_to_rime_key)."""
    entries = [
        ["去--啊", "khi3  ah", "1768"],
        ["唯--啊", "hann5  ah4", "100"],
    ]
    att = build_attestation(entries)
    out, repaired, dropped = repair(entries, att)
    assert repaired == 1 and not dropped
    assert out[0] == "去--啊\tkhi3  ah4\t1768"


def test_repaired_key_dedupes_against_existing_toned_twin():
    """補調後撞上既有帶調同鍵的條目要 dedupe, 不得產生重複(validate_dict fatal)."""
    entries = [
        ["免--得", "bian2  tit4", "2738"],
        ["免--得", "bian2  tit", "1461"],
        ["唯--啊", "hann5  ah4", "100"],
    ]
    att = build_attestation(entries)
    out, repaired, dropped = repair(entries, att)
    assert repaired == 0  # the bare twin collapses into the existing toned key
    assert dropped == []
    assert out == ["免--得\tbian2  tit4\t2738", "唯--啊\thann5  ah4\t100"]


def test_dedupe_keeps_max_weight_independent_of_order():
    """同鍵重複保留最大權重, 與輸入順序無關."""
    hi = ["免--得", "bian2  tit4", "2738"]
    lo = ["免--得", "bian2  tit", "1461"]
    att = build_attestation([hi])
    for order in ([lo, hi], [hi, lo]):
        out, _repaired, dropped = repair(order, att)
        assert out == ["免--得\tbian2  tit4\t2738"], (order, out)
        assert not dropped


def test_unevidenced_bare_syllable_dropped_not_guessed():
    entries = [
        ["起--哩", "khi2 lih", "100"],
        ["英哩", "ing1 li2", "100"],
    ]
    att = build_attestation(entries)
    out, repaired, dropped = repair(entries, att)
    assert repaired == 0
    assert dropped == [("起--哩", "khi2 lih")]
    assert out == ["英哩\ting1 li2\t100"]


def test_toned_entries_untouched(tmp_path: Path):
    entries = [
        ["食飯", "tsiah8 png7", "500"],
        ["去--啊", "khi3  ah", "1768"],
        ["唯--啊", "hann5  ah4", "100"],
    ]
    att = build_attestation(entries)
    out, repaired, dropped = repair(entries, att)
    assert repaired == 1 and not dropped
    assert out[0] == "食飯\ttsiah8 png7\t500"
