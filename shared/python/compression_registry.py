"""
STAR
Situation: Ingestion sources send structured, semi structured, and unstructured files in multiple compression formats.
Task: Keep file handling consistent without adding cloud specific logic.
Action: Implement extension based openers for plain text, gzip, bz2, and zip.
Result: Batch jobs can process several input formats with one utility and fewer edge case bugs.
"""

from __future__ import annotations

import bz2
import gzip
import io
import zipfile
from pathlib import Path
from typing import Iterator


def iter_text_lines(path: str | Path, encoding: str = "utf-8") -> Iterator[str]:
    """Yield text lines from plain, gzip, bz2, or zip files.

    Zip support reads the first non directory file in the archive. Production jobs can extend this
    to enforce one file per archive or process all files in deterministic order.
    """
    file_path = Path(path)
    suffixes = [suffix.lower() for suffix in file_path.suffixes]

    if suffixes and suffixes[-1] == ".gz":
        with gzip.open(file_path, "rt", encoding=encoding) as handle:
            yield from handle
        return

    if suffixes and suffixes[-1] == ".bz2":
        with bz2.open(file_path, "rt", encoding=encoding) as handle:
            yield from handle
        return

    if suffixes and suffixes[-1] == ".zip":
        with zipfile.ZipFile(file_path) as archive:
            names = sorted(name for name in archive.namelist() if not name.endswith("/"))
            if not names:
                return
            with archive.open(names[0]) as raw:
                text = io.TextIOWrapper(raw, encoding=encoding)
                yield from text
        return

    with file_path.open("r", encoding=encoding) as handle:
        yield from handle
