import streamlit as st
import pandas as pd

from db import (
    get_customer_by_token,
    get_order_dates,
    get_skus_for_date,
    get_submitted_dates,
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
    st.caption("Tap a date to rate the products delivered that day.")

    for d in order_dates:
        d_str = d.strftime("%d %b %Y") if hasattr(d, "strftime") else str(d)
        done  = str(d) in submitted_set
        label = f"📅  {d_str}{'   ✅ Submitted' if done else ''}"

        if st.button(label, key=f"btn_{d}", use_container_width=True):
            st.session_state.selected_date = d
            st.session_state.page = "feedback"
            st.rerun()

        if done:
            st.caption("&nbsp;&nbsp;&nbsp; Tap to view or update feedback.", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE ❷ — FEEDBACK FORM
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "feedback":
    sel_date = st.session_state.selected_date
    d_str    = sel_date.strftime("%d %b %Y") if hasattr(sel_date, "strftime") else str(sel_date)

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

    # ── Form ──────────────────────────────────────────────────────────────────
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

    # ── On submit ─────────────────────────────────────────────────────────────
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
# PAGE ❸ — SUCCESS
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
