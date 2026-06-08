from pathlib import Path
import gzip

from shared.python.compression_registry import iter_text_lines


def test_iter_text_lines_reads_gzip(tmp_path: Path):
    path = tmp_path / "sample.txt.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write("a\n")
        handle.write("b\n")

    assert list(iter_text_lines(path)) == ["a\n", "b\n"]
