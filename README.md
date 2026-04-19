# The Story Behind ROE · A DuPont Decomposition Tool on WRDS Data

*ACC102 Mini Assignment · Track 4 (Interactive Tool)*

---

## 📌 Product Demo

- **Live app**: https://acc102-roe-decoded-5ieqygutyahcimlpjrq8fh.streamlit.app/
- **Demo video**: _[link will be added after recording]_
- **GitHub repository**: https://github.com/mainiyang/acc102-roe-decoded

---

## 🎯 For the Grader — How to Use the Live App

The app is deployed publicly. To evaluate it live, please follow these steps:

### Prerequisites

1. **A WRDS account** — the app queries Compustat in real time
2. **Duo Mobile app installed on your phone** — WRDS requires Duo Push for PostgreSQL database connections
3. **Your phone nearby** with a stable internet connection

### Step-by-step

1. **Open the app link** above in any modern browser
2. **Enter your WRDS credentials** in the login form and click **Log in**
3. **Check your phone immediately** — a Duo Push notification will arrive within 5-20 seconds
4. **Approve the push** on your phone within ~60 seconds (otherwise the connection times out)
5. Once approved, the app transitions to the main analysis screen
6. **Enter 2–4 U.S. ticker symbols** (e.g., `WMT, COST, TGT` or `AAPL, MSFT, GOOGL`) in the sidebar
7. **Adjust the fiscal year range** if you want (default is 2018–2024)
8. Click **Analyze**. The app will query WRDS (10–30 seconds) and render:
   - Three-factor DuPont comparison (bar charts)
   - Business model "fingerprints" (radar charts)
   - Auto-generated English commentary
   - Raw data table (expandable)

### Troubleshooting

- **"PAM authentication failed"**: Your Duo Push request wasn't approved in time, or your account doesn't have Duo Push enabled. Retry with your phone ready. Note that SMS-based MFA is *not* supported for WRDS PostgreSQL connections — only Duo Push works.
- **"No data returned"**: Double-check the ticker symbols are valid Compustat tickers and that data exists in the chosen year range.
- **Want to skip the live login?** Clone the GitHub repo and run locally — see Section 5 below.

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
git clone https://github.com/mainiyang/acc102-roe-decoded
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
├── runtime.txt                  # Pins Python 3.11 for deployment
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

### Why connect to WRDS directly (not via the `wrds` Python library)?

The official `wrds` library assumes interactive use in a Jupyter notebook and falls back to a terminal prompt when a password cannot be resolved from `~/.pgpass`. This breaks in a Streamlit web-app context — there's no terminal for the library to prompt into.

The app instead uses `sqlalchemy + psycopg2` to connect directly to the same PostgreSQL backend that the `wrds` library uses (`wrds-pgdata.wharton.upenn.edu:9737`), with credentials supplied by the user via the web login form. This is equivalent to what the `wrds` library does internally, just without the interactive prompt fallback.

### How does the app handle WRDS's Duo MFA?

WRDS requires Duo Push for all PostgreSQL connections. When the user clicks "Log in" with valid credentials, WRDS automatically sends a push notification to the user's registered Duo Mobile device. The PostgreSQL connection waits for the user to approve the push, then completes. This is the **intended** MFA flow for automated WRDS access — the app does not try to bypass it.

### Caching

Query results are cached for 1 hour using `st.cache_data`. Repeated queries with the same ticker set and year range return instantly without re-hitting WRDS, which is useful when the grader wants to adjust the year-range slider and see different averages without re-authenticating.

### Deployment notes

The app is deployed to **Streamlit Community Cloud** with Python 3.11 (pinned in both `runtime.txt` and via the "Advanced settings" dialog during app creation, because Streamlit Cloud currently ignores `runtime.txt` alone). `psycopg2-binary` requires Python 3.11 — newer Python versions (3.13+) lack pre-built wheels and fail to compile in the Cloud's build environment.

---

## 8. Limitations and Future Directions

**Analytical**:
- Annual data only, cannot capture within-year seasonality
- DuPont decomposition is one perspective; it does not replace cash-flow analysis, valuation, etc.
- Cases are all U.S.-listed companies (to keep accounting conventions comparable); cross-border GAAP/IFRS differences are not considered

**Tool**:
- The rule-based insight generator has limited coverage; extreme cases (persistent losses, negative equity) fall back to generic text rather than deep analysis
- No industry-median benchmark — a future version could add peer-distribution context
- Every user must have their own WRDS account with Duo Push enabled, which creates a friction point for any user who has not previously used WRDS programmatically

**Engineering**:
- No unit tests — acceptable for a small assignment, but would be needed at larger scale
- Each deployed session holds an open PostgreSQL connection until the user logs out or the session expires; at higher user volumes a connection pool with cleanup would be needed

---

## 9. AI Use Declaration

This project follows the "AI-assisted analysis" workflow introduced in course W6. Claude (Anthropic) was used for coding collaboration, visualization design, and insight template drafting. All AI-generated content has been read, understood, and verified by the author. Detailed disclosure is in `reflection.md`.

---

## 10. Acknowledgments

This project builds directly on the ACC102 course material from W4–W6: WRDS connections, SQL querying, pandas processing, AI-assisted analysis, and function encapsulation.

---

*ACC102 · AI-Driven Data Analytics · 2026*
