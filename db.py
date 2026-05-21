import base64
import io

import mysql.connector
import streamlit as st
from contextlib import contextmanager
from PIL import Image


@contextmanager
def _get_conn():
    cfg = st.secrets["mysql"]
    conn = mysql.connector.connect(
        host=cfg["host"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        port=int(cfg.get("port", 3306)),
        autocommit=False,
        connection_timeout=10,
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_customer_by_token(token: str):
    with _get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT customer_id, customer_name FROM customer_tokens WHERE token = %s",
            (token,),
        )
        return cur.fetchone()


@st.cache_data(ttl=300)
def get_order_dates(customer_id: int):
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT DISTINCT DeliveryDate FROM PHD_OrderFeedback_Base
               WHERE CustomerId = %s ORDER BY DeliveryDate DESC""",
            (customer_id,),
        )
        return [row[0] for row in cur.fetchall()]


@st.cache_data(ttl=600)
def get_skus_for_date(customer_id: int, order_date):
    with _get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT SkuId, Sku, SaleKg, SaleOrderId, Customer
               FROM PHD_OrderFeedback_Base
               WHERE CustomerId = %s AND DeliveryDate = %s
               ORDER BY Sku""",
            (customer_id, order_date),
        )
        return cur.fetchall()


def get_feedback_for_date(customer_id: int, order_date):
    with _get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT Sku, SkuId, SkuRating, OverAllRating, Comments,
                      ImageUrl1, CreatedAt, UpdatedAt
               FROM PHD_OrderFeedback_Ratings
               WHERE CustomerId = %s AND DeliveryDate = %s""",
            (customer_id, order_date),
        )
        return cur.fetchall()


def get_submitted_dates(customer_id: int):
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT DISTINCT DeliveryDate FROM PHD_OrderFeedback_Ratings
               WHERE CustomerId = %s""",
            (customer_id,),
        )
        return {str(row[0]) for row in cur.fetchall()}


def _encode_image(raw_file) -> str | None:
    """Resize image and return as base64 data-URI string."""
    try:
        img = Image.open(raw_file).convert("RGB")
        img.thumbnail((800, 800), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/jpeg;base64,{b64}"
    except Exception:
        return None


def save_feedback(
    customer_id: int,
    order_date,
    skus: list[dict],           # rows from get_skus_for_date
    sku_ratings: dict,          # {sku_name: int 1-5}
    overall_rating: int,
    comments: str | None,
    image1=None,                # raw file-like objects from Streamlit
    image2=None,
):
    img_url1 = _encode_image(image1) if image1 else None
    img_url2 = _encode_image(image2) if image2 else None

    with _get_conn() as conn:
        cur = conn.cursor()
        for row in skus:
            sku_name   = row["Sku"]
            sku_id     = row["SkuId"]
            sale_order = row["SaleOrderId"]
            customer   = row["Customer"]
            rating     = sku_ratings.get(sku_name)

            cur.execute(
                """INSERT INTO PHD_OrderFeedback_Ratings
                   (DeliveryDate, SaleOrderId, CustomerId, Customer,
                    SkuId, Sku, SkuRating, OverAllRating, Comments,
                    ImageUrl1, ImageUrl2, CreatedAt, UpdatedAt)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, NOW(), NOW())
                   ON DUPLICATE KEY UPDATE
                     SkuRating     = VALUES(SkuRating),
                     OverAllRating = VALUES(OverAllRating),
                     Comments      = VALUES(Comments),
                     ImageUrl1     = VALUES(ImageUrl1),
                     ImageUrl2     = VALUES(ImageUrl2),
                     UpdatedAt     = NOW()""",
                (
                    order_date, sale_order, customer_id, customer,
                    sku_id, sku_name, rating, overall_rating,
                    comments or None, img_url1, img_url2,
                ),
            )
    # clear date caches so submitted badge updates immediately
    get_order_dates.clear()
