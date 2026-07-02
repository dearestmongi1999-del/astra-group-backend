from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status


UPLOAD_ROOT = Path("uploads")
PUBLIC_UPLOAD_PREFIX = "/uploads"
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_IMAGE_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB


def ensure_upload_root() -> None:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def validate_image_upload(file: UploadFile) -> str:
    """
    Validates an UploadFile and returns a safe extension.
    """
    content_type = file.content_type or ""

    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPG, PNG, WEBP and GIF image uploads are allowed.",
        )

    return ALLOWED_IMAGE_CONTENT_TYPES[content_type]


def save_upload_file(file: UploadFile, folder: str) -> dict[str, str | None]:
    """
    Saves an uploaded image to the local uploads folder.

    Returns:
        image_url: public URL path served by FastAPI static files
        image_path: local filesystem path
        original_filename: original uploaded filename
    """
    extension = validate_image_upload(file)
    safe_folder = folder.strip().strip("/\\") or "general"

    target_dir = UPLOAD_ROOT / safe_folder
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}{extension}"
    destination = target_dir / filename

    total_size = 0
    try:
        with destination.open("wb") as output:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break

                total_size += len(chunk)
                if total_size > MAX_IMAGE_SIZE_BYTES:
                    output.close()
                    destination.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Image is too large. Maximum size is 8 MB.",
                    )

                output.write(chunk)
    finally:
        file.file.close()

    image_url = f"{PUBLIC_UPLOAD_PREFIX}/{safe_folder}/{filename}"

    return {
        "image_url": image_url,
        "image_path": str(destination).replace("\\", "/"),
        "original_filename": file.filename,
    }


def delete_local_file(path: str | None) -> None:
    """
    Deletes a local uploaded file when the database record is removed.
    Safe to call for missing files or remote URLs.
    """
    if not path:
        return

    file_path = Path(path)
    if file_path.exists() and file_path.is_file():
        file_path.unlink(missing_ok=True)
