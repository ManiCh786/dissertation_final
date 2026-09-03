# Power BI Build Guide - Evidence-Aligned

The validated analytical data in this package is stored in local Gold CSV files under `data/gold/`.

For a reproducible local dashboard, Power BI Desktop can import:

- `gold_customer_engagement.csv`
- `gold_conversion_funnel.csv`
- `gold_cart_abandonment.csv`
- `gold_category_performance.csv`
- `gold_kpi_summary.csv`

Recommended pages:

1. **Customer engagement:** engagement-level distribution, engagement score, sessions and purchase value.
2. **Conversion:** View -> Cart -> Purchase session funnel and stage conversion percentages.
3. **Category / abandonment:** category revenue, purchase conversion, cart abandonment and remove-from-cart counts.

If Azure SQL is later successfully loaded and verified, the same Gold model can be connected from Azure SQL. Until that evidence exists, do not describe the dashboard as proof of a completed Azure SQL -> Power BI integration. The 15 PNGs in `visualizations_results/` are local reproducible analytical figures, not Power BI or Azure execution evidence.
