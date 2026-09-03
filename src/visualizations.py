"""Generate 15 reproducible visual results from the validated local Pandas outputs.

These figures are LOCAL analytical evidence. They do not represent Azure
Databricks, Azure SQL, ADF, Power BI, or cloud scalability execution results.
"""
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from common import PROJECT_ROOT

GOLD_DIR = PROJECT_ROOT / 'data' / 'gold'
SILVER_DIR = PROJECT_ROOT / 'data' / 'silver'
OUTPUT_DIR = PROJECT_ROOT / 'visualizations_results'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save_plot(filename: str):
    plt.figtext(0.5, 0.005, 'Validated local Python/Pandas execution - not Azure benchmark evidence',
                ha='center', fontsize=8)
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    plt.savefig(OUTPUT_DIR / filename, dpi=180, bbox_inches='tight')
    plt.close()


def label_bars(ax, fmt='{:.0f}'):
    for patch in ax.patches:
        width = patch.get_width()
        height = patch.get_height()
        # Horizontal bars have a long width and a small categorical height.
        if abs(width) > max(2.0, abs(height) * 3):
            value = width
            ax.text(patch.get_x() + width, patch.get_y() + height / 2,
                    ' ' + fmt.format(value), va='center', fontsize=8)
        else:
            value = height
            ax.text(patch.get_x() + width / 2, patch.get_y() + height,
                    fmt.format(value), ha='center', va='bottom', fontsize=8)


category = pd.read_csv(GOLD_DIR / 'gold_category_performance.csv')
funnel = pd.read_csv(GOLD_DIR / 'gold_conversion_funnel.csv').sort_values('stage_order')
abandonment = pd.read_csv(GOLD_DIR / 'gold_cart_abandonment.csv')
engagement = pd.read_csv(GOLD_DIR / 'gold_customer_engagement.csv')
quality = pd.read_csv(SILVER_DIR / 'data_quality_report.csv')
events = pd.read_csv(SILVER_DIR / 'ecommerce_events_clean.csv')
events['event_time'] = pd.to_datetime(events['event_time'], errors='coerce', utc=True)
events['event_date'] = pd.to_datetime(events['event_date'], errors='coerce')

# 01 Data cleaning: source vs clean
q = quality.set_index('metric')['value']
fig, ax = plt.subplots(figsize=(7, 5))
ax.bar(['Original records', 'Clean records'], [q['raw_rows'], q['clean_rows']])
ax.set_title('Data Cleaning Result: 1,920 to 1,916 Records')
ax.set_ylabel('Records')
label_bars(ax)
save_plot('01_data_cleaning_summary.png')

# 02 Rejection reasons
reason_map = {
    'duplicate_rows_removed': 'Duplicate',
    'unsupported_event_type_rows_removed': 'Unsupported event',
    'missing_required_identifier_rows_removed': 'Missing identifier',
    'nonpositive_price_rows_removed': 'Non-positive price',
}
reasons = pd.Series({label: int(q.get(metric, 0)) for metric, label in reason_map.items()})
fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(reasons.index, reasons.values)
ax.set_title('Four Removed Records by Validation Reason')
ax.set_ylabel('Removed records')
ax.tick_params(axis='x', rotation=20)
label_bars(ax)
save_plot('02_data_quality_rejection_reasons.png')

# 03 Ordered conversion funnel
fig, ax = plt.subplots(figsize=(8, 5))
ax.barh(funnel['stage'], funnel['sessions'])
ax.invert_yaxis()
ax.set_title('Session Conversion Funnel: View -> Cart -> Purchase')
ax.set_xlabel('Distinct sessions')
for i, row in funnel.reset_index(drop=True).iterrows():
    ax.text(row['sessions'] + 3, i, f"{row['percent_of_view_sessions']:.1f}% of view sessions", va='center', fontsize=8)
save_plot('03_conversion_funnel_sessions.png')

# 04 Stage conversion rates
stage_rates = funnel.iloc[1:][['stage', 'conversion_from_previous_stage_pct']].copy()
stage_rates['stage'] = ['View -> Cart', 'Cart -> Purchase']
fig, ax = plt.subplots(figsize=(7, 5))
ax.bar(stage_rates['stage'], stage_rates['conversion_from_previous_stage_pct'])
ax.set_title('Conversion Rate Between Funnel Stages')
ax.set_ylabel('Conversion rate (%)')
label_bars(ax, '{:.1f}')
save_plot('04_funnel_stage_conversion_rates.png')

# 05 Purchase revenue by category
rev = category.sort_values('purchase_revenue')
fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(rev['category_code'], rev['purchase_revenue'])
ax.set_title('Purchase Revenue by Category')
ax.set_xlabel('Revenue (sum of purchase-event price)')
save_plot('05_purchase_revenue_by_category.png')

# 06 Category conversion rates
rates = category.sort_values('purchase_conversion_rate_pct', ascending=False)
x = np.arange(len(rates))
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(x - 0.2, rates['view_to_cart_rate_pct'], 0.4, label='View to cart %')
ax.bar(x + 0.2, rates['purchase_conversion_rate_pct'], 0.4, label='Purchase conversion %')
ax.set_xticks(x, rates['category_code'], rotation=25, ha='right')
ax.set_ylabel('Rate (%)')
ax.set_title('Category Conversion Rate Comparison')
ax.legend()
save_plot('06_category_conversion_rates.png')

# 07 Cart abandonment by category
ab = abandonment.sort_values('abandonment_rate_pct', ascending=False)
fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(ab['category_code'], ab['abandonment_rate_pct'])
ax.set_title('Cart Abandonment Rate by Category')
ax.set_ylabel('Abandonment rate (%)')
ax.tick_params(axis='x', rotation=25)
save_plot('07_cart_abandonment_rate_by_category.png')

# 08 Cart vs abandoned sessions
ab2 = abandonment.sort_values('cart_sessions', ascending=False)
x = np.arange(len(ab2))
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(x - 0.2, ab2['cart_sessions'], 0.4, label='Cart sessions')
ax.bar(x + 0.2, ab2['abandoned_sessions'], 0.4, label='Abandoned sessions')
ax.set_xticks(x, ab2['category_code'], rotation=25, ha='right')
ax.set_title('Cart Sessions and Abandoned Sessions by Category')
ax.set_ylabel('Session-category count')
ax.legend()
save_plot('08_cart_vs_abandoned_sessions.png')

# 09 Engagement level distribution
engagement_counts = engagement['engagement_level'].value_counts().reindex(['Low', 'Medium', 'High']).fillna(0)
fig, ax = plt.subplots(figsize=(7, 5))
ax.bar(engagement_counts.index, engagement_counts.values)
ax.set_title('Customer Engagement Level Distribution')
ax.set_ylabel('Customers')
label_bars(ax)
save_plot('09_customer_engagement_distribution.png')

# 10 Top 15 engagement scores
top = engagement.nlargest(15, 'engagement_score').sort_values('engagement_score')
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(top['user_id'].astype(str), top['engagement_score'])
ax.set_title('Top 15 Customers by Engagement Score')
ax.set_xlabel('Engagement Score = Views + 3*Carts + 5*Purchases')
ax.set_ylabel('User ID')
save_plot('10_top_15_engagement_scores.png')

# 11 Average purchase value by engagement level
avg_purchase = engagement.groupby('engagement_level')['purchase_value'].mean().reindex(['Low', 'Medium', 'High']).fillna(0)
fig, ax = plt.subplots(figsize=(7, 5))
ax.bar(avg_purchase.index, avg_purchase.values)
ax.set_title('Average Purchase Value by Engagement Level')
ax.set_ylabel('Average purchase value')
label_bars(ax, '{:.2f}')
save_plot('11_avg_purchase_value_by_engagement.png')

# 12 Event type distribution
event_counts = events['event_type'].value_counts().reindex(['view', 'cart', 'remove_from_cart', 'purchase']).fillna(0)
fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(event_counts.index, event_counts.values)
ax.set_title('Behavioural Event Type Distribution')
ax.set_ylabel('Events')
ax.tick_params(axis='x', rotation=15)
label_bars(ax)
save_plot('12_event_type_distribution.png')

# 13 Hourly event activity
hourly = events.pivot_table(index='event_hour', columns='event_type', values='user_session', aggfunc='count', fill_value=0).sort_index()
fig, ax = plt.subplots(figsize=(10, 5))
for col in hourly.columns:
    ax.plot(hourly.index, hourly[col], marker='o', label=col)
ax.set_title('Hourly Event Activity')
ax.set_xlabel('Hour of day')
ax.set_ylabel('Event count')
ax.set_xticks(range(0, 24))
ax.legend()
save_plot('13_hourly_event_activity.png')

# 14 Daily purchase revenue trend
purchases = events[events['event_type'].eq('purchase')].copy()
daily_revenue = purchases.groupby('event_date', as_index=False)['price'].sum().sort_values('event_date')
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(daily_revenue['event_date'], daily_revenue['price'], marker='o')
ax.set_title('Daily Purchase Revenue Trend')
ax.set_xlabel('Date')
ax.set_ylabel('Revenue')
ax.tick_params(axis='x', rotation=25)
save_plot('14_daily_purchase_revenue_trend.png')

# 15 Category event mix
mix = category.set_index('category_code')[['views', 'cart_additions', 'purchases', 'remove_from_cart_events']]
fig, ax = plt.subplots(figsize=(10, 6))
bottom = np.zeros(len(mix))
for col in mix.columns:
    vals = mix[col].to_numpy()
    ax.bar(mix.index, vals, bottom=bottom, label=col)
    bottom += vals
ax.set_title('Behavioural Event Mix by Category')
ax.set_ylabel('Event count')
ax.tick_params(axis='x', rotation=25)
ax.legend()
save_plot('15_category_event_mix.png')

index_rows = [
    ('01_data_cleaning_summary.png', 'Functional ETL correctness: original vs clean rows'),
    ('02_data_quality_rejection_reasons.png', 'Exact reasons for the four rejected demo records'),
    ('03_conversion_funnel_sessions.png', 'Ordered session funnel View -> Cart -> Purchase'),
    ('04_funnel_stage_conversion_rates.png', 'View-to-cart and cart-to-purchase session rates'),
    ('05_purchase_revenue_by_category.png', 'Purchase-event revenue by category'),
    ('06_category_conversion_rates.png', 'Category view-to-cart and purchase conversion rates'),
    ('07_cart_abandonment_rate_by_category.png', 'Session-category abandonment rate'),
    ('08_cart_vs_abandoned_sessions.png', 'Cart sessions compared with abandoned sessions'),
    ('09_customer_engagement_distribution.png', 'Low/Medium/High engagement distribution'),
    ('10_top_15_engagement_scores.png', 'Highest engagement scores using the implemented formula'),
    ('11_avg_purchase_value_by_engagement.png', 'Average purchase value by engagement level'),
    ('12_event_type_distribution.png', 'Counts of validated behavioural event types'),
    ('13_hourly_event_activity.png', 'Event activity by hour'),
    ('14_daily_purchase_revenue_trend.png', 'Daily revenue from purchase events'),
    ('15_category_event_mix.png', 'Views/carts/purchases/remove-from-cart mix by category'),
]
pd.DataFrame(index_rows, columns=['file', 'result']).to_csv(OUTPUT_DIR / 'visualization_result_index.csv', index=False)
(OUTPUT_DIR / 'README.txt').write_text(
    'These 15 figures were generated from the validated local Python/Pandas Silver and Gold outputs.\n'
    'They are analytical/functional results, not Azure performance benchmarks and not proof of Azure SQL or Power BI execution.\n'
    'Run: python src/visualizations.py\n', encoding='utf-8'
)
print(f'15 visualizations saved in: {OUTPUT_DIR}')
