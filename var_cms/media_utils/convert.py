"""
var_cms/media_utils/convert.py
==============================
File format converter.

Supported conversions:
  Images  — jpeg ↔ png ↔ webp ↔ bmp ↔ tiff ↔ gif
  Audio   — mp3 ↔ wav ↔ ogg ↔ flac ↔ aac   (requires ffmpeg)
  Video   — mp4 ↔ webm ↔ avi ↔ mov          (requires ffmpeg)
  PDF → images (page-by-page PNG)             (requires pdf2image + poppler)
"""

import io
import os
import subprocess
import tempfile
import uuid

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse

IMAGE_FORMATS  = {"jpeg", "jpg", "png", "webp", "bmp", "tiff", "gif"}
AUDIO_FORMATS  = {"mp3", "wav", "ogg", "flac", "aac", "m4a"}
VIDEO_FORMATS  = {"mp4", "webm", "avi", "mov", "mkv"}
DOC_FORMATS    = {"pdf"}


def _abs(file_path: str) -> str:
    clean = file_path.lstrip("/").replace(settings.MEDIA_URL.lstrip("/"), "", 1)
    return os.path.join(settings.MEDIA_ROOT, clean)


def _save(data: bytes, ext: str) -> dict:
    name = f"converted/{uuid.uuid4().hex[:12]}.{ext}"
    path = default_storage.save(name, ContentFile(data))
    return {"url": default_storage.url(path), "path": path}


def handle_convert(request):
    """
    POST params:
        file_path   — relative media path of source file
        target_fmt  — desired output extension (e.g. "webp", "mp3", "mp4")
    """
    file_path  = request.POST.get("file_path", "")
    target_fmt = request.POST.get("target_fmt", "").lower().lstrip(".")

    if not file_path or not target_fmt:
        return JsonResponse({"error": "file_path and target_fmt required"}, status=400)

    abs_path = _abs(file_path)
    if not os.path.exists(abs_path):
        return JsonResponse({"error": "File not found"}, status=404)

    src_ext = abs_path.rsplit(".", 1)[-1].lower()

    # ── Image conversion ──────────────────────────────────────────────────────
    if src_ext in IMAGE_FORMATS and target_fmt in IMAGE_FORMATS:
        return _convert_image(abs_path, target_fmt)

    # ── Audio / Video conversion (ffmpeg) ─────────────────────────────────────
    if src_ext in (AUDIO_FORMATS | VIDEO_FORMATS) or target_fmt in (AUDIO_FORMATS | VIDEO_FORMATS):
        return _convert_ffmpeg(abs_path, target_fmt)

    # ── PDF → images ──────────────────────────────────────────────────────────
    if src_ext == "pdf" and target_fmt in ("png", "jpg", "jpeg"):
        return _convert_pdf(abs_path, target_fmt)

    return JsonResponse({"error": f"Unsupported conversion: {src_ext} → {target_fmt}"}, status=400)


def _convert_image(abs_path: str, target_fmt: str) -> JsonResponse:
    try:
        from PIL import Image
    except ImportError:
        return JsonResponse({"error": "Pillow not installed"}, status=500)

    fmt_map = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG",
               "webp": "WEBP", "bmp": "BMP", "tiff": "TIFF", "gif": "GIF"}
    pil_fmt = fmt_map.get(target_fmt, target_fmt.upper())

    img = Image.open(abs_path)
    if pil_fmt == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format=pil_fmt, quality=90)
    buf.seek(0)
    ext = "jpg" if target_fmt in ("jpg", "jpeg") else target_fmt
    return JsonResponse(_save(buf.read(), ext) | {"type": "image"})


def _convert_ffmpeg(abs_path: str, target_fmt: str) -> JsonResponse:
    if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
        return JsonResponse({
            "error": "ffmpeg not found. Install with: sudo apt install ffmpeg",
            "install_hint": "sudo apt install ffmpeg"
        }, status=500)

    with tempfile.NamedTemporaryFile(suffix=f".{target_fmt}", delete=False) as tmp:
        out_path = tmp.name

    try:
        cmd = ["ffmpeg", "-y", "-i", abs_path, out_path]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            err = result.stderr.decode(errors="replace")[-500:]
            return JsonResponse({"error": f"ffmpeg error: {err}"}, status=500)

        with open(out_path, "rb") as f:
            data = f.read()

        media_type = "audio" if target_fmt in AUDIO_FORMATS else "video"
        return JsonResponse(_save(data, target_fmt) | {"type": media_type})
    finally:
        if os.path.exists(out_path):
            os.unlink(out_path)


def _convert_pdf(abs_path: str, target_fmt: str) -> JsonResponse:
    try:
        from pdf2image import convert_from_path
    except ImportError:
        return JsonResponse({
            "error": "pdf2image not installed. Run: uv add pdf2image",
            "install_hint": "uv add pdf2image"
        }, status=500)

    images = convert_from_path(abs_path, dpi=150)
    urls = []
    for i, img in enumerate(images):
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        result = _save(buf.read(), "png")
        urls.append(result["url"])

    return JsonResponse({"type": "pdf_pages", "pages": urls, "count": len(urls)})
