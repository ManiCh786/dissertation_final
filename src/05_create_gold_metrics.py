"""Create the validated local Gold analytical outputs from Silver CSV data.

The resulting tables are produced by Python/Pandas and are the evidence source for
behavioural results in the practical package. They must not be described as
Databricks, Azure SQL, ADF or Power BI execution results unless separate cloud
execution evidence exists.
"""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
from common import PROJECT_ROOT


def safe_rate(num, den):
    return np.where(np.asarray(den) > 0, np.asarray(num) / np.asarray(den) * 100.0, 0.0)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--output-dir', default=str(PROJECT_ROOT / 'data' / 'gold'))
    a = p.parse_args()

    source = Path(a.input)
    if not source.exists():
        raise SystemExit(f'Input file not found: {source}')

    df = pd.read_csv(source, parse_dates=['event_time'])
    gold = Path(a.output_dir)
    gold.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1) Customer engagement
    # Formula required by the practical implementation:
    # Engagement Score = Views + (3 x Carts) + (5 x Purchases)
    # remove_from_cart is retained as a descriptive interaction count but is
    # intentionally not assigned engagement-score weight.
    # Levels use the 33rd and 67th percentiles of the observed user scores:
    # Low <= q33; Medium > q33 and <= q67; High > q67.
    # ------------------------------------------------------------------
    piv = pd.crosstab(df['user_id'], df['event_type'])
    for c in ['view', 'cart', 'purchase', 'remove_from_cart']:
        if c not in piv.columns:
            piv[c] = 0
    sessions = df.groupby('user_id')['user_session'].nunique().rename('sessions')
    purchase_value = (
        df.loc[df.event_type.eq('purchase')]
        .groupby('user_id')['price'].sum()
        .rename('purchase_value')
    )
    customer = (
        piv[['view', 'cart', 'purchase', 'remove_from_cart']]
        .join(sessions).join(purchase_value).fillna(0).reset_index()
        .rename(columns={'view': 'views', 'cart': 'carts', 'purchase': 'purchases'})
    )
    customer['total_interactions'] = (
        customer['views'] + customer['carts'] + customer['purchases'] + customer['remove_from_cart']
    )
    customer['engagement_score'] = customer['views'] + 3 * customer['carts'] + 5 * customer['purchases']

    if len(customer) >= 3:
        q33, q67 = customer['engagement_score'].quantile([0.33, 0.67]).tolist()
        customer['engagement_level'] = np.select(
            [customer['engagement_score'] <= q33, customer['engagement_score'] <= q67],
            ['Low', 'Medium'],
            default='High'
        )
    else:
        q33 = q67 = float(customer['engagement_score'].median()) if len(customer) else 0.0
        customer['engagement_level'] = 'Medium'
    customer.to_csv(gold / 'gold_customer_engagement.csv', index=False)

    # ------------------------------------------------------------------
    # 2) Session-based ordered conversion funnel: View -> Cart -> Purchase
    # A session reaches Cart only when a cart event occurs at/after its first
    # view; it reaches Purchase only when a purchase occurs at/after its first
    # reached cart. This keeps the funnel explicitly session based and ordered.
    # ------------------------------------------------------------------
    first_times = (
        df[df['event_type'].isin(['view', 'cart', 'purchase'])]
        .groupby(['user_session', 'event_type'])['event_time'].min()
        .unstack()
    )
    for c in ['view', 'cart', 'purchase']:
        if c not in first_times.columns:
            first_times[c] = pd.NaT

    has_view = first_times['view'].notna()
    reached_cart = has_view & first_times['cart'].notna() & (first_times['cart'] >= first_times['view'])
    reached_purchase = reached_cart & first_times['purchase'].notna() & (first_times['purchase'] >= first_times['cart'])

    view_sessions = int(has_view.sum())
    cart_sessions = int(reached_cart.sum())
    purchase_sessions = int(reached_purchase.sum())
    funnel = pd.DataFrame([
        {'stage_order': 1, 'stage': 'View sessions', 'sessions': view_sessions},
        {'stage_order': 2, 'stage': 'Cart sessions', 'sessions': cart_sessions},
        {'stage_order': 3, 'stage': 'Purchase sessions', 'sessions': purchase_sessions},
    ])
    funnel['percent_of_view_sessions'] = safe_rate(funnel['sessions'], view_sessions)
    funnel['conversion_from_previous_stage_pct'] = [
        100.0,
        float(safe_rate(cart_sessions, view_sessions)),
        float(safe_rate(purchase_sessions, cart_sessions)),
    ]
    funnel.to_csv(gold / 'gold_conversion_funnel.csv', index=False)

    # ------------------------------------------------------------------
    # 3) Cart abandonment by session + category
    # A session/category is abandoned when it contains >=1 cart event and no
    # purchase event in that same session/category. remove_from_cart is retained
    # in Silver data but does not independently change this abandonment flag.
    # ------------------------------------------------------------------
    session_cat = (
        df.groupby(['user_session', 'category_code', 'event_type'])
        .size().unstack(fill_value=0).reset_index()
    )
    for c in ['cart', 'purchase', 'remove_from_cart']:
        if c not in session_cat.columns:
            session_cat[c] = 0
    session_cat['had_cart'] = session_cat['cart'] > 0
    session_cat['had_purchase'] = session_cat['purchase'] > 0
    session_cat['abandoned'] = session_cat['had_cart'] & ~session_cat['had_purchase']
    abandonment = session_cat.groupby('category_code').agg(
        cart_sessions=('had_cart', 'sum'),
        abandoned_sessions=('abandoned', 'sum'),
        remove_from_cart_events=('remove_from_cart', 'sum'),
    ).reset_index()
    abandonment['abandonment_rate_pct'] = safe_rate(
        abandonment['abandoned_sessions'], abandonment['cart_sessions']
    )
    abandonment.to_csv(gold / 'gold_cart_abandonment.csv', index=False)

    # ------------------------------------------------------------------
    # 4) Category performance
    # views/carts/purchases are event counts. Purchase revenue is the sum of the
    # price field only for purchase events. The source has no quantity field,
    # therefore each purchase event contributes its recorded price once.
    # ------------------------------------------------------------------
    counts = (
        df.groupby(['category_code', 'event_type'])['product_id'].size()
        .unstack(fill_value=0)
    )
    for c in ['view', 'cart', 'purchase', 'remove_from_cart']:
        if c not in counts.columns:
            counts[c] = 0
    rev = (
        df[df.event_type.eq('purchase')]
        .groupby('category_code')['price'].sum()
        .rename('purchase_revenue')
    )
    perf = (
        counts[['view', 'cart', 'purchase', 'remove_from_cart']]
        .rename(columns={
            'view': 'views', 'cart': 'cart_additions', 'purchase': 'purchases',
            'remove_from_cart': 'remove_from_cart_events'
        })
        .join(rev).fillna(0).reset_index()
    )
    perf['view_to_cart_rate_pct'] = safe_rate(perf['cart_additions'], perf['views'])
    perf['purchase_conversion_rate_pct'] = safe_rate(perf['purchases'], perf['views'])
    perf.to_csv(gold / 'gold_category_performance.csv', index=False)

    # ------------------------------------------------------------------
    # 5) Compact KPI summary and reproducibility definitions
    # ------------------------------------------------------------------
    total_cart_sessions = int(abandonment['cart_sessions'].sum())
    total_abandoned = int(abandonment['abandoned_sessions'].sum())
    summary = pd.DataFrame([
        {'metric': 'clean_events', 'value': len(df)},
        {'metric': 'unique_users', 'value': df['user_id'].nunique()},
        {'metric': 'unique_sessions', 'value': df['user_session'].nunique()},
        {'metric': 'view_events', 'value': int(df['event_type'].eq('view').sum())},
        {'metric': 'cart_events', 'value': int(df['event_type'].eq('cart').sum())},
        {'metric': 'purchase_events', 'value': int(df['event_type'].eq('purchase').sum())},
        {'metric': 'remove_from_cart_events', 'value': int(df['event_type'].eq('remove_from_cart').sum())},
        {'metric': 'purchase_revenue', 'value': round(float(df.loc[df.event_type.eq('purchase'), 'price'].sum()), 2)},
        {'metric': 'view_sessions', 'value': view_sessions},
        {'metric': 'cart_sessions', 'value': cart_sessions},
        {'metric': 'purchase_sessions', 'value': purchase_sessions},
        {'metric': 'view_to_cart_session_rate_pct', 'value': round(float(safe_rate(cart_sessions, view_sessions)), 4)},
        {'metric': 'cart_to_purchase_session_rate_pct', 'value': round(float(safe_rate(purchase_sessions, cart_sessions)), 4)},
        {'metric': 'overall_session_conversion_rate_pct', 'value': round(float(safe_rate(purchase_sessions, view_sessions)), 4)},
        {'metric': 'overall_cart_abandonment_rate_pct', 'value': round(float(safe_rate(total_abandoned, total_cart_sessions)), 4)},
        {'metric': 'engagement_q33_threshold', 'value': float(q33)},
        {'metric': 'engagement_q67_threshold', 'value': float(q67)},
    ])
    summary.to_csv(gold / 'gold_kpi_summary.csv', index=False)

    definitions = pd.DataFrame([
        {'metric': 'Engagement score', 'definition': 'Views + (3 x Carts) + (5 x Purchases)'},
        {'metric': 'Low engagement', 'definition': f'Engagement score <= 33rd percentile threshold ({q33:g})'},
        {'metric': 'Medium engagement', 'definition': f'Engagement score > {q33:g} and <= 67th percentile threshold ({q67:g})'},
        {'metric': 'High engagement', 'definition': f'Engagement score > 67th percentile threshold ({q67:g})'},
        {'metric': 'Conversion funnel', 'definition': 'Distinct sessions reaching ordered stages View -> Cart -> Purchase using first event timestamps'},
        {'metric': 'Cart abandonment', 'definition': 'Session/category has >=1 cart event and no purchase event in the same session/category'},
        {'metric': 'remove_from_cart treatment', 'definition': 'Retained and reported, but does not independently define abandonment and has zero engagement-score weight'},
        {'metric': 'Category views/carts/purchases', 'definition': 'Counts of view, cart and purchase events for each category_code'},
        {'metric': 'View-to-cart rate', 'definition': 'Category cart events / category view events x 100'},
        {'metric': 'Purchase conversion rate', 'definition': 'Category purchase events / category view events x 100'},
        {'metric': 'Purchase revenue', 'definition': 'Sum(price) for purchase events; no quantity field exists, so each purchase event contributes price once'},
    ])
    definitions.to_csv(gold / 'gold_metric_definitions.csv', index=False)

    print('LOCAL PANDAS GOLD ANALYTICS - VALIDATED EXECUTION')
    for f in sorted(gold.glob('gold_*.csv')):
        print(' -', f)
    print(f'Engagement thresholds: Low <= {q33:g}; Medium <= {q67:g}; High > {q67:g}')
    print('Scope note: these outputs were produced locally with Pandas, not by Azure Databricks/ADF.')


if __name__ == '__main__':
    main()
