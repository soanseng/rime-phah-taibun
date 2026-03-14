"""Tests for reverse dictionary builder."""

from scripts.build_reverse_dict import build_reverse_entries, write_reverse_dict


class TestBuildReverseEntries:
    """Build Mandarin → Taiwanese reverse lookup entries."""

    def test_basic_reverse(self):
        entries = [
            {
                "hanlo": "食飯",
                "kip_input": "tsiah8-png7",
                "rime_key": "tsiah png",
                "hoabun": "吃飯",
                "source": "itaigi",
            },
        ]
        result = build_reverse_entries(entries)
        assert len(result) == 1
        assert result[0]["hoabun"] == "吃飯"
        assert result[0]["hanlo"] == "食飯"
        assert result[0]["kip_input"] == "tsiah8-png7"

    def test_multiple_taiwanese_for_one_mandarin(self):
        entries = [
            {
                "hanlo": "食飯",
                "kip_input": "tsiah8-png7",
                "rime_key": "tsiah png",
                "hoabun": "吃飯",
                "source": "itaigi",
            },
            {
                "hanlo": "食餐",
                "kip_input": "tsiah8-tshan1",
                "rime_key": "tsiah tshan",
                "hoabun": "吃飯",
                "source": "taihoa",
            },
        ]
        result = build_reverse_entries(entries)
        hoabun_entries = [r for r in result if r["hoabun"] == "吃飯"]
        assert len(hoabun_entries) == 2

    def test_skips_empty_hoabun(self):
        entries = [
            {"hanlo": "食飯", "kip_input": "tsiah8-png7", "rime_key": "tsiah png", "hoabun": "", "source": "itaigi"},
        ]
        result = build_reverse_entries(entries)
        assert len(result) == 0


class TestWriteReverseDict:
    """Write reverse lookup entries to Rime dict.yaml format."""

    def test_yaml_header(self, tmp_path):
        outfile = tmp_path / "reverse.dict.yaml"
        write_reverse_dict([], outfile)
        content = outfile.read_text()
        assert "name: phah_taibun_reverse" in content

    def test_entries_with_comment(self, tmp_path):
        entries = [
            {"hoabun": "吃飯", "hanlo": "食飯", "kip_input": "tsiah8-png7"},
        ]
        outfile = tmp_path / "reverse.dict.yaml"
        write_reverse_dict(entries, outfile)
        content = outfile.read_text()
        assert "吃飯" in content
        assert "食飯" in content
