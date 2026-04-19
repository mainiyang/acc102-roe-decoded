"""
ROE 背后的故事 · 杜邦分解对比工具

Streamlit 交互式工具入口。
使用方式: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==========================================================================
# 页面配置
# ==========================================================================
st.set_page_config(
    page_title='ROE 背后的故事',
    page_icon='📊',
    layout='wide'
)

# matplotlib 中文支持
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# ==========================================================================
# 公司池（和 notebook 里保持一致）
# ==========================================================================
COMPANY_POOL = {
    'WMT':   'Walmart · 沃尔玛',
    'COST':  'Costco · 好市多',
    'TGT':   'Target · 塔吉特',
    'HD':    'Home Depot · 家得宝',
    'AAPL':  'Apple · 苹果',
    'MSFT':  'Microsoft · 微软',
    'GOOGL': 'Alphabet · 谷歌',
    'KO':    'Coca-Cola · 可口可乐',
    'PEP':   'PepsiCo · 百事',
    'NKE':   'Nike · 耐克',
}


# ==========================================================================
# 数据加载与处理函数
# ==========================================================================
@st.cache_data
def load_data():
    """读取缓存的 WRDS 数据并做清洗。"""
    data = pd.read_csv('company_financials.csv')
    
    # 重命名列，和 notebook 保持一致
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
    
    # 排除股东权益为负的异常行
    data = data[data['equity'] > 0].copy()
    
    # 计算五大比率
    data['roe'] = data['net_income'] / data['equity']
    data['profit_margin'] = data['net_income'] / data['revenue']
    data['asset_turnover'] = data['revenue'] / data['total_assets']
    data['equity_multiplier'] = data['total_assets'] / data['equity']
    data['current_ratio'] = data['current_assets'] / data['current_liabilities']
    
    return data


def identify_dominant_factor(dupont_table, ticker, threshold=0.85):
    """判断一家公司的杜邦特征类型。"""
    pm_norm = dupont_table['profit_margin'] / dupont_table['profit_margin'].max()
    at_norm = dupont_table['asset_turnover'] / dupont_table['asset_turnover'].max()
    em_norm = dupont_table['equity_multiplier'] / dupont_table['equity_multiplier'].max()
    
    factors = {
        '净利率': pm_norm[ticker],
        '周转率': at_norm[ticker],
        '权益乘数': em_norm[ticker]
    }
    
    dominant_factor = max(factors, key=factors.get)
    dominant_value = factors[dominant_factor]
    
    if dominant_value < threshold:
        return '均衡型', None
    
    tag_map = {
        '净利率': '溢价型',
        '周转率': '效率型',
        '权益乘数': '杠杆型'
    }
    
    return tag_map[dominant_factor], dominant_factor


def generate_insights(dupont_table):
    """给定杜邦分解表，生成一段中文业务解读（返回 Markdown 字符串）。"""
    tickers = dupont_table.index.tolist()
    lines = []
    
    roe_ranked = dupont_table['roe'].sort_values(ascending=False)
    top_company = roe_ranked.index[0]
    top_roe = roe_ranked.iloc[0] * 100
    bottom_company = roe_ranked.index[-1]
    bottom_roe = roe_ranked.iloc[-1] * 100
    
    lines.append(
        f'在所选的 {len(tickers)} 家公司中，**{top_company}** 的 ROE 最高'
        f'（{top_roe:.1f}%），**{bottom_company}** 最低（{bottom_roe:.1f}%）。'
    )
    lines.append('但 ROE 的数字只是结果——杜邦分解才能告诉我们每家公司"怎么赚到的"。\n')
    
    lines.append('**各公司的杜邦特征：**\n')
    for ticker in tickers:
        tag, factor_name = identify_dominant_factor(dupont_table, ticker)
        pm = dupont_table.loc[ticker, 'profit_margin'] * 100
        at = dupont_table.loc[ticker, 'asset_turnover']
        em = dupont_table.loc[ticker, 'equity_multiplier']
        roe_pct = dupont_table.loc[ticker, 'roe'] * 100
        
        if factor_name is None:
            lines.append(
                f'- **{ticker}（{tag}）**：'
                f'净利率 {pm:.1f}%，周转率 {at:.2f}，权益乘数 {em:.2f} → '
                f'ROE = {roe_pct:.1f}%。三个因子相对均衡，没有单一突出驱动。'
            )
        else:
            lines.append(
                f'- **{ticker}（{tag}）**：'
                f'净利率 {pm:.1f}%，周转率 {at:.2f}，权益乘数 {em:.2f} → '
                f'ROE = {roe_pct:.1f}%。其 ROE 的主要驱动是**{factor_name}**。'
            )
    
    lines.append('')
    
    # 识别 ROE 相近但驱动因子不同的对子
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
        lines.append('**关键洞察：**\n')
        for t1, t2, f1, f2 in similar_pairs:
            lines.append(
                f'- **{t1} 和 {t2} 的 ROE 数字相近，但驱动因子完全不同**：'
                f'{t1} 靠 **{f1}**，{t2} 靠 **{f2}**。'
                f'这正是杜邦分解最经典的场景——同样的回报率背后是完全不同的商业模式。'
            )
    
    return '\n'.join(lines)


def plot_three_factors(dupont_avg, companies, colors):
    """画三因子对比柱状图。"""
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    
    # 净利率
    values_pm = (dupont_avg['profit_margin'] * 100).values
    bars1 = axes[0].bar(companies, values_pm, color=colors, width=0.6)
    axes[0].set_title('净利率 (%)', fontsize=12)
    axes[0].grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars1, values_pm):
        axes[0].text(bar.get_x() + bar.get_width()/2, val + 0.1,
                     f'{val:.1f}%', ha='center', fontsize=10, fontweight='bold')
    
    # 周转率
    values_at = dupont_avg['asset_turnover'].values
    bars2 = axes[1].bar(companies, values_at, color=colors, width=0.6)
    axes[1].set_title('资产周转率 (倍)', fontsize=12)
    axes[1].grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars2, values_at):
        axes[1].text(bar.get_x() + bar.get_width()/2, val + 0.05,
                     f'{val:.2f}', ha='center', fontsize=10, fontweight='bold')
    
    # 权益乘数
    values_em = dupont_avg['equity_multiplier'].values
    bars3 = axes[2].bar(companies, values_em, color=colors, width=0.6)
    axes[2].set_title('权益乘数 (倍)', fontsize=12)
    axes[2].grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars3, values_em):
        axes[2].text(bar.get_x() + bar.get_width()/2, val + 0.05,
                     f'{val:.2f}', ha='center', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    return fig


def plot_radar(dupont_avg, companies, colors):
    """画三家公司的商业模式雷达图。"""
    pm_norm = dupont_avg['profit_margin'] / dupont_avg['profit_margin'].max()
    at_norm = dupont_avg['asset_turnover'] / dupont_avg['asset_turnover'].max()
    em_norm = dupont_avg['equity_multiplier'] / dupont_avg['equity_multiplier'].max()
    
    categories = ['净利率', '周转率', '权益乘数']
    num_vars = len(categories)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]
    
    n_companies = len(companies)
    fig, axes = plt.subplots(1, n_companies, figsize=(4 * n_companies, 4),
                              subplot_kw=dict(projection='polar'))
    
    # 如果只有一家公司，axes 不是数组
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
# 主界面
# ==========================================================================
st.title('📊 ROE 背后的故事')
st.caption('基于 WRDS 数据的杜邦分解对比工具 · ACC102 Mini Assignment')

# 加载数据
try:
    data = load_data()
except FileNotFoundError:
    st.error('❌ 找不到 company_financials.csv。请先运行 notebook 生成数据文件。')
    st.stop()

# --- 侧边栏：用户控件 ---
st.sidebar.header('分析参数')

selected_tickers = st.sidebar.multiselect(
    '选择要对比的公司（2–4 家）',
    options=list(COMPANY_POOL.keys()),
    default=['WMT', 'COST', 'TGT'],
    format_func=lambda x: f'{x} — {COMPANY_POOL[x]}'
)

year_range = st.sidebar.slider(
    '财年范围',
    min_value=int(data['year'].min()),
    max_value=int(data['year'].max()),
    value=(int(data['year'].min()), int(data['year'].max()))
)

# 输入校验
if len(selected_tickers) < 2:
    st.warning('⚠️ 请至少选择 2 家公司进行对比。')
    st.stop()

if len(selected_tickers) > 4:
    st.warning('⚠️ 为了图表清晰，建议最多选择 4 家公司。')

# --- 过滤数据 ---
filtered = data[
    (data['ticker'].isin(selected_tickers)) &
    (data['year'] >= year_range[0]) &
    (data['year'] <= year_range[1])
]

if len(filtered) == 0:
    st.error('所选条件下没有可用数据。')
    st.stop()

# --- 计算每家公司的平均值（用于杜邦对比） ---
dupont_avg = filtered.groupby('ticker').agg({
    'profit_margin': 'mean',
    'asset_turnover': 'mean',
    'equity_multiplier': 'mean',
    'roe': 'mean'
}).reindex(selected_tickers)

# 颜色池
color_palette = ['#FF6B35', '#004E89', '#E63946', '#2A9D8F',
                 '#F4A261', '#264653', '#A663CC', '#E9C46A',
                 '#E76F51', '#8338EC']
colors = color_palette[:len(selected_tickers)]

# --- 主区域渲染 ---
st.markdown(f'### 分析结果：{year_range[0]} – {year_range[1]} 年平均')

# 三因子对比柱状图
st.markdown('#### 杜邦三因子对比')
fig1 = plot_three_factors(dupont_avg, selected_tickers, colors)
st.pyplot(fig1)

# 雷达图
st.markdown('#### 商业模式"指纹"')
st.caption('各因子已归一化到同组最大值，形状差异反映商业模式差异')
fig2 = plot_radar(dupont_avg, selected_tickers, colors)
st.pyplot(fig2)

# 自动文字洞察
st.markdown('#### 自动生成的业务解读')
insight = generate_insights(dupont_avg)
st.markdown(insight)

# 数据表（可展开）
with st.expander('查看原始数据表'):
    st.dataframe(
        filtered[['ticker', 'year', 'revenue', 'net_income',
                  'equity', 'roe', 'profit_margin',
                  'asset_turnover', 'equity_multiplier']].round(3),
        use_container_width=True
    )