-- Prepared Azure SQL schema for the Gold CSV serving path.
-- This file is implementation code only; its presence is not evidence that the
-- tables were successfully created or loaded in Azure SQL.

CREATE TABLE customer_engagement (
    user_id BIGINT NULL,
    views INT NULL,
    carts INT NULL,
    purchases INT NULL,
    remove_from_cart INT NULL,
    sessions INT NULL,
    purchase_value FLOAT NULL,
    total_interactions INT NULL,
    engagement_score FLOAT NULL,
    engagement_level VARCHAR(20) NULL
);

CREATE TABLE conversion_funnel (
    stage_order INT NULL,
    stage VARCHAR(50) NULL,
    sessions INT NULL,
    percent_of_view_sessions FLOAT NULL,
    conversion_from_previous_stage_pct FLOAT NULL
);

CREATE TABLE cart_abandonment (
    category_code VARCHAR(255) NULL,
    cart_sessions INT NULL,
    abandoned_sessions INT NULL,
    remove_from_cart_events INT NULL,
    abandonment_rate_pct FLOAT NULL
);

CREATE TABLE category_performance (
    category_code VARCHAR(255) NULL,
    views INT NULL,
    cart_additions INT NULL,
    purchases INT NULL,
    remove_from_cart_events INT NULL,
    purchase_revenue FLOAT NULL,
    view_to_cart_rate_pct FLOAT NULL,
    purchase_conversion_rate_pct FLOAT NULL
);
