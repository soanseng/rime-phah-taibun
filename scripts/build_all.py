"""Build all Rime dictionary files from downloaded data sources.

Orchestrates the full preprocessing pipeline:
1. Extract word frequencies + sentences from iCorpus corpus
2. Extract word frequencies + sentences from Ungian corpus
3. Convert ChhoeTaigi CSVs → Rime dict.yaml (with corpus frequency boost)
4. Parse LKK rules → hanlo_rules.yaml
4b. Parse light-tone rules → lighttone_rules.json
5. Build reverse dictionary (KipSutian or MOE fallback)
6. Validate generated dictionary
7. Extract nmtl literary corpus sentences + frequencies
8. Extract KipSutian example sentences
9. Extract Khin-hoan POJ texts (with POJ→TL conversion)
10. Build bigram phrases from all corpora
11. Re-validate dictionary (with new phrases)

Usage:
    uv run python scripts/build_all.py
    uv run python scripts/build_all.py --data-dir /path/to/data --output-dir /path/to/schema
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_step(description: str, cmd: list[str]) -> bool:
    """Run a pipeline step, printing status."""
    print(f"\n{'=' * 60}")
    print(f"  {description}")
    print(f"{'=' * 60}")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"  FAILED: {description}")
        return False
    return True


def main(argv: list[str] | None = None) -> None:
    """Run the full build pipeline."""
    parser = argparse.ArgumentParser(description="Build all Rime dictionary files")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Path to downloaded data directory (default: data/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("schema"),
        help="Output directory for generated files (default: schema/)",
    )
    args = parser.parse_args(argv)

    data = args.data_dir
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    python = sys.executable
    steps_ok = True

    # Pre-define output paths for corpus extractors (used in Steps 3 and 7-10)
    nmtl_freq = data / "nmtl_freq.tsv"
    nmtl_sentences = data / "nmtl_sentences.txt"
    kipsutian_sent_freq = data / "kipsutian_sent_freq.tsv"
    kipsutian_sentences = data / "kipsutian_sentences.txt"
    pojbh_freq = data / "pojbh_freq.tsv"
    pojbh_sentences = data / "pojbh_sentences.txt"

    # Step 1: Extract iCorpus frequencies + sentences
    icorpus_file = data / "icorpus_ka1_han3-ji7" / "語料" / "自動標人工改音標.txt"
    icorpus_freq = data / "icorpus_freq.tsv"
    icorpus_sentences = data / "icorpus_sentences.txt"
    if icorpus_file.exists():
        steps_ok &= run_step(
            "Extract iCorpus word frequencies",
            [python, "scripts/extract_icorpus_freq.py", "--input", str(icorpus_file),
             "--output", str(icorpus_freq), "--sentences", str(icorpus_sentences)],
        )
    else:
        print(f"SKIP: iCorpus not found at {icorpus_file}")

    # Step 2: Extract Ungian frequencies + sentences
    ungian_dir = data / "Ungian_2009_KIPsupin"
    ungian_freq = data / "ungian_freq.tsv"
    ungian_sentences = data / "ungian_sentences.txt"
    if ungian_dir.exists():
        steps_ok &= run_step(
            "Extract Ungian literary corpus frequencies",
            [python, "scripts/extract_ungian_freq.py", "--input", str(ungian_dir),
             "--output", str(ungian_freq), "--sentences", str(ungian_sentences)],
        )
    else:
        print(f"SKIP: Ungian data not found at {ungian_dir}")

    # Step 3: Convert ChhoeTaigi → dict.yaml (with corpus frequency boost)
    chhoetaigi_dir = data / "ChhoeTaigiDatabase"
    if chhoetaigi_dir.exists():
        convert_cmd = [python, "scripts/convert_chhoetaigi.py", "--input", str(chhoetaigi_dir), "--output", str(out)]
        # Attach extracted corpus frequency TSVs if available
        freq_files = [f for f in [icorpus_freq, ungian_freq, nmtl_freq, kipsutian_sent_freq, pojbh_freq] if f.exists()]
        if freq_files:
            convert_cmd.append("--corpus-freq")
            convert_cmd.extend(str(f) for f in freq_files)
        steps_ok &= run_step(
            "Convert ChhoeTaigi CSVs to Rime dictionary",
            convert_cmd,
        )
    else:
        print(f"SKIP: ChhoeTaigi not found at {chhoetaigi_dir}")

    # Step 4: Parse LKK rules
    lkk_csv = data / "lkk_yongji.csv"
    if lkk_csv.exists():
        steps_ok &= run_step(
            "Parse LKK rules → hanlo_rules.yaml",
            [python, "scripts/parse_lkk_rules.py", "--input", str(lkk_csv), "--output", str(out / "hanlo_rules.yaml")],
        )
    else:
        print(f"SKIP: LKK CSV not found at {lkk_csv}")

    # Step 4b: Parse light-tone rules
    lighttone_csv = data / "khin1siann1-hun1sik4" / "輕聲詞資料" / "全部輕聲詞.csv"
    if lighttone_csv.exists():
        steps_ok &= run_step(
            "Parse light-tone rules → lighttone_rules.json",
            [python, "scripts/parse_lighttone.py", "--input", str(lighttone_csv), "--output", str(out / "lighttone_rules.json")],
        )
    else:
        print(f"SKIP: Light-tone CSV not found at {lighttone_csv}")

    # Step 5: Build reverse dictionary (prefer KipSutian 65K, fallback to MOE 24K)
    # KipSutian CSV is nested: public/<date>/bunji/kautian.csv
    kipsutian_base = data / "KipSutianDataMirror" / "public"
    kipsutian_csv = None
    if kipsutian_base.exists():
        for candidate in sorted(kipsutian_base.iterdir(), reverse=True):
            csv_path = candidate / "bunji" / "kautian.csv"
            if csv_path.exists():
                kipsutian_csv = csv_path
                break
    moe_dir = data / "moedict-data-twblg" / "uni"
    reverse_output = out / "phah_taibun_reverse.dict.yaml"

    if kipsutian_csv and kipsutian_csv.exists():
        steps_ok &= run_step(
            "Build KipSutian reverse dictionary (65K entries)",
            [python, "scripts/build_kipsutian_reverse.py", "--input", str(kipsutian_csv), "--output", str(reverse_output)],
        )
    elif moe_dir.exists():
        steps_ok &= run_step(
            "Build MOE reverse dictionary (24K entries, fallback)",
            [python, "scripts/build_moe_reverse.py", "--input", str(moe_dir), "--output", str(reverse_output)],
        )
    else:
        print("SKIP: No reverse dict source found")

    # Step 6: Validate
    dict_yaml = out / "phah_taibun.dict.yaml"
    if dict_yaml.exists():
        steps_ok &= run_step(
            "Validate generated dictionary",
            [python, "scripts/validate_dict.py", str(dict_yaml)],
        )

    # Step 7: Extract nmtl literary corpus sentences + frequencies
    nmtl_dir = data / "nmtl_2006_dadwt"
    if nmtl_dir.exists():
        steps_ok &= run_step(
            "Extract nmtl literary corpus",
            [python, "scripts/extract_nmtl.py", "--input", str(nmtl_dir),
             "--output", str(nmtl_freq), "--sentences", str(nmtl_sentences)],
        )
    else:
        print(f"SKIP: nmtl data not found at {nmtl_dir}")

    # Step 8: Extract KipSutian example sentences
    if kipsutian_csv and kipsutian_csv.exists():
        steps_ok &= run_step(
            "Extract KipSutian example sentences",
            [python, "scripts/extract_kipsutian_sentences.py", "--input", str(kipsutian_csv),
             "--output", str(kipsutian_sent_freq), "--sentences", str(kipsutian_sentences)],
        )

    # Step 9: Extract Khin-hoan POJ texts (with POJ→TL conversion)
    pojbh_dir = data / "Khin-hoan_2010_pojbh"
    if pojbh_dir.exists():
        steps_ok &= run_step(
            "Extract Khin-hoan POJ texts (with POJ→TL conversion)",
            [python, "scripts/extract_pojbh.py", "--input", str(pojbh_dir),
             "--output", str(pojbh_freq), "--sentences", str(pojbh_sentences)],
        )
    else:
        print(f"SKIP: Khin-hoan POJ data not found at {pojbh_dir}")

    # Step 10: Build bigram phrases from all corpora
    sentence_files = [f for f in [
        icorpus_sentences, ungian_sentences, nmtl_sentences,
        kipsutian_sentences, pojbh_sentences,
    ] if f.exists()]
    dict_yaml = out / "phah_taibun.dict.yaml"
    if sentence_files and dict_yaml.exists():
        phrase_output = data / "new_phrases.txt"
        steps_ok &= run_step(
            "Build bigram phrases from all corpora",
            [python, "scripts/build_phrases.py",
             "--dict", str(dict_yaml),
             "--sentences"] + [str(f) for f in sentence_files] +
            ["--output", str(phrase_output), "--min-count", "5"],
        )
        # Append new phrases to dict.yaml
        if phrase_output.exists() and phrase_output.stat().st_size > 0:
            with open(dict_yaml, "a", encoding="utf-8") as out_f:
                with open(phrase_output, encoding="utf-8") as in_f:
                    out_f.write(in_f.read())
            print(f"  Appended phrases from {phrase_output}")

    # Step 11: Re-validate dictionary (with new phrases)
    if dict_yaml.exists():
        steps_ok &= run_step(
            "Re-validate dictionary (with new phrases)",
            [python, "scripts/validate_dict.py", str(dict_yaml)],
        )

    # Summary
    print(f"\n{'=' * 60}")
    if steps_ok:
        print("  BUILD COMPLETE")
        print(f"  Output: {out}/")
        print("  Install: ./install.sh")
    else:
        print("  BUILD FAILED — check errors above")
        sys.exit(1)
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
