"""
The Story Behind ROE · DuPont Decomposition Tool (Live WRDS version)

This version lets the user log in with their own WRDS credentials
and query any U.S.-listed companies in real time.

Usage: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sqlalchemy

# ==========================================================================
# Page config
# ==========================================================================
st.set_page_config(
    page_title='The Story Behind ROE',
    page_icon='📊',
    layout='wide'
)

plt.rcParams['axes.unicode_minus'] = False


# ==========================================================================
# WRDS connection management
# ==========================================================================
WRDS_HOST = 'wrds-pgdata.wharton.upenn.edu'
WRDS_PORT = 9737
WRDS_DB = 'wrds'

# Connection timeout must be long enough for:
#  (1) PAM to call Duo API
#  (2) Duo to push notification to the user's phone
#  (3) User to unlock phone and tap Approve
#  (4) Duo to notify PAM, PAM to finalize authentication
# A realistic end-to-end time is 30-90 seconds. We allow 120s to be safe.
WRDS_CONNECT_TIMEOUT = 120


def connect_wrds(username, password):
    """Try to connect to the WRDS PostgreSQL database directly via SQLAlchemy.

    We bypass the wrds library's Connection class because it does not accept
    a password argument and will fall back to interactive prompts in a web
    app context.

    Returns (engine, error_message). error_message is None on success.
    """
    try:
        from urllib.parse import quote_plus
        user_esc = quote_plus(username)
        pass_esc = quote_plus(password)

        url = (
            f'postgresql+psycopg2://{user_esc}:{pass_esc}'
            f'@{WRDS_HOST}:{WRDS_PORT}/{WRDS_DB}'
            f'?sslmode=require'
        )
        engine = sqlalchemy.create_engine(
            url,
            connect_args={
                'connect_timeout': WRDS_CONNECT_TIMEOUT,
                # Keep the socket alive while waiting for Duo approval
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5,
            }
        )

        # Quick probe to verify credentials (this is what triggers the Duo push)
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text('SELECT 1'))

        return engine, None
    except Exception as e:
        return None, str(e)


def run_sql(engine, query):
    """Run a SQL query against the WRDS engine, return a DataFrame."""
    with engine.connect() as conn:
        return pd.read_sql(sqlalchemy.text(query), conn)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_financials(tickers_tuple, start_year, end_year, _engine):
    """Fetch financial data from WRDS. Cached for 1 hour per ticker set.

    Note: _engine is prefixed with underscore so Streamlit does not try to hash it.
    tickers_tuple must be a tuple (not list) for hashing.
    """
    tickers = list(tickers_tuple)
    tickers_str = "', '".join(tickers)

    sql_query = f"""
    SELECT tic, fyear, sale, at, lt, ceq, ni, act, lct
    FROM comp.funda
    WHERE tic IN ('{tickers_str}')
      AND fyear BETWEEN {start_year} AND {end_year}
      AND datafmt = 'STD'
      AND consol = 'C'
      AND indfmt = 'INDL'
    """

    data = run_sql(_engine, sql_query)
    return data


def clean_and_compute(data):
    """Rename columns, exclude negative-equity rows, compute five ratios."""
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

    excluded = data[data['equity'] <= 0][['ticker', 'year', 'equity']].copy()
    data = data[data['equity'] > 0].copy()

    data['roe'] = data['net_income'] / data['equity']
    data['profit_margin'] = data['net_income'] / data['revenue']
    data['asset_turnover'] = data['revenue'] / data['total_assets']
    data['equity_multiplier'] = data['total_assets'] / data['equity']
    data['current_ratio'] = data['current_assets'] / data['current_liabilities']

    return data, excluded


# ==========================================================================
# Analysis functions (same as notebook)
# ==========================================================================
def identify_dominant_factor(dupont_table, ticker, threshold=0.85):
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


# ==========================================================================
# Plotting functions
# ==========================================================================
def plot_three_factors(dupont_avg, companies, colors):
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))

    values_pm = (dupont_avg['profit_margin'] * 100).values
    bars1 = axes[0].bar(companies, values_pm, color=colors, width=0.6)
    axes[0].set_title('Profit Margin (%)', fontsize=12)
    axes[0].grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars1, values_pm):
        axes[0].text(bar.get_x() + bar.get_width()/2, val + 0.1,
                     f'{val:.1f}%', ha='center', fontsize=10, fontweight='bold')

    values_at = dupont_avg['asset_turnover'].values
    bars2 = axes[1].bar(companies, values_at, color=colors, width=0.6)
    axes[1].set_title('Asset Turnover (x)', fontsize=12)
    axes[1].grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars2, values_at):
        axes[1].text(bar.get_x() + bar.get_width()/2, val + 0.05,
                     f'{val:.2f}', ha='center', fontsize=10, fontweight='bold')

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


def plot_trajectories(data, companies, colors):
    """Three-factor time trajectories: one subplot per factor, one line per company."""
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2), sharex=True)

    factor_specs = [
        ('profit_margin', 'Profit Margin (%)', 100),
        ('asset_turnover', 'Asset Turnover (x)', 1),
        ('equity_multiplier', 'Equity Multiplier (x)', 1),
    ]

    color_map = dict(zip(companies, colors))

    for ax, (col, title, multiplier) in zip(axes, factor_specs):
        for ticker in companies:
            company_data = data[data['ticker'] == ticker].sort_values('year')
            if len(company_data) == 0:
                continue
            ax.plot(company_data['year'], company_data[col] * multiplier,
                    marker='o', linewidth=2.2, markersize=7,
                    label=ticker, color=color_map[ticker])
        ax.set_title(title, fontsize=12, pad=10)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=9)
        ax.set_xlabel('Fiscal Year')

    plt.tight_layout()
    return fig


def plot_attribution(data, companies, colors):
    """Year-over-year ROE change decomposed into PM / AT / EM contributions."""
    color_map = dict(zip(companies, colors))

    n = len(companies)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 4.5), sharey=True)
    if n == 1:
        axes = [axes]

    any_plotted = False

    for ax, ticker in zip(axes, companies):
        company_data = data[data['ticker'] == ticker].sort_values('year').reset_index(drop=True)

        if len(company_data) < 2:
            ax.text(0.5, 0.5, f'{ticker}\n(need \u22652 years)',
                    ha='center', va='center', transform=ax.transAxes, fontsize=11)
            ax.set_title(f'{ticker}', fontsize=12, pad=10,
                         color=color_map[ticker], fontweight='bold')
            ax.set_xticks([])
            ax.set_yticks([])
            continue

        attribution_records = []
        for i in range(1, len(company_data)):
            prev = company_data.iloc[i-1]
            curr = company_data.iloc[i]

            delta_roe_pp = (curr['roe'] - prev['roe']) * 100

            try:
                d_ln_pm = np.log(curr['profit_margin'] / prev['profit_margin'])
                d_ln_at = np.log(curr['asset_turnover'] / prev['asset_turnover'])
                d_ln_em = np.log(curr['equity_multiplier'] / prev['equity_multiplier'])
                d_ln_total = d_ln_pm + d_ln_at + d_ln_em

                if abs(d_ln_total) > 1e-9 and np.isfinite(d_ln_total):
                    pm_contrib = delta_roe_pp * (d_ln_pm / d_ln_total)
                    at_contrib = delta_roe_pp * (d_ln_at / d_ln_total)
                    em_contrib = delta_roe_pp * (d_ln_em / d_ln_total)
                else:
                    pm_contrib = at_contrib = em_contrib = 0
            except (ZeroDivisionError, ValueError):
                pm_contrib = at_contrib = em_contrib = 0

            attribution_records.append({
                'transition': f"{int(prev['year'])}\u2192{int(curr['year'])}",
                'PM': pm_contrib,
                'AT': at_contrib,
                'EM': em_contrib,
                'total': delta_roe_pp
            })

        attr_df = pd.DataFrame(attribution_records)
        x_positions = np.arange(len(attr_df))
        width = 0.6

        pm_vals = attr_df['PM'].values
        at_vals = attr_df['AT'].values
        em_vals = attr_df['EM'].values

        def stack_positive(vals):
            return np.where(vals > 0, vals, 0)
        def stack_negative(vals):
            return np.where(vals < 0, vals, 0)

        pm_pos, pm_neg = stack_positive(pm_vals), stack_negative(pm_vals)
        at_pos, at_neg = stack_positive(at_vals), stack_negative(at_vals)
        em_pos, em_neg = stack_positive(em_vals), stack_negative(em_vals)

        ax.bar(x_positions, pm_pos, width, color='#F4A261', label='Profit Margin')
        ax.bar(x_positions, at_pos, width, bottom=pm_pos, color='#2A9D8F', label='Asset Turnover')
        ax.bar(x_positions, em_pos, width, bottom=pm_pos + at_pos, color='#264653', label='Equity Multiplier')

        ax.bar(x_positions, pm_neg, width, color='#F4A261')
        ax.bar(x_positions, at_neg, width, bottom=pm_neg, color='#2A9D8F')
        ax.bar(x_positions, em_neg, width, bottom=pm_neg + at_neg, color='#264653')

        ax.plot(x_positions, attr_df['total'], 'ko-', markersize=7, linewidth=1.5,
                label='Total \u0394ROE', zorder=5)

        ax.axhline(0, color='black', linewidth=0.8)
        ax.set_xticks(x_positions)
        ax.set_xticklabels(attr_df['transition'], rotation=45, fontsize=8)
        ax.set_title(f'{ticker}', fontsize=12, pad=10,
                     color=color_map[ticker], fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        any_plotted = True

    if any_plotted:
        axes[0].set_ylabel('ROE Change (percentage points)', fontsize=10)
        axes[-1].legend(loc='upper right', fontsize=7.5, framealpha=0.9)

    plt.tight_layout()
    return fig


def plot_volatility(data, companies, colors):
    """Bar chart of ROE standard deviation per company."""
    roe_stats = (
        data[data['ticker'].isin(companies)]
        .groupby('ticker')['roe']
        .agg(['mean', 'std'])
        .reindex(companies)
    )
    # Replace NaN std (single-year data) with 0 so the bar still plots
    roe_stats['std'] = roe_stats['std'].fillna(0)
    roe_stats['mean_pct'] = roe_stats['mean'] * 100
    roe_stats['std_pct'] = roe_stats['std'] * 100

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(roe_stats.index, roe_stats['std_pct'], color=colors, width=0.55)

    for bar, val_std, val_mean in zip(bars, roe_stats['std_pct'], roe_stats['mean_pct']):
        ax.text(bar.get_x() + bar.get_width()/2, val_std + 0.3,
                f'\u03c3 = {val_std:.1f}%\n(mean {val_mean:.1f}%)',
                ha='center', fontsize=10, fontweight='bold')

    ax.set_title('ROE Volatility: Standard Deviation Across Selected Years',
                 fontsize=12, pad=15)
    ax.set_ylabel('ROE Standard Deviation (%)')
    ax.grid(True, alpha=0.3, axis='y')
    max_std = max(roe_stats['std_pct']) if len(roe_stats) > 0 else 1
    ax.set_ylim(0, max(max_std * 1.4, 1))

    plt.tight_layout()
    return fig


def plot_current_ratio(data, companies, colors):
    """Current ratio time series per company, with liquidity threshold at 1.0."""
    color_map = dict(zip(companies, colors))

    fig, ax = plt.subplots(figsize=(10, 4.5))

    for ticker in companies:
        company_data = data[data['ticker'] == ticker].sort_values('year')
        if len(company_data) == 0:
            continue
        ax.plot(company_data['year'], company_data['current_ratio'],
                marker='o', linewidth=2.5, markersize=9,
                label=ticker, color=color_map[ticker])

    ax.axhline(y=1.0, color='gray', linestyle='--', linewidth=1.2, alpha=0.7,
               label='Current Ratio = 1 (liquidity threshold)')

    ax.set_title('Current Ratio: Short-Term Liquidity', fontsize=13, pad=15)
    ax.set_xlabel('Fiscal Year', fontsize=11)
    ax.set_ylabel('Current Ratio (x)', fontsize=11)
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


# ==========================================================================
# UI: Login gate
# ==========================================================================
st.title('📊 The Story Behind ROE')
st.caption('A DuPont decomposition tool on WRDS data · ACC102 Mini Assignment')

if 'engine' not in st.session_state:
    st.session_state.engine = None

if st.session_state.engine is None:
    st.markdown('### WRDS Login')
    st.info(
        'This tool queries Compustat data in real time via WRDS. '
        'Please enter your own WRDS credentials. '
        'Your password is used only for this session and is never stored.'
    )
    st.warning(
        '**📱 Heads up — WRDS requires Duo Push for database connections.**  \n'
        '1. Have your phone ready with the Duo Mobile app open  \n'
        '2. After clicking **Log in**, wait for a Duo push notification (may take 10–30 seconds)  \n'
        '3. Tap **Approve** on your phone  \n'
        '4. The app will automatically continue once approved  \n'
        'If you don\'t receive a push within 60 seconds, it may mean your account uses a '
        'different MFA method — please contact WRDS support.'
    )

    with st.form('login_form'):
        wrds_user = st.text_input('WRDS username')
        wrds_pass = st.text_input('WRDS password', type='password')
        login_btn = st.form_submit_button('Log in')

    if login_btn:
        if not wrds_user or not wrds_pass:
            st.error('Please enter both username and password.')
        else:
            with st.spinner('Connecting to WRDS... Please check your phone for a Duo push and tap Approve.'):
                engine, err = connect_wrds(wrds_user, wrds_pass)
            if err:
                st.error(f'Login failed: {err}')
                st.caption(
                    'Common causes: (1) Duo push timed out — try again and approve faster; '
                    '(2) your account does not have Duo Push enabled for PostgreSQL connections; '
                    '(3) wrong password.'
                )
            else:
                st.session_state.engine = engine
                st.success('Connected. Redirecting...')
                st.rerun()

    st.stop()


# ==========================================================================
# UI: Main analysis interface
# ==========================================================================
engine = st.session_state.engine

with st.sidebar:
    st.markdown('### Session')
    if st.button('Log out'):
        try:
            engine.dispose()
        except Exception:
            pass
        st.session_state.engine = None
        st.rerun()
    st.markdown('---')

st.sidebar.header('Analysis Parameters')

ticker_input = st.sidebar.text_area(
    'Enter 2–4 U.S. ticker symbols (comma- or space-separated)',
    value='WMT, COST, TGT',
    height=80,
    help='Example: AAPL, MSFT, GOOGL. Use ticker symbols as they appear in Compustat.'
)

year_range = st.sidebar.slider(
    'Fiscal year range',
    min_value=2010,
    max_value=2024,
    value=(2018, 2024)
)

run_btn = st.sidebar.button('Analyze', type='primary')

raw = ticker_input.replace(',', ' ').split()
tickers = [t.strip().upper() for t in raw if t.strip()]

if not run_btn:
    st.markdown(
        '### How to use\n'
        '1. Enter 2–4 U.S. ticker symbols in the sidebar (e.g., `AAPL, MSFT, GOOGL`)\n'
        '2. Pick a fiscal year range\n'
        '3. Click **Analyze**\n\n'
        'The tool will fetch the data live from WRDS, compute a multi-dimensional DuPont analysis, '
        'and generate six charts plus automated commentary:\n\n'
        '- DuPont three-factor comparison\n'
        '- Factor trajectories over time\n'
        '- Year-over-year ROE attribution\n'
        '- Business model fingerprints (radar)\n'
        '- ROE volatility\n'
        '- Short-term liquidity (current ratio)\n'
    )
    st.stop()

if len(tickers) < 2:
    st.warning('Please enter at least 2 ticker symbols.')
    st.stop()

if len(tickers) > 4:
    st.warning('Please enter at most 4 ticker symbols for chart clarity.')
    st.stop()

with st.spinner(f'Fetching data for {", ".join(tickers)} from WRDS...'):
    try:
        raw_data = fetch_financials(tuple(tickers), year_range[0], year_range[1], engine)
    except Exception as e:
        st.error(f'WRDS query failed: {e}')
        st.stop()

if raw_data is None or len(raw_data) == 0:
    st.error(
        'No data returned. Check that your ticker symbols are valid Compustat tickers '
        'and that data is available in the selected year range.'
    )
    st.stop()

data, excluded = clean_and_compute(raw_data)

available_tickers = set(data['ticker'].unique())
missing = [t for t in tickers if t not in available_tickers]

if missing:
    st.warning(
        f'No valid data found for: {", ".join(missing)}. '
        f'These tickers may not be in Compustat or may have negative equity throughout the period.'
    )

if len(available_tickers) < 2:
    st.error('Fewer than 2 companies have valid data. Cannot produce a comparison.')
    st.stop()

selected_tickers = [t for t in tickers if t in available_tickers]

if len(excluded) > 0:
    with st.expander(f'Note: {len(excluded)} rows excluded (negative equity)'):
        st.caption(
            'Rows with non-positive shareholders\' equity are excluded because '
            'ROE becomes a meaningless negative number when equity is negative. '
            'This is often due to large cumulative share buybacks (e.g., Home Depot).'
        )
        st.dataframe(excluded, use_container_width=True)

dupont_avg = data[data['ticker'].isin(selected_tickers)].groupby('ticker').agg({
    'profit_margin': 'mean',
    'asset_turnover': 'mean',
    'equity_multiplier': 'mean',
    'roe': 'mean'
}).reindex(selected_tickers)

color_palette = ['#FF6B35', '#004E89', '#E63946', '#2A9D8F',
                 '#F4A261', '#264653', '#A663CC', '#E9C46A',
                 '#E76F51', '#8338EC']
colors = color_palette[:len(selected_tickers)]

# Only keep rows that are for selected tickers (used by time-series plots)
data_selected = data[data['ticker'].isin(selected_tickers)].copy()

st.markdown(f'### Results: {year_range[0]} – {year_range[1]}')

# ----- Chart 1: Three-factor static comparison -----
st.markdown('#### 1. DuPont Three-Factor Comparison')
st.caption('Average values across the selected year range')
fig1 = plot_three_factors(dupont_avg, selected_tickers, colors)
st.pyplot(fig1)

# ----- Chart 2: Three-factor trajectories over time -----
st.markdown('#### 2. Factor Trajectories Over Time')
st.caption('How each DuPont factor evolves year by year — reveals whether business models are stable or shifting')
fig2 = plot_trajectories(data_selected, selected_tickers, colors)
st.pyplot(fig2)

# ----- Chart 3: Year-over-year ROE attribution -----
st.markdown('#### 3. Year-over-Year ROE Attribution')
st.caption(
    'What drove each change in ROE? Log-difference decomposition attributes each year-to-year ROE change '
    'to profit margin, asset turnover, and equity multiplier.'
)
fig3 = plot_attribution(data_selected, selected_tickers, colors)
st.pyplot(fig3)

# ----- Chart 4: Business-model fingerprints (radar) -----
st.markdown('#### 4. Business Model "Fingerprints"')
st.caption('Each factor is normalized to the group maximum; shape differences reflect business-model differences')
fig4 = plot_radar(dupont_avg, selected_tickers, colors)
st.pyplot(fig4)

# ----- Chart 5: ROE volatility -----
st.markdown('#### 5. ROE Volatility')
st.caption('Standard deviation of ROE across the selected years — low volatility = steady compounding')
fig5 = plot_volatility(data_selected, selected_tickers, colors)
st.pyplot(fig5)

# ----- Chart 6: Current ratio -----
st.markdown('#### 6. Short-Term Liquidity (Current Ratio)')
st.caption(
    'Current ratio = current assets ÷ current liabilities. '
    'Retailers often run below 1.0 by design (fast cash collection, slow supplier payments).'
)
fig6 = plot_current_ratio(data_selected, selected_tickers, colors)
st.pyplot(fig6)

# ----- Commentary -----
st.markdown('#### Auto-Generated Business Commentary')
insight = generate_insights(dupont_avg)
st.markdown(insight)

with st.expander('Show raw data table'):
    st.dataframe(
        data_selected[
            ['ticker', 'year', 'revenue', 'net_income',
             'equity', 'roe', 'profit_margin',
             'asset_turnover', 'equity_multiplier', 'current_ratio']
        ].round(3),
        use_container_width=True
    )
