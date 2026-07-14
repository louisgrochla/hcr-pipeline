"""Tests for hcr.ingest against tiny files written to tmp_path.

The contract under test: loading is format-tolerant, and a file that
cannot be parsed is logged and skipped — recorded in the inventory,
never fatal.
"""

import pandas as pd
import pytest

from hcr import ingest


@pytest.fixture
def raw_dir(tmp_path):
    pd.DataFrame({"Col A": [1, 2], "Col B": ["x", "y"]}).to_csv(
        tmp_path / "y1.csv", index=False
    )
    with pd.ExcelWriter(tmp_path / "y2.xlsx") as writer:
        pd.DataFrame({"C1": [1]}).to_excel(writer, sheet_name="Releases", index=False)
        pd.DataFrame({"Notes": ["n"]}).to_excel(writer, sheet_name="Notes", index=False)
    (tmp_path / "broken.xlsx").write_text("not really an xlsx")
    (tmp_path / "notes.txt").write_text("ignore me")
    return tmp_path


class TestLoadFile:
    def test_csv_single_frame(self, raw_dir):
        sheets = ingest.load_file(raw_dir / "y1.csv")
        assert list(sheets) == [None]
        assert list(sheets[None].columns) == ["Col A", "Col B"]

    def test_excel_all_sheets(self, raw_dir):
        sheets = ingest.load_file(raw_dir / "y2.xlsx")
        assert set(sheets) == {"Releases", "Notes"}

    def test_unsupported_suffix_raises(self, raw_dir):
        with pytest.raises(ValueError, match="Unsupported format"):
            ingest.load_file(raw_dir / "notes.txt")


class TestLoadAll:
    def test_unparseable_files_skipped_never_fatal(self, raw_dir, caplog):
        with caplog.at_level("WARNING"):
            loaded = ingest.load_all(raw_dir)
        assert set(loaded) == {"y1.csv", "y2.xlsx"}
        assert any("broken.xlsx" in r.message for r in caplog.records)


class TestInventory:
    def test_one_row_per_file_and_sheet_with_status(self, raw_dir):
        inv = ingest.inventory(raw_dir).set_index(["file", "sheet"])
        assert inv.loc[("y1.csv", None), "status"] == "ok"
        assert inv.loc[("y1.csv", None), "n_rows"] == 2
        assert inv.loc[("y2.xlsx", "Releases"), "columns"] == ["C1"]

    def test_failures_and_unsupported_recorded_not_dropped(self, raw_dir):
        inv = ingest.inventory(raw_dir).set_index("file")
        assert inv.loc["broken.xlsx", "status"].startswith("error:")
        assert inv.loc["notes.txt", "status"] == "unsupported"


class TestLoadSourceTables:
    def test_missing_raw_dir_yields_empty_not_fatal(self, tmp_path, caplog):
        with caplog.at_level("WARNING"):
            tables = ingest.load_source_tables(tmp_path / "nowhere")
        assert tables == []
        assert len(caplog.records) > 0
