from fastapi import UploadFile

from src.domain.exceptions import DomainValidationError


async def read_upload_with_limit(
    file: UploadFile, max_bytes: int = 5 * 1024 * 1024
) -> bytes:
    chunk_size = 64 * 1024
    chunks: list[bytes] = []
    total_size = 0
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_bytes:
            raise DomainValidationError("File size exceeds 5 MB limit")
        chunks.append(chunk)
    return b"".join(chunks)
