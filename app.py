"""
The Story Behind ROE · DuPont Decomposition Tool

Streamlit interactive entry point.
Usage: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==========================================================================
# Page config
# ==========================================================================
st.set_page_config(
    page_title='The Story Behind ROE',
    page_icon='📊',
    layout='wide'
)

# matplotlib: avoid unicode-minus display issues
plt.rcParams['axes.unicode_minus'] = False

# ==========================================================================
# Company pool (kept consistent with the notebook)
# ==========================================================================
COMPANY_POOL = {
    'WMT':   'Walmart',
    'COST':  'Costco',
    'TGT':   'Target',
    'HD':    'Home Depot',
    'AAPL':  'Apple',
    'MSFT':  'Microsoft',
    'GOOGL': 'Alphabet (Google)',
    'KO':    'Coca-Cola',
    'PEP':   'PepsiCo',
    'NKE':   'Nike',
}


# ==========================================================================
# Data loading and processing
# ==========================================================================
@st.cache_data
def load_data():
    """Load the cached WRDS data and run the cleaning steps."""
    data = pd.read_csv('company_financials.csv')

    # Rename columns (consistent with the notebook)
    data = data.rename(columns={
        'tic': 'ticker',
        'fyear': 'year',
        'sale': 'revenue',
        'at': 'total_assets',
        'lt': 'total_liabilities',
        'ceq': 'equity',
        'ni': 'net_income',
        'act': 'current_assets',
        'lct': 'current_liabilities'
    })

    # Exclude rows with non-positive equity
    data = data[data['equity'] > 0].copy()

    # Compute the five ratios
    data['roe'] = data['net_income'] / data['equity']
    data['profit_margin'] = data['net_income'] / data['revenue']
    data['asset_turnover'] = data['revenue'] / data['total_assets']
    data['equity_multiplier'] = data['total_assets'] / data['equity']
    data['current_ratio'] = data['current_assets'] / data['current_liabilities']

    return data


def identify_dominant_factor(dupont_table, ticker, threshold=0.85):
    """Return a DuPont characteristic type for the given ticker.

    A factor counts as "dominant" only if its normalized value >= threshold.
    If no factor clears the threshold, the company is tagged 'Balanced'.
    """
    pm_norm = dupont_table['profit_margin']     / dupont_table['profit_margin'].max()
    at_norm = dupont_table['asset_turnover']    / dupont_table['asset_turnover'].max()
    em_norm = dupont_table['equity_multiplier'] / dupont_table['equity_multiplier'].max()

    factors = {
        'Profit Margin':     pm_norm[ticker],
        'Asset Turnover':    at_norm[ticker],
        'Equity Multiplier': em_norm[ticker]
    }

    dominant_factor = max(factors, key=factors.get)
    dominant_value = factors[dominant_factor]

    if dominant_value < threshold:
        return 'Balanced', None

    tag_map = {
        'Profit Margin':     'Premium',
        'Asset Turnover':    'Efficiency',
        'Equity Multiplier': 'Leverage'
    }

    return tag_map[dominant_factor], dominant_factor


def generate_insights(dupont_table):
    """Given a DuPont table, produce an English business commentary
    as a Markdown string."""
    tickers = dupont_table.index.tolist()
    lines = []

    roe_ranked = dupont_table['roe'].sort_values(ascending=False)
    top_company = roe_ranked.index[0]
    top_roe = roe_ranked.iloc[0] * 100
    bottom_company = roe_ranked.index[-1]
    bottom_roe = roe_ranked.iloc[-1] * 100

    lines.append(
        f'Among the {len(tickers)} selected companies, **{top_company}** has the highest ROE '
        f'({top_roe:.1f}%), while **{bottom_company}** has the lowest ({bottom_roe:.1f}%).'
    )
    lines.append('But ROE is only the result — the DuPont decomposition tells us *how* each company got there.\n')

    lines.append('**DuPont characteristics by company:**\n')
    for ticker in tickers:
        tag, factor_name = identify_dominant_factor(dupont_table, ticker)
        pm = dupont_table.loc[ticker, 'profit_margin'] * 100
        at = dupont_table.loc[ticker, 'asset_turnover']
        em = dupont_table.loc[ticker, 'equity_multiplier']
        roe_pct = dupont_table.loc[ticker, 'roe'] * 100

        if factor_name is None:
            lines.append(
                f"- **{ticker} ({tag})**: "
                f"Profit Margin {pm:.1f}%, Turnover {at:.2f}, Equity Multiplier {em:.2f} -> "
                f"ROE = {roe_pct:.1f}%. The three factors are relatively balanced, with no single dominant driver."
            )
        else:
            lines.append(
                f"- **{ticker} ({tag})**: "
                f"Profit Margin {pm:.1f}%, Turnover {at:.2f}, Equity Multiplier {em:.2f} -> "
                f"ROE = {roe_pct:.1f}%. The primary driver of this company's ROE is **{factor_name}**."
            )

    lines.append('')

    # Flag pairs with similar ROE but different drivers
    roe_values = dupont_table['roe']
    similar_pairs = []
    for i, t1 in enumerate(tickers):
        for t2 in tickers[i+1:]:
            roe_diff_pct = abs(roe_values[t1] - roe_values[t2]) / max(abs(roe_values[t1]), abs(roe_values[t2]))
            if roe_diff_pct < 0.20:
                tag1, f1 = identify_dominant_factor(dupont_table, t1)
                tag2, f2 = identify_dominant_factor(dupont_table, t2)
                if f1 is not None and f2 is not None and f1 != f2:
                    similar_pairs.append((t1, t2, f1, f2))

    if similar_pairs:
        lines.append('**Key insight:**\n')
        for t1, t2, f1, f2 in similar_pairs:
            lines.append(
                f'- **{t1} and {t2} have similar ROE but completely different drivers**: '
                f'{t1} relies on **{f1}**, while {t2} relies on **{f2}**. '
                f'This is precisely the classic DuPont scenario — the same return on equity '
                f'can sit on top of fundamentally different business models.'
            )

    return '\n'.join(lines)


def plot_three_factors(dupont_avg, companies, colors):
    """Bar chart comparing the three DuPont factors across companies."""
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))

    # Profit margin
    values_pm = (dupont_avg['profit_margin'] * 100).values
    bars1 = axes[0].bar(companies, values_pm, color=colors, width=0.6)
    axes[0].set_title('Profit Margin (%)', fontsize=12)
    axes[0].grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars1, values_pm):
        axes[0].text(bar.get_x() + bar.get_width()/2, val + 0.1,
                     f'{val:.1f}%', ha='center', fontsize=10, fontweight='bold')

    # Asset turnover
    values_at = dupont_avg['asset_turnover'].values
    bars2 = axes[1].bar(companies, values_at, color=colors, width=0.6)
    axes[1].set_title('Asset Turnover (x)', fontsize=12)
    axes[1].grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars2, values_at):
        axes[1].text(bar.get_x() + bar.get_width()/2, val + 0.05,
                     f'{val:.2f}', ha='center', fontsize=10, fontweight='bold')

    # Equity multiplier
    values_em = dupont_avg['equity_multiplier'].values
    bars3 = axes[2].bar(companies, values_em, color=colors, width=0.6)
    axes[2].set_title('Equity Multiplier (x)', fontsize=12)
    axes[2].grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars3, values_em):
        axes[2].text(bar.get_x() + bar.get_width()/2, val + 0.05,
                     f'{val:.2f}', ha='center', fontsize=10, fontweight='bold')

    plt.tight_layout()
    return fig


def plot_radar(dupont_avg, companies, colors):
    """Radar (spider) charts, one per company, showing business-model 'fingerprints'."""
    pm_norm = dupont_avg['profit_margin']     / dupont_avg['profit_margin'].max()
    at_norm = dupont_avg['asset_turnover']    / dupont_avg['asset_turnover'].max()
    em_norm = dupont_avg['equity_multiplier'] / dupont_avg['equity_multiplier'].max()

    categories = ['Profit Margin', 'Asset Turnover', 'Equity Multiplier']
    num_vars = len(categories)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    n_companies = len(companies)
    fig, axes = plt.subplots(1, n_companies, figsize=(4 * n_companies, 4),
                              subplot_kw=dict(projection='polar'))

    # If only one company, axes is not iterable
    if n_companies == 1:
        axes = [axes]

    for i, ticker in enumerate(companies):
        values = [pm_norm[ticker], at_norm[ticker], em_norm[ticker]]
        values += values[:1]

        ax = axes[i]
        ax.plot(angles, values, color=colors[i], linewidth=2.5)
        ax.fill(angles, values, color=colors[i], alpha=0.25)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=10)
        ax.set_ylim(0, 1.1)
        ax.set_yticklabels([])
        ax.grid(True, alpha=0.4)
        ax.set_title(ticker, fontsize=12, pad=15,
                     color=colors[i], fontweight='bold')

    plt.tight_layout()
    return fig


# ==========================================================================
# Main UI
# ==========================================================================
st.title('📊 The Story Behind ROE')
st.caption('A DuPont decomposition tool on WRDS data · ACC102 Mini Assignment')

# Load data
try:
    data = load_data()
except FileNotFoundError:
    st.error('❌ company_financials.csv not found. Please run the notebook first to generate the data file.')
    st.stop()

# --- Sidebar: user controls ---
st.sidebar.header('Analysis Parameters')

selected_tickers = st.sidebar.multiselect(
    'Select companies to compare (2–4)',
    options=list(COMPANY_POOL.keys()),
    default=['WMT', 'COST', 'TGT'],
    format_func=lambda x: f'{x} — {COMPANY_POOL[x]}'
)

year_range = st.sidebar.slider(
    'Fiscal year range',
    min_value=int(data['year'].min()),
    max_value=int(data['year'].max()),
    value=(int(data['year'].min()), int(data['year'].max()))
)

# Input validation
if len(selected_tickers) < 2:
    st.warning('⚠️ Please select at least 2 companies to compare.')
    st.stop()

if len(selected_tickers) > 4:
    st.warning('⚠️ For chart clarity, please select at most 4 companies.')

# --- Filter data ---
filtered = data[
    (data['ticker'].isin(selected_tickers)) &
    (data['year'] >= year_range[0]) &
    (data['year'] <= year_range[1])
]

if len(filtered) == 0:
    st.error('No data available for the selected filters.')
    st.stop()

# --- Compute per-company averages for DuPont ---
dupont_avg = filtered.groupby('ticker').agg({
    'profit_margin': 'mean',
    'asset_turnover': 'mean',
    'equity_multiplier': 'mean',
    'roe': 'mean'
}).reindex(selected_tickers)

# Color palette
color_palette = ['#FF6B35', '#004E89', '#E63946', '#2A9D8F',
                 '#F4A261', '#264653', '#A663CC', '#E9C46A',
                 '#E76F51', '#8338EC']
colors = color_palette[:len(selected_tickers)]

# --- Main content ---
st.markdown(f'### Results: {year_range[0]} – {year_range[1]} average')

# Three-factor bar chart
st.markdown('#### DuPont Three-Factor Comparison')
fig1 = plot_three_factors(dupont_avg, selected_tickers, colors)
st.pyplot(fig1)

# Radar chart
st.markdown('#### Business Model "Fingerprints"')
st.caption('Each factor is normalized to the group maximum; shape differences reflect business-model differences')
fig2 = plot_radar(dupont_avg, selected_tickers, colors)
st.pyplot(fig2)

# Auto-generated insight
st.markdown('#### Auto-Generated Business Commentary')
insight = generate_insights(dupont_avg)
st.markdown(insight)

# Raw data (collapsible)
with st.expander('Show raw data table'):
    st.dataframe(
        filtered[['ticker', 'year', 'revenue', 'net_income',
                  'equity', 'roe', 'profit_margin',
                  'asset_turnover', 'equity_multiplier']].round(3),
        use_container_width=True
    )
