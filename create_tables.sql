-- ─────────────────────────────────────────────────────────────────────────────
-- Run this script once against your MySQL database to create the required tables
-- ─────────────────────────────────────────────────────────────────────────────

-- Stores the unique token for each customer (used in WhatsApp links)
CREATE TABLE IF NOT EXISTS customer_tokens (
    id            INT          AUTO_INCREMENT PRIMARY KEY,
    token         VARCHAR(100) NOT NULL UNIQUE,
    customer_id   VARCHAR(255) NOT NULL,
    customer_name VARCHAR(255),                    -- optional display name
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_token      (token),
    INDEX idx_customer   (customer_id)
);

-- Stores all feedback submitted by customers
-- One row per SKU (sku_rating filled), plus one 'OVERALL' row per submission
-- (overall_rating, comments, image_data filled on the OVERALL row)
CREATE TABLE IF NOT EXISTS PHD_OrderFeedback_Ratings (
    id             INT          AUTO_INCREMENT PRIMARY KEY,
    customer_id    VARCHAR(255) NOT NULL,
    order_date     DATE         NOT NULL,
    sku            VARCHAR(255) NOT NULL,           -- 'OVERALL' for the summary row
    sku_rating     TINYINT      CHECK (sku_rating BETWEEN 1 AND 5),
    overall_rating TINYINT      CHECK (overall_rating BETWEEN 1 AND 5),
    comments       TEXT,
    image_data     LONGBLOB,
    image_filename VARCHAR(255),
    submitted_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_cust_date (customer_id, order_date)
);
