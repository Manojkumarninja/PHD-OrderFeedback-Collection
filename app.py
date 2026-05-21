import streamlit as st
import pandas as pd

from db import (
    get_customer_by_token,
    get_order_dates,
    get_skus_for_date,
    get_submitted_dates,
    get_feedback_for_date,
    save_feedback,
)

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Order Feedback",
    page_icon="📦",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #f0f4f8; }
[data-testid="stHeader"]           { background: transparent; }

.header-card {
    background: linear-gradient(135deg, #1d4ed8 0%, #3b82f6 100%);
    color: white;
    padding: 1.4rem 1.8rem;
    border-radius: 14px;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 15px rgba(59,130,246,.3);
}
.header-card h2 { margin: 0 0 .25rem; font-size: 1.5rem; }
.header-card p  { margin: 0; opacity: .85; font-size: .95rem; }

.sku-block {
    background: white;
    border-radius: 10px;
    padding: 1rem 1.2rem .4rem;
    margin-bottom: .8rem;
    box-shadow: 0 1px 4px rgba(0,0,0,.07);
}

.view-card {
    background: white;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: .75rem;
    box-shadow: 0 1px 4px rgba(0,0,0,.07);
}
.view-label  { color: #6b7280; font-size: .82rem; margin-bottom: .2rem; }
.view-value  { font-size: 1.05rem; font-weight: 500; }
.view-stars  { font-size: 1.2rem; }
.submitted-badge {
    display: inline-block;
    background: #d1fae5;
    color: #065f46;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: .82rem;
    font-weight: 600;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ─── Session state defaults ────────────────────────────────────────────────────
for key, default in [("page", "dates"), ("selected_date", None)]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─── Token auth ────────────────────────────────────────────────────────────────
token = st.query_params.get("token")

if not token:
    st.error("🔗 Invalid link. Please use the link shared in your WhatsApp group.")
    st.stop()

customer = get_customer_by_token(token)
if not customer:
    st.error("❌ This link is invalid or has expired. Please contact your sales representative.")
    st.stop()

customer_id   = int(customer["customer_id"])
customer_name = customer.get("customer_name") or f"Customer {customer_id}"

# ─── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="header-card">
  <h2>📦 Order Feedback</h2>
  <p>Welcome, <strong>{customer_name}</strong> — we value your feedback!</p>
</div>
""", unsafe_allow_html=True)

STAR_LABELS = {
    1: "⭐  Poor",
    2: "⭐⭐  Fair",
    3: "⭐⭐⭐  Good",
    4: "⭐⭐⭐⭐  Very Good",
    5: "⭐⭐⭐⭐⭐  Excellent",
}

def stars_display(rating) -> str:
    """Return star emoji string for a numeric rating."""
    try:
        n = int(round(float(rating)))
        return "⭐" * n + f"  ({n}/5)"
    except (TypeError, ValueError):
        return "—"


# ══════════════════════════════════════════════════════════════════════════════
# PAGE ❶ — ORDER DATES
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "dates":
    order_dates   = get_order_dates(customer_id)
    submitted_set = get_submitted_dates(customer_id)

    if not order_dates:
        st.info("No orders found for your account yet.")
        st.stop()

    st.subheader("Your Order Dates")
    st.caption("Tap a date to provide feedback. Already submitted dates are view-only.")

    for d in order_dates:
        d_str = d.strftime("%d %b %Y") if hasattr(d, "strftime") else str(d)
        done  = str(d) in submitted_set
        label = f"📅  {d_str}{'   ✅ Submitted' if done else ''}"

        if st.button(label, key=f"btn_{d}", use_container_width=True):
            st.session_state.selected_date = d
            # Route to read-only view if already submitted, else to the form
            st.session_state.page = "view" if done else "feedback"
            st.rerun()

        if done:
            st.caption("&nbsp;&nbsp;&nbsp; Feedback submitted — tap to view.", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE ❷ — READ-ONLY VIEW (submitted dates)
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "view":
    sel_date = st.session_state.selected_date
    d_str    = sel_date.strftime("%d %b %Y") if hasattr(sel_date, "strftime") else str(sel_date)

    if st.button("← Back to dates"):
        st.session_state.page = "dates"
        st.rerun()

    st.subheader(f"Your Feedback — {d_str}")

    rows = get_feedback_for_date(customer_id, sel_date)
    if not rows:
        st.warning("No feedback found for this date.")
        st.stop()

    # Submitted timestamp (from first row)
    submitted_at = rows[0].get("UpdatedAt") or rows[0].get("CreatedAt")
    if submitted_at:
        ts = submitted_at.strftime("%d %b %Y, %I:%M %p") if hasattr(submitted_at, "strftime") else str(submitted_at)
        st.markdown(f'<span class="submitted-badge">✅ Submitted on {ts}</span>', unsafe_allow_html=True)

    # Order summary
    skus = get_skus_for_date(customer_id, sel_date)
    with st.expander("📋 Order Summary", expanded=False):
        df = pd.DataFrame(skus)[["Sku", "SaleKg"]].rename(
            columns={"Sku": "Product", "SaleKg": "Qty (Kg)"}
        )
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    # Per-SKU ratings (read-only)
    st.markdown("### ⭐ Product Ratings")
    for row in rows:
        if row["Sku"] == "OVERALL":
            continue
        st.markdown(
            f'<div class="view-card">'
            f'<div class="view-label">{row["Sku"]}</div>'
            f'<div class="view-stars">{stars_display(row["SkuRating"])}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # Overall rating (read-only) — take from any row since it's the same across all
    overall = next((r["OverAllRating"] for r in rows if r["OverAllRating"] is not None), None)
    st.markdown("### 🏆 Overall Rating")
    st.markdown(
        f'<div class="view-card"><div class="view-stars">{stars_display(overall)}</div></div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # Comments (read-only)
    comments = next((r["Comments"] for r in rows if r["Comments"]), None)
    st.markdown("### 💬 Comments")
    st.markdown(
        f'<div class="view-card"><div class="view-value">{comments if comments else "<em style=\'color:#9ca3af\'>No comments provided.</em>"}</div></div>',
        unsafe_allow_html=True,
    )

    # Photo (read-only)
    image_url = next((r["ImageUrl1"] for r in rows if r.get("ImageUrl1")), None)
    if image_url:
        st.divider()
        st.markdown("### 📷 Photo")
        st.image(image_url, use_column_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE ❸ — FEEDBACK FORM (new submissions only)
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "feedback":
    sel_date = st.session_state.selected_date
    d_str    = sel_date.strftime("%d %b %Y") if hasattr(sel_date, "strftime") else str(sel_date)

    # Safety guard: if someone navigates here for an already-submitted date, redirect to view
    submitted_set = get_submitted_dates(customer_id)
    if str(sel_date) in submitted_set:
        st.session_state.page = "view"
        st.rerun()

    if st.button("← Back to dates"):
        st.session_state.page = "dates"
        st.rerun()

    st.subheader(f"Feedback for {d_str}")

    skus = get_skus_for_date(customer_id, sel_date)
    if not skus:
        st.warning("No products found for this order date.")
        st.stop()

    with st.expander("📋 Order Summary", expanded=False):
        df = pd.DataFrame(skus)[["Sku", "SaleKg"]].rename(
            columns={"Sku": "Product", "SaleKg": "Qty (Kg)"}
        )
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    with st.form("feedback_form", clear_on_submit=False):

        st.markdown("### ⭐ Rate Each Product")
        sku_ratings: dict[str, int] = {}

        for row in skus:
            sku = row["Sku"]
            st.markdown(
                f'<div class="sku-block">'
                f'<strong>{sku}</strong> &nbsp;'
                f'<span style="color:#6b7280;font-size:.85rem">{row["SaleKg"]} Kg</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            sku_ratings[sku] = st.radio(
                f"Rating for {sku}",
                options=[1, 2, 3, 4, 5],
                format_func=lambda x: STAR_LABELS[x],
                index=2,
                horizontal=True,
                key=f"r_{row['SkuId']}",
                label_visibility="collapsed",
            )

        st.divider()

        st.markdown("### 🏆 Overall Order Rating")
        overall_rating: int = st.radio(
            "Overall experience",
            options=[1, 2, 3, 4, 5],
            format_func=lambda x: STAR_LABELS[x],
            index=2,
            horizontal=True,
            key="overall",
        )

        st.divider()

        st.markdown("### 💬 Comments")
        comments: str = st.text_area(
            "Share any additional thoughts",
            placeholder="e.g. Freshness was great, would love faster delivery next time…",
            height=120,
            key="comments",
        )

        st.divider()

        st.markdown("### 📷 Add Photos  *(optional)*")
        img_col1, img_col2 = st.columns(2)
        with img_col1:
            uploaded_file = st.file_uploader(
                "Upload from gallery",
                type=["jpg", "jpeg", "png"],
                key="upload",
            )
        with img_col2:
            camera_photo = st.camera_input("Take a photo", key="camera")

        st.markdown("")
        submitted = st.form_submit_button(
            "✅  Submit Feedback",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        with st.spinner("Saving your feedback…"):
            try:
                save_feedback(
                    customer_id    = customer_id,
                    order_date     = sel_date,
                    skus           = skus,
                    sku_ratings    = sku_ratings,
                    overall_rating = overall_rating,
                    comments       = comments,
                    image1         = camera_photo or uploaded_file,
                    image2         = None,
                )
                st.session_state.page = "success"
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save feedback: {exc}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE ❹ — SUCCESS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "success":
    sel_date = st.session_state.selected_date
    d_str    = sel_date.strftime("%d %b %Y") if hasattr(sel_date, "strftime") else str(sel_date)

    st.success(f"✅ Thank you! Your feedback for **{d_str}** has been submitted.")
    st.balloons()
    st.markdown("Your input helps us improve quality and service. 🙏")
    st.markdown("")

    if st.button("📅  Give feedback for another date", use_container_width=True, type="primary"):
        st.session_state.page          = "dates"
        st.session_state.selected_date = None
        st.rerun()
