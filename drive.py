import io
from datetime import datetime

import streamlit as st
from PIL import Image
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


@st.cache_resource
def _get_drive_service():
    creds = service_account.Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=_SCOPES,
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def upload_photo(raw_file, customer_id: int, order_date) -> str | None:
    """
    Resize raw_file, upload to the configured Drive folder, make it
    publicly readable, and return a direct-view URL.
    Returns None on any failure (photo is optional).
    """
    try:
        service   = _get_drive_service()
        folder_id = st.secrets["google_drive"]["folder_id"]

        # Resize to keep file size reasonable
        img = Image.open(raw_file).convert("RGB")
        img.thumbnail((1024, 1024), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        buf.seek(0)

        # Unique filename: customerID_date_timestamp.jpg
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_str = order_date.strftime("%Y%m%d") if hasattr(order_date, "strftime") else str(order_date)
        filename = f"{customer_id}_{date_str}_{ts}.jpg"

        file_metadata = {"name": filename, "parents": [folder_id]}
        media = MediaIoBaseUpload(buf, mimetype="image/jpeg", resumable=False)

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
        ).execute()

        file_id = file.get("id")

        # Make publicly viewable (anyone with link)
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        return f"https://drive.google.com/uc?id={file_id}"

    except Exception:
        return None
