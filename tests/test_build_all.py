"""Behavioral contracts for the build_all.py orchestration pipeline.

These tests pin three production properties of the full dictionary build:

1. A fresh data/ directory must feed ALL wired corpus frequencies into the
   dictionary conversion step on a SINGLE run — corpus extraction steps
   must run BEFORE the ChhoeTaigi conversion that consumes their TSVs.
   (Before the fix, nmtl/KipSutian/POJBH frequencies only reached the main
   dictionary on the second run, via stale TSVs left in data/.)
2. A run whose light-tone rules source is missing must degrade gracefully
   when corpus sentences exist — no NameError from a conditionally bound
   output path.
3. A failed (or skipped) dictionary conversion must never layer appends
   onto a previous build's dictionary, and must end BUILD FAILED with a
   non-zero exit code — never a false BUILD COMPLETE.

The pipeline is driven with a fake subprocess runner that simulates each
child script's output artifacts, so ordering and wiring are asserted
without executing the real (multi-minute) extraction steps.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.build_all import main

MINIMAL_DICT = (
    "---\n"
    "name: phah_taibun\n"
    'version: "0.9.0"\n'
    "sort: by_weight\n"
    "use_preset_vocabulary: false\n"
    "...\n"
    "食\ttsiah8\t640\n"
    "食飯\ttsiah8 png7\t1536\n"
)

FREQ_TSV = "e5\t10\ngua2\t5\n"
SENTENCE = "gua2 tsiah8 png7\n"


def _value_after(cmd: list[str], flag: str) -> str | None:
    try:
        return cmd[cmd.index(flag) + 1]
    except (ValueError, IndexError):
        return None


class FakeRunner:
    """Record every child command; simulate success outputs (or failures)."""

    def __init__(self, fail_scripts: frozenset[str] = frozenset()):
        self.commands: list[list[str]] = []
        self.fail_scripts = fail_scripts

    def __call__(self, cmd, capture_output=False):
        self.commands.append(list(cmd))
        script = Path(cmd[1]).name if len(cmd) > 1 else ""
        if script in self.fail_scripts:
            return SimpleNamespace(returncode=1)

        freq = _value_after(cmd, "--output")
        sentences = _value_after(cmd, "--sentences")
        if freq and script.startswith("extract_"):
            Path(freq).write_text(FREQ_TSV, encoding="utf-8")
            if sentences:
                Path(sentences).write_text(SENTENCE, encoding="utf-8")
        if script == "extract_identity_freq.py" and freq:
            Path(freq).write_text("我\tgua2\t5\n", encoding="utf-8")
        if script == "convert_chhoetaigi.py" and freq:
            # --output of convert_chhoetaigi is the output *directory*;
            # the dictionary lands inside it.
            (Path(freq) / "phah_taibun.dict.yaml").write_text(MINIMAL_DICT, encoding="utf-8")
        if script == "build_dictionary_supplement.py" and freq:
            Path(freq).write_text(
                "食\ttsiah8\t900\n新詞\tsin1 su5\t700\n一種\ttsit8 tsiong2\t700\n食\ttsiah8\t700\n",
                encoding="utf-8",
            )
            report = _value_after(cmd, "--report")
            if report:
                Path(report).write_text("", encoding="utf-8")
        if script == "build_phrases.py" and freq:
            Path(freq).write_text("食飯\ttsiah8 png7\t900\n", encoding="utf-8")
        if script == "build_lighttone_entries.py" and freq:
            # 食飯 tsiah8␣␣png7 duplicates a core row's identity under the
            # double-space light-tone key at an absurd weight: the final
            # in-process invariant pass must cap it below the plain parent
            # (repro of the shipped inversion tng2␣␣lai5=7108 > tng2 lai5=3386).
            Path(freq).write_text("阿\ta2\t300\n食飯\ttsiah8  png7\t9999\n", encoding="utf-8")
        if script == "parse_lkk_rules.py" and freq:
            Path(freq).write_text("rules: {}\n", encoding="utf-8")
        if script == "parse_lighttone.py" and freq:
            Path(freq).write_text("{}\n", encoding="utf-8")
        if script == "parse_moe700.py" and freq:
            Path(freq).write_text("字:\n", encoding="utf-8")
        if script == "build_hoabun_map.py" and freq:
            Path(freq).write_text("我\tgua2\n", encoding="utf-8")
        if script == "build_wordlist.py" and freq:
            Path(freq).write_text("食\ttsiah8\n", encoding="utf-8")
        if script == "parse_stti.py" and freq:
            Path(freq).write_text("110\t110\tit4 it4 khong3\n", encoding="utf-8")
        if script == "parse_placenames.py" and freq:
            Path(freq).write_text(
                "左營\t左營\ttso2 iann5\t700\n新地名\t新地名\tsin1 tua7\t650\n", encoding="utf-8"
            )
        return SimpleNamespace(returncode=0)

    def index_of(self, script_name: str) -> int:
        for i, cmd in enumerate(self.commands):
            if len(cmd) > 1 and Path(cmd[1]).name == script_name:
                return i
        raise AssertionError(f"{script_name} was never invoked")


def make_data_dir(root: Path, *, with_chhoetaigi: bool = True, with_lighttone: bool = True) -> Path:
    """Create a data/ tree whose every pipeline input exists as a marker."""
    data = root / "data"
    (data / "icorpus_ka1_han3-ji7" / "語料").mkdir(parents=True)
    (data / "icorpus_ka1_han3-ji7" / "語料" / "自動標人工改音標.txt").write_text("", encoding="utf-8")
    (data / "icorpus_ka1_han3-ji7" / "語料" / "自動標人工改漢字.txt").write_text("", encoding="utf-8")
    for d in [
        "Ungian_2009_KIPsupin",
        "kok4hau7-kho3pun2",
        "nmtl_2006_dadwt",
        "Khin-hoan_2010_pojbh",
    ]:
        (data / d).mkdir()
    (data / "Sin1pak8tshi7_2015_900-le7ku3").mkdir()
    (data / "Sin1pak8tshi7_2015_900-le7ku3" / "minnan900.json").write_text("[]", encoding="utf-8")
    kip = data / "KipSutianDataMirror" / "public" / "20260101" / "bunji"
    kip.mkdir(parents=True)
    (kip / "kautian.csv").write_text("漢字,羅馬字\n", encoding="utf-8")
    if with_chhoetaigi:
        (data / "ChhoeTaigiDatabase").mkdir()
    (data / "lkk_yongji.csv").write_text("字,音\n", encoding="utf-8")
    if with_lighttone:
        lt = data / "khin1siann1-hun1sik4" / "輕聲詞資料"
        lt.mkdir(parents=True)
        (lt / "全部輕聲詞.csv").write_text("詞,音\n", encoding="utf-8")
    (data / "700iongji.csv").write_text("字,音\n", encoding="utf-8")
    (data / "Taigi-Input-method-dictionary-supplement").mkdir()
    return data


@pytest.fixture()
def run_build(tmp_path, monkeypatch):
    """Run build_all.main against a fixture tree; return runner + paths."""

    def _run(data: Path, out: Path, fail_scripts: frozenset[str] = frozenset()):
        monkeypatch.chdir(tmp_path)  # keep dist/ snapshots inside tmp
        runner = FakeRunner(fail_scripts)
        monkeypatch.setattr(sys.modules["scripts.build_all"].subprocess, "run", runner)
        main(["--data-dir", str(data), "--output-dir", str(out)])
        return runner

    return _run


class TestCorpusOrdering:
    """D1: extraction must precede the conversion that consumes it."""

    def test_fresh_run_feeds_all_seven_corpora_into_conversion(self, run_build, tmp_path):
        data = make_data_dir(tmp_path)
        out = tmp_path / "schema"
        runner = run_build(data, out)

        convert_i = runner.index_of("convert_chhoetaigi.py")
        convert_cmd = runner.commands[convert_i]
        assert "--corpus-freq" in convert_cmd
        freq_args = convert_cmd[convert_cmd.index("--corpus-freq") + 1 :]
        attached: set[str] = set()
        for arg in freq_args:
            if arg.startswith("--"):
                break
            attached.add(Path(arg).name)
        assert attached == {
            "icorpus_freq.tsv",
            "ungian_freq.tsv",
            "kok4hau7_freq.tsv",
            "900leku_freq.tsv",
            "nmtl_freq.tsv",
            "kipsutian_sent_freq.tsv",
            "pojbh_freq.tsv",
        }

    def test_late_corpora_extract_before_conversion(self, run_build, tmp_path):
        """nmtl/KipSutian/POJBH extractors must precede convert_chhoetaigi."""
        data = make_data_dir(tmp_path)
        out = tmp_path / "schema"
        runner = run_build(data, out)

        convert_i = runner.index_of("convert_chhoetaigi.py")
        for extractor in [
            "extract_nmtl.py",
            "extract_kipsutian_sentences.py",
            "extract_pojbh.py",
        ]:
            assert runner.index_of(extractor) < convert_i, (
                f"{extractor} must run before convert_chhoetaigi.py on a fresh run"
            )


class TestDegradedRuns:
    """D2: missing light-tone rules must not crash the pipeline."""

    def test_missing_lighttone_rules_with_sentences_completes(self, run_build, tmp_path, capsys):
        data = make_data_dir(tmp_path, with_lighttone=False)
        out = tmp_path / "schema"
        run_build(data, out)  # must not raise NameError
        captured = capsys.readouterr().out
        assert "BUILD COMPLETE" in captured


class TestSupplementAppend:
    """Step 3b appends must never duplicate existing (text, code) rows.

    The supplement is editorial curation for words the core dictionaries
    miss; a (text, code) row already in the freshly built dictionary is a
    fatal validate_dict gate (duplicate entry), so the append must skip it.
    Rows sourced from written_supplement.tsv (weight 700) follow the same
    gate: a core duplicate is skipped, a unique word is appended at 700.
    """

    def test_supplement_rows_dedup_against_core_dict(self, run_build, tmp_path):
        data = make_data_dir(tmp_path)
        out = tmp_path / "schema"
        run_build(data, out)

        lines = (out / "phah_taibun.dict.yaml").read_text(encoding="utf-8").splitlines()
        tsiah = [ln for ln in lines if ln.split("\t")[:2] == ["食", "tsiah8"]]
        new_row = [ln for ln in lines if ln.startswith("新詞\t")]
        written_unique = [ln for ln in lines if ln.split("\t")[:2] == ["一種", "tsit8 tsiong2"]]
        assert len(tsiah) == 1, "supplement duplicate of a core row must be skipped"
        assert tsiah[0] == "食\ttsiah8\t640", "the freshly built core row wins"
        assert new_row == ["新詞\tsin1 su5\t700"]
        assert written_unique == ["一種\ttsit8 tsiong2\t700"]

    def test_step_3b_passes_written_supplement_extra_file(self, run_build, tmp_path):
        """Step 3b must wire scripts/data/written_supplement.tsv when it exists."""
        data = make_data_dir(tmp_path)
        written = tmp_path / "scripts" / "data" / "written_supplement.tsv"
        written.parent.mkdir(parents=True)
        written.write_text("一種\ttsit8 tsiong2\n", encoding="utf-8")
        out = tmp_path / "schema"
        runner = run_build(data, out)

        cmd = runner.commands[runner.index_of("build_dictionary_supplement.py")]
        extra = _value_after(cmd, "--extra-file")
        assert extra is not None, "build_all must pass --extra-file for the written supplement"
        assert Path(extra).name == "written_supplement.tsv"


class TestMoeSourcesAppend:
    """Step 3d parses MOE STTI/placenames and appends fresh TSVs only."""

    def make_moe_markers(self, data: Path) -> None:
        (data / "stti_ttg").mkdir()
        (data / "stti_ttg" / "ttg_20241219.ods").write_text("", encoding="utf-8")
        (data / "moe_placenames" / "odt").mkdir(parents=True)
        (data / "moe_placenames" / "odt" / "list.odt").write_text("", encoding="utf-8")

    def test_parses_and_appends_with_weight_column(self, run_build, tmp_path):
        data = make_data_dir(tmp_path)
        self.make_moe_markers(data)
        out = tmp_path / "schema"
        runner = run_build(data, out)

        stti_cmd = runner.commands[runner.index_of("parse_stti.py")]
        assert Path(_value_after(stti_cmd, "--output")).name == "stti_entries.tsv"
        placename_cmd = runner.commands[runner.index_of("parse_placenames.py")]
        assert Path(_value_after(placename_cmd, "--output")).name == "placename_entries.tsv"

        dict_text = (out / "phah_taibun.dict.yaml").read_text(encoding="utf-8")
        assert "110\tit4 it4 khong3\t600\n" in dict_text  # STTI default tier
        assert "左營\ttso2 iann5\t700\n" in dict_text  # placename primary weight
        assert "新地名\tsin1 tua7\t650\n" in dict_text  # placename secondary weight
        assert "新詞\tsin1 su5\t700\n" in dict_text  # supplement path untouched

        hoabun_cmd = runner.commands[runner.index_of("build_hoabun_map.py")]
        extras = {
            Path(hoabun_cmd[i + 1]).name for i, arg in enumerate(hoabun_cmd) if arg == "--extra-tsv"
        }
        assert extras == {"stti_entries.tsv", "placename_entries.tsv"}

    def test_failed_parse_leaves_stale_tsv_unconsumed(self, run_build, tmp_path):
        data = make_data_dir(tmp_path)
        (data / "moe_placenames" / "odt").mkdir(parents=True)
        (data / "moe_placenames" / "odt" / "list.odt").write_text("", encoding="utf-8")
        stale = data / "placename_entries.tsv"
        stale.write_text("舊地名\t舊地名\tku7 tua7\t700\n", encoding="utf-8")
        out = tmp_path / "schema"

        with pytest.raises(SystemExit):
            run_build(data, out, fail_scripts=frozenset({"parse_placenames.py"}))

        dict_text = (out / "phah_taibun.dict.yaml").read_text(encoding="utf-8")
        assert "舊地名" not in dict_text


class TestFailLoud:
    """D3: no dictionary rebuild ⇒ no appends to stale dict, exit non-zero."""

    def test_failed_conversion_leaves_stale_dict_untouched(self, run_build, tmp_path):
        data = make_data_dir(tmp_path)
        out = tmp_path / "schema"
        out.mkdir()
        stale = out / "phah_taibun.dict.yaml"
        stale.write_text(MINIMAL_DICT, encoding="utf-8")
        stale_bytes = stale.read_bytes()

        with pytest.raises(SystemExit) as exc:
            run_build(data, out, fail_scripts=frozenset({"convert_chhoetaigi.py"}))

        assert exc.value.code == 1
        assert stale.read_bytes() == stale_bytes, "appends must never layer onto a previous build's dictionary"

    def test_missing_chhoetaigi_fails_build(self, run_build, tmp_path, capsys):
        data = make_data_dir(tmp_path, with_chhoetaigi=False)
        out = tmp_path / "schema"

        with pytest.raises(SystemExit) as exc:
            run_build(data, out)

        assert exc.value.code == 1
        assert "BUILD FAILED" in capsys.readouterr().out


class TestLighttoneCap:
    """Step 9 (enforce_dict_file_invariant) must cap light-tone rows below parent.

    The fake light-tone TSV ships 食飯 tsiah8␣␣png7=9999, duplicating the
    core row 食飯 tsiah8 png7=1536 (re-appended at 900 by the phrase
    builder). The final in-process pass is the single cap authority, so
    the assembled dict must ship the LT row at most parent-100; without
    it the row stays 9999 — the shipped 轉來 tng2␣␣lai5=7108 > 3386
    inversion.
    """

    def test_appended_double_space_row_capped_below_parent(self, run_build, tmp_path):
        data = make_data_dir(tmp_path)
        out = tmp_path / "schema"
        run_build(data, out)

        lines = (out / "phah_taibun.dict.yaml").read_text(encoding="utf-8").splitlines()
        parents = [int(ln.split("\t")[2]) for ln in lines if ln.split("\t")[:2] == ["食飯", "tsiah8 png7"]]
        lt = [ln for ln in lines if ln.split("\t")[:2] == ["食飯", "tsiah8  png7"]]
        assert max(parents) == 1536, "core parent row must survive the pipeline"
        assert lt == ["食飯\ttsiah8  png7\t1436"], "LT row must sit at parent-100 after Step 9"
