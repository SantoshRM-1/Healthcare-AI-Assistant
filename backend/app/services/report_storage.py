import asyncio
import io
import time
from functools import partial

import cloudinary
from cloudinary import uploader, utils

from app.core.config import settings


def configure_cloudinary() -> None:
    if not settings.cloudinary_cloud_name or not settings.cloudinary_api_key or not settings.cloudinary_api_secret:
        raise RuntimeError("Cloudinary credentials are not configured")
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )


async def upload_report(data: bytes, public_id: str, resource_type: str) -> dict:
    configure_cloudinary()
    options = {"public_id": public_id, "resource_type": resource_type, "type": "authenticated", "overwrite": False, "use_filename": False}
    return await asyncio.to_thread(partial(uploader.upload, io.BytesIO(data), **options))


async def create_private_download_url(public_id: str, resource_type: str, file_type: str) -> str:
    configure_cloudinary()
    extension = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "text/plain": "txt",
        "text/markdown": "md",
        "application/json": "json",
        "text/csv": "csv",
    }.get(file_type, file_type.split("/")[-1])
    return await asyncio.to_thread(
        partial(
            utils.private_download_url,
            public_id,
            extension,
            resource_type=resource_type,
            type="authenticated",
            expires_at=int(time.time()) + 120,
        )
    )


async def delete_report_asset(public_id: str, resource_type: str) -> None:
    configure_cloudinary()
    await asyncio.to_thread(partial(uploader.destroy, public_id, resource_type=resource_type, type="authenticated", invalidate=True))
