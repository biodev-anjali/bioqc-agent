"""
FastQC ZIP parser service.

Parses fastqc_data.txt from a FastQC ZIP archive and extracts:
  - Basic Statistics: Total Sequences, Sequence Length, %GC
  - Module pass/warn/fail statuses for 4 key modules

FastQC ZIP canonical layout:
  <sample_name>_fastqc/
      fastqc_data.txt   <- authoritative source
      fastqc_report.html
      summary.txt
      Images/

We target fastqc_data.txt because it contains both statistics and
module-level statuses, unlike summary.txt which only has statuses.
"""

import zipfile
from dataclasses import dataclass
from pathlib import Path


class FastQCParseError(Exception):
    """Raised for any recoverable FastQC parsing failure."""


@dataclass(frozen=True)
class FastQCMetrics:
    total_sequences: int
    sequence_length: str          # string: FastQC may emit "35-150"
    gc_percent: float
    per_base_quality_status: str  # "pass" | "warn" | "fail" | "unknown"
    per_sequence_quality_status: str
    adapter_content_status: str
    overrepresented_sequences_status: str


_TARGET_MODULES: frozenset[str] = frozenset({
    "Per base sequence quality",
    "Per sequence quality scores",
    "Adapter Content",
    "Overrepresented sequences",
})


def _locate_fastqc_data(zf: zipfile.ZipFile) -> str:
    """
    Find fastqc_data.txt inside the ZIP.
    Handles canonical layout (<name>_fastqc/fastqc_data.txt) and flat ZIPs.
    """
    for name in zf.namelist():
        if name.endswith("fastqc_data.txt"):
            return name

    raise FastQCParseError(
        "fastqc_data.txt not found inside the ZIP archive. "
        "Please upload a FastQC output ZIP, not a raw FASTQ file."
    )


def _parse_content(content: str) -> FastQCMetrics:
    """
    Parse the text content of fastqc_data.txt into FastQCMetrics.

    Format:
      >>Module Name\\tstatus     module header
      #Column headers            skipped
      key\\tvalue                data row
      >>END_MODULE
    """
    total_sequences: int | None = None
    sequence_length: str | None = None
    gc_percent: float | None = None
    module_statuses: dict[str, str] = {}
    in_basic_stats = False

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith(">>"):
            if line == ">>END_MODULE":
                in_basic_stats = False
                continue
            parts = line[2:].split("\t", 1)
            module_name = parts[0].strip()
            status = parts[1].strip().lower() if len(parts) == 2 else "unknown"
            in_basic_stats = (module_name == "Basic Statistics")
            if module_name in _TARGET_MODULES:
                module_statuses[module_name] = status
            continue

        if line.startswith("#"):
            continue

        if in_basic_stats and "\t" in line:
            key, _, value = line.partition("\t")
            key = key.strip()
            value = value.strip()

            if key == "Total Sequences":
                try:
                    total_sequences = int(value.replace(",", ""))
                except ValueError:
                    raise FastQCParseError(
                        f"Cannot parse Total Sequences value: '{value}'"
                    )
            elif key == "Sequence length":
                sequence_length = value
            elif key == "%GC":
                try:
                    gc_percent = float(value)
                except ValueError:
                    raise FastQCParseError(f"Cannot parse %GC value: '{value}'")

    if total_sequences is None:
        raise FastQCParseError(
            "Total Sequences not found in fastqc_data.txt. "
            "The file may be truncated or from an unsupported FastQC version."
        )
    if sequence_length is None:
        raise FastQCParseError("Sequence length not found in fastqc_data.txt.")
    if gc_percent is None:
        raise FastQCParseError("%GC not found in fastqc_data.txt.")

    def _status(module: str) -> str:
        return module_statuses.get(module, "unknown")

    return FastQCMetrics(
        total_sequences=total_sequences,
        sequence_length=sequence_length,
        gc_percent=gc_percent,
        per_base_quality_status=_status("Per base sequence quality"),
        per_sequence_quality_status=_status("Per sequence quality scores"),
        adapter_content_status=_status("Adapter Content"),
        overrepresented_sequences_status=_status("Overrepresented sequences"),
    )


def parse_fastqc_zip(zip_path: Path) -> FastQCMetrics:
    """
    Parse a FastQC ZIP file and return structured QC metrics.

    Args:
        zip_path: Absolute path to the FastQC ZIP on disk.

    Returns:
        Populated FastQCMetrics dataclass.

    Raises:
        FileNotFoundError: zip_path does not exist.
        FastQCParseError: ZIP is invalid, missing fastqc_data.txt,
                          corrupted, or missing required fields.
    """
    if not zip_path.exists():
        raise FileNotFoundError(f"Upload file not found on disk: {zip_path}")

    if not zipfile.is_zipfile(zip_path):
        raise FastQCParseError(
            f"'{zip_path.name}' is not a valid ZIP archive. "
            "FastQC output must be a .zip file."
        )

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            data_entry = _locate_fastqc_data(zf)
            try:
                raw_bytes = zf.read(data_entry)
            except KeyError:
                raise FastQCParseError(
                    f"Could not read '{data_entry}' from the ZIP. "
                    "Archive may be corrupted."
                )
    except zipfile.BadZipFile as exc:
        raise FastQCParseError(
            f"ZIP archive is corrupted or incomplete: {exc}"
        ) from exc

    # FastQC writes UTF-8; latin-1 fallback for pre-0.11 files
    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = raw_bytes.decode("latin-1")

    return _parse_content(content)
