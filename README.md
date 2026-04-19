# The Story Behind ROE · A DuPont Decomposition Tool on WRDS Data

*ACC102 Mini Assignment · Track 4 (Interactive Tool)*

---

## 📌 Product Demo

- **Live app**: _[link will be added after deployment to Streamlit Community Cloud]_
- **Demo video**: _[link will be added after recording]_
- **GitHub repository**: _[link will be added]_

### How the live app works

1. Open the app link in a browser
2. Enter your own WRDS credentials in the login form
3. Type 2–4 ticker symbols (e.g., `AAPL, MSFT, GOOGL`)
4. Pick a fiscal year range
5. Click **Analyze** — the app queries WRDS in real time and renders a DuPont decomposition

### ⚠️ Important: WRDS account and MFA

This app queries WRDS live, so **a valid WRDS account is required**. If your institution enforces Duo MFA (multi-factor authentication) on WRDS database connections, login through this app may fail with a `PAM authentication failed` error. In that case:

- Try again — MFA tokens can be picky about timing
- If it keeps failing, the repository can be cloned and run locally (see Section 5), which uses the same WRDS account but typically does not hit the MFA gate
- Or contact WRDS support to confirm whether your account allows PostgreSQL direct connections

---

## 1. Problem and User

**Target user**: undergraduate business / accounting students learning financial ratio analysis, and instructors who want to demonstrate how DuPont decomposition reveals business-model differences.

**Pain point**: textbooks teach ROE = Profit Margin × Asset Turnover × Equity Multiplier, but when students see a real company reporting "ROE 25%," they have no intuition — is that high? Is it driven by operational efficiency or by leverage? Textbook examples use stylized numbers, leaving a gap between theory and real companies.

**What this tool does**: the user picks 2–4 companies using standard ticker symbols, the tool pulls financial data live from WRDS and immediately shows a side-by-side DuPont decomposition. Visualizations plus natural-language commentary help the user *see through* the ROE number to understand where it comes from.

---

## 2. Data

| Item | Description |
|---|---|
| **Source** | WRDS · Compustat database · `comp.funda` table |
| **Coverage** | Any U.S.-listed company in Compustat |
| **Time range** | 2010 – 2024 (configurable via the sidebar) |
| **Key fields** | `tic`, `fyear`, `sale`, `at`, `lt`, `ceq`, `ni`, `act`, `lct` |
| **Standard filters** | `datafmt='STD'` · `consol='C'` · `indfmt='INDL'` (following W5 course guidance) |

**Cleaning**: rows with non-positive shareholders' equity are excluded (common for companies with large cumulative share buybacks, e.g., Home Depot). The app reports how many rows are excluded and why.

---

## 3. Analysis Method

The core framework is the **DuPont decomposition** — breaking ROE into three factors each with a direct business meaning:

> **ROE = Profit Margin × Asset Turnover × Equity Multiplier**

- **Profit Margin**: how much of each dollar of sales becomes profit
- **Asset Turnover**: how fast the assets generate revenue
- **Equity Multiplier**: how much leverage is being used

### Case study in the notebook: the Big Three U.S. retailers

The notebook walks through a deep analysis of three retail giants in the same industry but with distinctly different strategies:

| Ticker | Company | Business model |
|---|---|---|
| WMT | Walmart | Scale-driven low margin |
| COST | Costco | Membership-based extreme turnover |
| TGT | Target | Mid-tier differentiated premium |

The Streamlit tool generalizes this analysis: **any** ticker (or combination of 2–4 tickers) can be analyzed with the same framework.

---

## 4. Key Findings from the Retail Case Study

**Finding 1: The DuPont formula holds exactly on real data**

The difference between the three-factor product and the directly-computed ROE is at floating-point precision (`10^-15`). The formula holds unambiguously.

**Finding 2: The same ROE can mean completely different business models**

Looking at 7-year averages for the three retailers:

| Company | Profit Margin | Turnover | Equity Multiplier | ROE |
|---|---|---|---|---|
| WMT | 2.3% | 2.39 | 3.04 | **16.8%** |
| COST | 2.5% | **3.40** | 3.06 | **26.2%** |
| TGT | **4.2%** | 1.90 | **3.98** | **31.7%** |

- **Costco = Efficiency**: profit margin nearly identical to Walmart's, but turnover reaches 3.4x — a textbook case of the high-turnover business model
- **Target = Premium**: profit margin 4.2% (highest of the three), earned through store experience and private-label brands; equity multiplier also highest (3.98), showing additional leverage
- **Walmart = Balanced**: no factor is outstanding, but none is weak either — the world's largest retailer maintaining a stable ROE

**Finding 3: Financial ratios cannot be read without business context**

Home Depot had negative equity in 2018/2019/2021 — not because of operational troubles, but because of sustained massive share buybacks. Walmart's 2018 ROE of only 9.2% is explained by two one-time events (the TCJA tax reform and the Flipkart acquisition). **Single-year ratios can be badly distorted by one-time events; analysts must combine numbers with business context to avoid misleading conclusions.**

---

## 5. How to Run Locally

### 5.1 Environment setup

```bash
# Clone the repo
git clone <repo URL>
cd acc102-roe-decoded

# Install dependencies
pip install -r requirements.txt
```

### 5.2 Running the notebook

```bash
jupyter lab notebook.ipynb
```

The notebook walks through the full analytical narrative: WRDS query → cleaning → ratio computation → DuPont decomposition → visualizations → automatic insight generation. Running it top-to-bottom will also produce a local `company_financials.csv` file.

### 5.3 Running the Streamlit app

```bash
streamlit run app.py
```

The browser will open `http://localhost:8501`. Enter your own WRDS credentials in the login form, then query any combination of tickers.

---

## 6. Project Structure

```
acc102-roe-decoded/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── .gitignore                   # Excludes WRDS data and system files
│
├── notebook.ipynb               # Core analytical narrative (primary deliverable)
├── app.py                       # Streamlit live-query interactive tool
│
├── company_financials.csv       # WRDS data (kept locally, not uploaded)
│
└── reflection.md                # 500–800 word reflection + AI use disclosure
```

---

## 7. Architecture Notes

### Why does the app connect to WRDS directly (not via the `wrds` Python library)?

The official `wrds` library assumes interactive use in a Jupyter notebook and falls back to a terminal prompt when a password cannot be resolved from `~/.pgpass`. This breaks in a Streamlit web-app context. The app instead uses `sqlalchemy + psycopg2` to connect directly to the same PostgreSQL backend that the `wrds` library uses (`wrds-pgdata.wharton.upenn.edu:9737`), with credentials supplied by the user via the login form.

This is equivalent to what the `wrds` library does internally, just without the interactive prompt fallback.

### Caching

Query results are cached for 1 hour using `st.cache_data`. Repeated queries with the same ticker set and year range return instantly without re-hitting WRDS.

---

## 8. Limitations and Future Directions

**Analytical**:
- Annual data only, cannot capture within-year seasonality
- DuPont decomposition is one perspective; it does not replace cash-flow analysis, valuation, etc.
- Cases are all U.S.-listed companies (to keep accounting conventions comparable); cross-border GAAP/IFRS differences are not considered

**Tool**:
- The rule-based insight generator has limited coverage; extreme cases (persistent losses, negative equity) fall back to generic text rather than deep analysis
- No industry-median benchmark — a future version could add peer-distribution context
- MFA-protected WRDS accounts may have trouble authenticating through the direct PostgreSQL connection; this is a WRDS-side limitation, not an app issue

**Engineering**:
- No unit tests — acceptable for a small assignment, but would be needed at larger scale

---

## 9. AI Use Declaration

This project follows the "AI-assisted analysis" workflow introduced in course W6. Claude (Anthropic) was used for coding collaboration, visualization design, and insight template drafting. All AI-generated content has been read, understood, and verified by the author. Detailed disclosure is in `reflection.md`.

---

## 10. Acknowledgments

This project builds directly on the ACC102 course material from W4–W6: WRDS connections, SQL querying, pandas processing, AI-assisted analysis, and function encapsulation.

---

*ACC102 · AI-Driven Data Analytics · 2026*
