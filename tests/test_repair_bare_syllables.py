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
