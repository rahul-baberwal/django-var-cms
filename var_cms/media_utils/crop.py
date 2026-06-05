"""
var_cms/media_utils/crop.py
===========================
Image crop handler — receives crop coordinates from the frontend Cropper.js
widget and returns a new cropped image saved to MEDIA_ROOT.
"""

import io
import os
import uuid

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse


def handle_crop(request):
    """
    POST params:
        file_path  — relative media path of the source image
        x, y, w, h — crop box in pixels
        rotate     — rotation degrees (optional, default 0)
        scale_x    — horizontal flip (-1 or 1)
        scale_y    — vertical flip (-1 or 1)
        format     — output format: jpeg | png | webp (default: same as source)
    """
    try:
        from PIL import Image
    except ImportError:
        return JsonResponse({"error": "Pillow not installed. Run: uv add pillow"}, status=500)

    file_path = request.POST.get("file_path", "")
    if not file_path:
        return JsonResponse({"error": "file_path required"}, status=400)

    # Sanitise — must be inside MEDIA_ROOT
    abs_path = os.path.join(settings.MEDIA_ROOT, file_path.lstrip("/").replace(settings.MEDIA_URL.lstrip("/"), "", 1))
    if not os.path.exists(abs_path):
        return JsonResponse({"error": "File not found"}, status=404)

    try:
        x = int(float(request.POST.get("x", 0)))
        y = int(float(request.POST.get("y", 0)))
        w = int(float(request.POST.get("w", 0)))
        h = int(float(request.POST.get("h", 0)))
        rotate   = float(request.POST.get("rotate", 0))
        scale_x  = float(request.POST.get("scale_x", 1))
        scale_y  = float(request.POST.get("scale_y", 1))
        out_fmt  = request.POST.get("format", "").upper()
    except (ValueError, TypeError) as e:
        return JsonResponse({"error": f"Invalid params: {e}"}, status=400)

    img = Image.open(abs_path).convert("RGBA")

    # Flip
    if scale_x == -1:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if scale_y == -1:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)

    # Rotate (expand=True keeps full image)
    if rotate:
        img = img.rotate(-rotate, expand=True)

    # Crop
    if w > 0 and h > 0:
        img = img.crop((x, y, x + w, y + h))

    # Determine output format
    orig_ext = abs_path.rsplit(".", 1)[-1].upper()
    fmt_map  = {"JPG": "JPEG", "JPEG": "JPEG", "PNG": "PNG", "WEBP": "WEBP"}
    save_fmt = fmt_map.get(out_fmt) or fmt_map.get(orig_ext) or "PNG"

    # JPEG can't have alpha
    if save_fmt == "JPEG":
        img = img.convert("RGB")

    ext_map = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
    ext = ext_map.get(save_fmt, "png")

    buf = io.BytesIO()
    img.save(buf, format=save_fmt, quality=90)
    buf.seek(0)

    # Save alongside originals
    new_name = f"crops/{uuid.uuid4().hex[:12]}.{ext}"
    saved_path = default_storage.save(new_name, ContentFile(buf.read()))
    url = default_storage.url(saved_path)

    return JsonResponse({"url": url, "path": saved_path, "format": save_fmt, "size": [img.width, img.height]})
