import re
import shutil
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from config import get_settings

UNSAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


class FileStorageError(Exception):
    pass


class FileStorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.upload_dir = self.settings.upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def sanitize_filename(self, filename: str) -> str:
        name = Path(filename).name
        sanitized = UNSAFE_FILENAME_PATTERN.sub("_", name).strip("._")
        if not sanitized:
            raise FileStorageError("Invalid filename.")
        return sanitized

    def get_extension(self, filename: str) -> str:
        lower_name = filename.lower()
        for ext in (".tar.gz", ".tar.bz2"):
            if lower_name.endswith(ext):
                return ext
        return Path(lower_name).suffix

    def validate_file(self, filename: str, size_bytes: int) -> None:
        if size_bytes <= 0:
            raise FileStorageError("Uploaded file is empty.")

        if size_bytes > self.settings.max_upload_size_bytes:
            raise FileStorageError(
                f"File exceeds maximum size of {self.settings.max_upload_size_mb} MB."
            )

        extension = self.get_extension(filename)
        if extension not in self.settings.allowed_extension_set:
            allowed = ", ".join(sorted(self.settings.allowed_extension_set))
            raise FileStorageError(f"Unsupported file type. Allowed extensions: {allowed}")

    def detect_file_type(self, filename: str) -> str:
        lower_name = filename.lower()
        extension = self.get_extension(filename)

        if extension == ".zip":
            if "fastqc" in lower_name:
                return "fastqc_zip"
            if "multiqc" in lower_name:
                return "multiqc_zip"
            return "zip_archive"

        if extension == ".html":
            return "multiqc_html"

        if extension in {".gz", ".tar.gz"}:
            return "compressed_archive"

        return "other"

    def get_job_directory(self, job_id: UUID) -> Path:
        job_dir = self.upload_dir / str(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def save_upload(self, job_id: UUID, upload_file: UploadFile) -> tuple[str, str, int]:
        if not upload_file.filename:
            raise FileStorageError("No filename provided.")

        content = upload_file.file.read()
        size_bytes = len(content)
        self.validate_file(upload_file.filename, size_bytes)

        safe_filename = self.sanitize_filename(upload_file.filename)
        job_dir = self.get_job_directory(job_id)
        destination = job_dir / safe_filename

        with destination.open("wb") as saved_file:
            saved_file.write(content)

        relative_path = destination.relative_to(self.settings.upload_dir.parent).as_posix()
        return safe_filename, relative_path, size_bytes

    def delete_job_files(self, job_id: UUID) -> None:
        job_dir = self.upload_dir / str(job_id)
        if job_dir.exists():
            shutil.rmtree(job_dir)
