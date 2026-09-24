"""Build all Rime dictionary files from downloaded data sources.

Orchestrates the full preprocessing pipeline:
1. Extract word frequencies + sentences from iCorpus corpus
1b. Extract per-identity frequencies from iCorpus parallel files
2. Extract word frequencies + sentences from Ungian corpus
2b. Extract word frequencies + sentences from 康軒 textbooks
2c. Extract word frequencies + sentences from 900例句
2d. Extract nmtl literary corpus sentences + frequencies
2e. Extract KipSutian example sentences
2f. Extract Khin-hoan POJ texts (with POJ→TL conversion)
3. Convert ChhoeTaigi CSVs → Rime dict.yaml (with corpus frequency boost).
   All corpus extraction runs BEFORE this step so a single fresh run
   carries every corpus into the dictionary weights — no dependency on
   stale TSVs from a previous run.
3b. Build and append Taigi input method dictionary supplement
3c. Append curated reading variants
4. Parse LKK rules → hanlo_rules.yaml
4b. Parse light-tone rules → lighttone_rules.json
4c. Parse MOE 700字 → moe700.yaml
5. Build Mandarin→Taiwanese mapping
6. Validate generated dictionary
7. Build light-tone entries from corpus frequencies + append
8. Build bigram phrases from all corpora + append
9. Enforce long-word-first weight invariant
10. Re-validate dictionary (final artifact, with known-keys gate)
11. Generate wordlist + word-key snapshot

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

    # Pre-define output paths for corpus extractors (used in Steps 2-3, 7-8)
    nmtl_freq = data / "nmtl_freq.tsv"
    nmtl_sentences = data / "nmtl_sentences.txt"
    kipsutian_sent_freq = data / "kipsutian_sent_freq.tsv"
    kipsutian_sentences = data / "kipsutian_sentences.txt"
    pojbh_freq = data / "pojbh_freq.tsv"
    pojbh_sentences = data / "pojbh_sentences.txt"
    kok4hau7_freq = data / "kok4hau7_freq.tsv"
    kok4hau7_sentences = data / "kok4hau7_sentences.txt"
    leku900_freq = data / "900leku_freq.tsv"
    leku900_sentences = data / "900leku_sentences.txt"
    supplement_dir = data / "Taigi-Input-method-dictionary-supplement"
    supplement_entries = data / "dictionary_supplement_entries.tsv"
    supplement_report = data / "dictionary_supplement_report.tsv"
    # Curated 書面語 supplement; repo-root-relative because build_all runs
    # from the repo root (as do all child script invocations below).
    written_supplement = Path("scripts/data/written_supplement.tsv")

    lighttone_output = data / "lighttone_entries.tsv"
    # True only when Step 3 rebuilt the dictionary THIS run. Every tail
    # step that reads or append-writes the dict gates on it, so a failed
    # or skipped conversion can never layer appends onto the previous
    # build's stale artifact.
    dict_rebuilt = False

    # Step 1: Extract iCorpus frequencies + sentences
    icorpus_file = data / "icorpus_ka1_han3-ji7" / "語料" / "自動標人工改音標.txt"
    icorpus_freq = data / "icorpus_freq.tsv"
    icorpus_sentences = data / "icorpus_sentences.txt"
    if icorpus_file.exists():
        steps_ok &= run_step(
            "Extract iCorpus word frequencies",
            [
                python,
                "scripts/extract_icorpus_freq.py",
                "--input",
                str(icorpus_file),
                "--output",
                str(icorpus_freq),
                "--sentences",
                str(icorpus_sentences),
            ],
        )
    else:
        print(f"SKIP: iCorpus not found at {icorpus_file}")

    # Step 1b: Extract per-identity (han, TL) counts from iCorpus parallel files
    icorpus_han = data / "icorpus_ka1_han3-ji7" / "語料" / "自動標人工改漢字.txt"
    identity_freq = data / "identity_freq.tsv"
    identity_bigrams = data / "identity_bigrams.tsv"
    if icorpus_han.exists() and icorpus_file.exists():
        steps_ok &= run_step(
            "Extract iCorpus per-identity frequencies",
            [
                python,
                "scripts/extract_identity_freq.py",
                "--han",
                str(icorpus_han),
                "--tl",
                str(icorpus_file),
                "--output",
                str(identity_freq),
                "--bigram-output",
                str(identity_bigrams),
            ],
        )
    else:
        print(f"SKIP: iCorpus parallel hanzi file not found at {icorpus_han}")

    # Step 2: Extract Ungian frequencies + sentences
    ungian_dir = data / "Ungian_2009_KIPsupin"
    ungian_freq = data / "ungian_freq.tsv"
    ungian_sentences = data / "ungian_sentences.txt"
    if ungian_dir.exists():
        steps_ok &= run_step(
            "Extract Ungian literary corpus frequencies",
            [
                python,
                "scripts/extract_ungian_freq.py",
                "--input",
                str(ungian_dir),
                "--output",
                str(ungian_freq),
                "--sentences",
                str(ungian_sentences),
            ],
        )
    else:
        print(f"SKIP: Ungian data not found at {ungian_dir}")

    # Step 2b: Extract 康軒 textbook frequencies + sentences
    kok4hau7_dir = data / "kok4hau7-kho3pun2"
    if kok4hau7_dir.exists():
        steps_ok &= run_step(
            "Extract 康軒 textbook frequencies",
            [
                python,
                "scripts/extract_kok4hau7_freq.py",
                "--input",
                str(kok4hau7_dir),
                "--output",
                str(kok4hau7_freq),
                "--sentences",
                str(kok4hau7_sentences),
            ],
        )
    else:
        print(f"SKIP: 康軒 textbook data not found at {kok4hau7_dir}")

    # Step 2c: Extract 900例句 frequencies + sentences
    leku900_json = data / "Sin1pak8tshi7_2015_900-le7ku3" / "minnan900.json"
    if leku900_json.exists():
        steps_ok &= run_step(
            "Extract 常用900例句 frequencies",
            [
                python,
                "scripts/extract_900leku_freq.py",
                "--input",
                str(leku900_json),
                "--output",
                str(leku900_freq),
                "--sentences",
                str(leku900_sentences),
            ],
        )
    else:
        print(f"SKIP: 900例句 not found at {leku900_json}")

    # KipSutian CSV is nested: public/<date>/bunji/kautian.csv
    kipsutian_base = data / "KipSutianDataMirror" / "public"
    kipsutian_csv = None
    if kipsutian_base.exists():
        for candidate in sorted(kipsutian_base.iterdir(), reverse=True):
            csv_path = candidate / "bunji" / "kautian.csv"
            if csv_path.exists():
                kipsutian_csv = csv_path
                break

    # Step 2d: Extract nmtl literary corpus sentences + frequencies
    nmtl_dir = data / "nmtl_2006_dadwt"
    if nmtl_dir.exists():
        steps_ok &= run_step(
            "Extract nmtl literary corpus",
            [
                python,
                "scripts/extract_nmtl.py",
                "--input",
                str(nmtl_dir),
                "--output",
                str(nmtl_freq),
                "--sentences",
                str(nmtl_sentences),
            ],
        )
    else:
        print(f"SKIP: nmtl data not found at {nmtl_dir}")

    # Step 2e: Extract KipSutian example sentences
    if kipsutian_csv and kipsutian_csv.exists():
        steps_ok &= run_step(
            "Extract KipSutian example sentences",
            [
                python,
                "scripts/extract_kipsutian_sentences.py",
                "--input",
                str(kipsutian_csv),
                "--output",
                str(kipsutian_sent_freq),
                "--sentences",
                str(kipsutian_sentences),
            ],
        )

    # Step 2f: Extract Khin-hoan POJ texts (with POJ→TL conversion)
    pojbh_dir = data / "Khin-hoan_2010_pojbh"
    if pojbh_dir.exists():
        steps_ok &= run_step(
            "Extract Khin-hoan POJ texts (with POJ→TL conversion)",
            [
                python,
                "scripts/extract_pojbh.py",
                "--input",
                str(pojbh_dir),
                "--output",
                str(pojbh_freq),
                "--sentences",
                str(pojbh_sentences),
            ],
        )
    else:
        print(f"SKIP: Khin-hoan POJ data not found at {pojbh_dir}")

    # Step 3: Convert ChhoeTaigi → dict.yaml (with corpus frequency boost)
    chhoetaigi_dir = data / "ChhoeTaigiDatabase"
    if chhoetaigi_dir.exists():
        convert_cmd = [
            python,
            "scripts/convert_chhoetaigi.py",
            "--input",
            str(chhoetaigi_dir),
            "--output",
            str(out),
        ]
        # Attach extracted corpus frequency TSVs if available
        freq_files = [
            f
            for f in [
                icorpus_freq,
                ungian_freq,
                kok4hau7_freq,
                leku900_freq,
                nmtl_freq,
                kipsutian_sent_freq,
                pojbh_freq,
            ]
            if f.exists()
        ]
        if freq_files:
            convert_cmd.append("--corpus-freq")
            convert_cmd.extend(str(f) for f in freq_files)
        if identity_freq.exists():
            convert_cmd.extend(["--identity-freq", str(identity_freq)])
        if kipsutian_csv and kipsutian_csv.exists():
            convert_cmd.extend(["--kipsutian-csv", str(kipsutian_csv)])
        if run_step(
            "Convert ChhoeTaigi CSVs to Rime dictionary",
            convert_cmd,
        ):
            dict_rebuilt = True
        else:
            steps_ok = False
    else:
        print(f"SKIP: ChhoeTaigi not found at {chhoetaigi_dir}")

    # Step 3b: Build third-party dictionary supplement entries
    if supplement_dir.exists() and dict_rebuilt:
        supplement_cmd = [
            python,
            "scripts/build_dictionary_supplement.py",
            "--input",
            str(supplement_dir),
            "--output",
            str(supplement_entries),
            "--report",
            str(supplement_report),
        ]
        if written_supplement.exists():
            supplement_cmd.extend(["--extra-file", str(written_supplement)])
        steps_ok &= run_step(
            "Build Taigi input method dictionary supplement",
            supplement_cmd,
        )
        dict_yaml = out / "phah_taibun.dict.yaml"
        if dict_yaml.exists() and supplement_entries.exists() and supplement_entries.stat().st_size > 0:
            # The supplement curates words the core dictionaries miss; a
            # (text, code) row already in the freshly built dictionary is a
            # fatal duplicate-entry gate, so those rows are skipped here.
            existing: set[tuple[str, str]] = set()
            with open(dict_yaml, encoding="utf-8") as f:
                for line in f:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) >= 2:
                        existing.add((parts[0], parts[1]))
            appended = skipped = 0
            with open(supplement_entries, encoding="utf-8") as in_f, open(dict_yaml, "a", encoding="utf-8") as out_f:
                for line in in_f:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) >= 2 and (parts[0], parts[1]) in existing:
                        skipped += 1
                        continue
                    out_f.write(line)
                    appended += 1
            print(
                f"  Appended {appended} supplement entries ({skipped} duplicate rows skipped) from {supplement_entries}"
            )
            print(f"  Supplement report: {supplement_report}")
    else:
        print("SKIP: Dictionary supplement not run (source or dictionary build missing)")

    # Step 3c: Append curated reading variants (word, variant key) that
    # upstream sources only record under the canonical reading. Weights are
    # copied from the canonical entry so ordering stays source-driven.
    dict_yaml = out / "phah_taibun.dict.yaml"
    if dict_rebuilt and dict_yaml.exists():
        reading_variants = [
            # 教典 records 袂記得 as bē-kì--tit (tit); common writing also
            # uses tsit (e.g. funbiochampion 漢羅文章 "bē-kì-tsit").
            ("袂記得", "be7 ki3 tit4", "be7 ki3 tsit8"),
        ]
        appended = 0
        with open(dict_yaml, encoding="utf-8") as f:
            rows = {}
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 3:
                    rows[(parts[0], parts[1])] = int(parts[2])
        with open(dict_yaml, "a", encoding="utf-8") as f:
            for word, canon_key, variant_key in reading_variants:
                if (word, variant_key) in rows:
                    continue
                weight = rows.get((word, canon_key))
                if weight is None:
                    print(f"  WARNING: variant source missing: {word} {canon_key}")
                    continue
                f.write(f"{word}\t{variant_key}\t{weight}\n")
                appended += 1
        print(f"  Appended {appended} reading-variant entries")

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
            [
                python,
                "scripts/parse_lighttone.py",
                "--input",
                str(lighttone_csv),
                "--output",
                str(out / "lighttone_rules.json"),
            ],
        )
    else:
        print(f"SKIP: Light-tone CSV not found at {lighttone_csv}")

    # Step 4c: Parse MOE 700 recommended characters
    moe700_csv = data / "700iongji.csv"
    if moe700_csv.exists():
        steps_ok &= run_step(
            "Parse MOE 700字 → moe700.yaml",
            [python, "scripts/parse_moe700.py", "--input", str(moe700_csv), "--output", str(out / "moe700.yaml")],
        )
    else:
        print("SKIP: 700iongji.csv not found (run download_resources.sh)")

    # Step 5: Build Mandarin→Taiwanese mapping (hoabun_map.txt)
    if chhoetaigi_dir.exists():
        steps_ok &= run_step(
            "Build Mandarin→Taiwanese mapping (hoabun_map.txt)",
            [
                python,
                "scripts/build_hoabun_map.py",
                "--input",
                str(chhoetaigi_dir),
                "--output",
                str(out / "hoabun_map.txt"),
            ],
        )

    # Step 6: Validate
    dict_yaml = out / "phah_taibun.dict.yaml"
    if dict_rebuilt and dict_yaml.exists():
        steps_ok &= run_step(
            "Validate generated dictionary",
            [python, "scripts/validate_dict.py", str(dict_yaml)],
        )

    # Step 7: Build light-tone entries from corpus frequencies
    dict_yaml = out / "phah_taibun.dict.yaml"
    lighttone_json = out / "lighttone_rules.json"
    all_freq_files = [
        f
        for f in [
            icorpus_freq,
            ungian_freq,
            kok4hau7_freq,
            leku900_freq,
            nmtl_freq,
            kipsutian_sent_freq,
            pojbh_freq,
        ]
        if f.exists()
    ]
    if dict_rebuilt and dict_yaml.exists() and lighttone_json.exists() and all_freq_files:
        steps_ok &= run_step(
            "Build light-tone entries from corpus frequencies",
            [
                python,
                "scripts/build_lighttone_entries.py",
                "--dict",
                str(dict_yaml),
                "--rules",
                str(lighttone_json),
                "--corpus-freq",
            ]
            + [str(f) for f in all_freq_files]
            + ["--output", str(lighttone_output)],
        )

    # Step 8: Build bigram phrases from all corpora
    sentence_files = [
        f
        for f in [
            icorpus_sentences,
            ungian_sentences,
            kok4hau7_sentences,
            leku900_sentences,
            nmtl_sentences,
            kipsutian_sentences,
            pojbh_sentences,
        ]
        if f.exists()
    ]
    dict_yaml = out / "phah_taibun.dict.yaml"
    if sentence_files and dict_rebuilt and dict_yaml.exists():
        phrase_output = data / "new_phrases.txt"
        phrase_cmd = (
            [python, "scripts/build_phrases.py", "--dict", str(dict_yaml), "--sentences"]
            + [str(f) for f in sentence_files]
            + ["--output", str(phrase_output), "--min-count", "5"]
        )
        if identity_bigrams.exists():
            phrase_cmd.extend(["--identity-bigrams", str(identity_bigrams)])
        steps_ok &= run_step("Build bigram phrases from all corpora", phrase_cmd)
        # Append new phrases to dict.yaml
        if phrase_output.exists() and phrase_output.stat().st_size > 0:
            with open(dict_yaml, "a", encoding="utf-8") as out_f, open(phrase_output, encoding="utf-8") as in_f:
                out_f.write(in_f.read())
            print(f"  Appended phrases from {phrase_output}")
        # Append new light-tone entries to dict.yaml
        if lighttone_output.exists() and lighttone_output.stat().st_size > 0:
            with open(dict_yaml, "a", encoding="utf-8") as out_f, open(lighttone_output, encoding="utf-8") as in_f:
                out_f.write(in_f.read())
            print(f"  Appended light-tone entries from {lighttone_output}")

    # Step 9: Enforce long-word-first weight invariant (PLAN section 9-1A)
    if dict_rebuilt and dict_yaml.exists():
        try:
            from scripts.build_frequency import enforce_dict_file_invariant
        except ModuleNotFoundError:
            from build_frequency import enforce_dict_file_invariant
        raised = enforce_dict_file_invariant(dict_yaml)
        print(f"  Long-word invariant raised {raised} entries")

    # Step 10: Re-validate dictionary (final artifact, after all rewrites)
    if dict_rebuilt and dict_yaml.exists():
        steps_ok &= run_step(
            "Re-validate dictionary (with new phrases)",
            [
                python,
                "scripts/validate_dict.py",
                str(dict_yaml),
                "--known-keys",
                "tests/fixtures/known_keys.yaml",
            ],
        )

    # Step 11: Generate wordlist for whole-sentence romanization boundaries
    if dict_rebuilt and dict_yaml.exists():
        steps_ok &= run_step(
            "Generate wordlist for sentence word boundaries",
            [
                python,
                "scripts/build_wordlist.py",
                "--dict",
                str(dict_yaml),
                "--output",
                str(out / "phah_taibun.wordlist"),
            ],
        )
    # Step 11b: Snapshot the dictionary key set for release diffing (PLAN 9-2H)
    if dict_rebuilt and dict_yaml.exists():
        try:
            from scripts.build_frequency import write_word_keys
        except ModuleNotFoundError:
            from build_frequency import write_word_keys
        snapshot = write_word_keys(dict_yaml, Path("dist"))
        print(f"  Word-key snapshot: {snapshot}")
    # Summary
    print(f"\n{'=' * 60}")
    if steps_ok and dict_rebuilt:
        print("  BUILD COMPLETE")
        print(f"  Output: {out}/")
        print("  Install: ./install.sh")
    else:
        if steps_ok:
            print("  BUILD FAILED — core dictionary was not rebuilt this run")
        else:
            print("  BUILD FAILED — check errors above")
        sys.exit(1)
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
