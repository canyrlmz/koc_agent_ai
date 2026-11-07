"""Kayıt kaynakları.

Analiz hattı sadece "diskte bir ses/video dosyası" bekler. Kaydın nereden geldiği
bu dosyadaki kaynak sınıflarının işidir:

- UploadSource: kullanıcı dosyayı web arayüzünden yükler (şu anki MVP).
- İleride ZoomSource / TeamsSource: Zoom/Teams bulut kayıtlarını API ile indirip
  aynı şekilde diske yazar. Analiz tarafında hiçbir şey değişmez.
"""
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from .config import UPLOAD_DIR

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".webm", ".ogg", ".mov", ".flac", ".mkv", ".avi"}


class UploadSource:
    name = "upload"

    def save(self, filename: str, fileobj: BinaryIO) -> Path:
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Desteklenmeyen dosya türü: {ext or '(uzantı yok)'}. "
                f"İzin verilenler: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
        target = UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
        with target.open("wb") as out:
            shutil.copyfileobj(fileobj, out)
        return target
