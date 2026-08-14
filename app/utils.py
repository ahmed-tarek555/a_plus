from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
import cloudinary
import cloudinary.uploader
from io import BytesIO
import os
from urllib.parse import urlparse, parse_qs

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)


ALLOWED_PFP_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_PFP_SIZE = 5 * 1024 * 1024
MAX_PFP_PIXELS = 10_000_000


ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "application/pdf"
}
MAX_FILE_SIZE = 5 * 1024 * 1024

def is_material_valid(file: UploadFile):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        return False

    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_FILE_SIZE:
        return False
    if size == 0:
        return False

    return True

def upload_image(file: UploadFile, folder: str):
    result = cloudinary.uploader.upload(
        file.file,
        folder=f"{folder}",
        transformation=[
            {"width": 256, "height": 256, "crop": "fill"},
            {"quality": "auto"}
        ]
    )
    return result["public_id"]

def upload_file(file: UploadFile, folder: str):
    result = cloudinary.uploader.upload(
        file.file,
        folder=f"{folder}",
        transformation=[
            {"quality": "auto"}
        ]
    )
    return result["public_id"]

def generate_url(public_id):
    url, _ = cloudinary.utils.cloudinary_url(
        public_id,
        resource_type="image",
    )
    return url

def delete_file(public_id: str, resource_type: str):
    cloudinary.uploader.destroy(public_id, resource_type=resource_type)

def is_valid_image(upload_file) -> bool:
    try:
        contents = upload_file.file.read()
        if not contents:
            return False
        if len(contents) > MAX_PFP_SIZE:
            return False
        if upload_file.content_type not in ALLOWED_PFP_MIME_TYPES:
            return False
        image = Image.open(BytesIO(contents))
        image.verify()
        image = Image.open(BytesIO(contents))
        width, height = image.size
        if width * height > MAX_PFP_PIXELS:
            return False
        if image.format not in {"JPEG", "PNG", "WEBP"}:
            return False
        return True

    except (UnidentifiedImageError, OSError, ValueError):
        return False
    finally:
        upload_file.file.seek(0)


def extract_youtube_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.hostname in ("youtu.be",):
        return parsed.path.lstrip("/")
    if parsed.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            query = parse_qs(parsed.query)
            if "v" in query:
                return query["v"][0]
        if parsed.path.startswith("/embed/"):
            return parsed.path.split("/embed/")[1]
    raise ValueError("Could not extract YouTube video ID from URL")
