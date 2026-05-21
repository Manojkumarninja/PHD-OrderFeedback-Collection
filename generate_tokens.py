"""
Run this script once (or whenever new customers are added) to generate
unique WhatsApp links for each customer.

Usage (Windows PowerShell):
    $env:DB_HOST="116.202.114.156"
    $env:DB_PORT="3971"
    $env:DB_USER="datalake_trw"
    $env:DB_PASSWORD="Tedd@13332!wq23"
    $env:DB_NAME="datalake"
    $env:APP_URL="https://your-app.streamlit.app"   # no trailing slash

    python generate_tokens.py
"""

import os
import secrets
import mysql.connector

DB_CONFIG = {
    "host":     os.environ["DB_HOST"],
    "user":     os.environ["DB_USER"],
    "password": os.environ["DB_PASSWORD"],
    "database": os.environ["DB_NAME"],
    "port":     int(os.environ.get("DB_PORT", 3306)),
}

APP_URL = os.environ.get("APP_URL", "https://your-app.streamlit.app")


def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur  = conn.cursor(dictionary=True)

    # All distinct customers from the base table (with their display name)
    cur.execute("""
        SELECT CustomerId, Customer
        FROM PHD_OrderFeedback_Base
        GROUP BY CustomerId, Customer
        ORDER BY Customer
    """)
    customers = cur.fetchall()
    print(f"Found {len(customers)} customer(s).\n")

    results = []
    for row in customers:
        cid   = row["CustomerId"]
        cname = row["Customer"]

        cur.execute("SELECT token FROM customer_tokens WHERE customer_id = %s", (cid,))
        existing = cur.fetchone()

        if existing:
            token  = existing["token"]
            status = "existing"
        else:
            token = secrets.token_urlsafe(32)
            cur.execute(
                "INSERT INTO customer_tokens (token, customer_id, customer_name) VALUES (%s, %s, %s)",
                (token, cid, cname),
            )
            conn.commit()
            status = "new"

        link = f"{APP_URL}?token={token}"
        results.append((cname, cid, status, link))

    cur.close()
    conn.close()

    print(f"{'Customer':<40} {'ID':<12} {'Status':<10} Link")
    print("-" * 120)
    for cname, cid, status, link in results:
        print(f"{cname:<40} {cid:<12} {status:<10} {link}")

    print(f"\nDone. Paste each customer's link into their WhatsApp group.")


if __name__ == "__main__":
    main()
