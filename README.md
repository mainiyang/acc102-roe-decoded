# The Story Behind ROE · A DuPont Decomposition Tool on WRDS Data

*ACC102 Mini Assignment · Track 4 (Interactive Tool)*

---

## 📌 Product Demo

- **Demo video**: _[link will be added after recording]_
- **Local run**: see Section 5 "How to Run" below
- **Note:** WRDS data is subject to licensing restrictions and is not uploaded to this repository. The grader can reproduce the data by running `notebook.ipynb` with their own WRDS account, then launching the local Streamlit app for the full interactive experience.

---

## 1. Problem and User

**Target user**: undergraduate business / accounting students learning financial ratio analysis.

**Pain point**: textbooks teach ROE = Profit Margin × Asset Turnover × Equity Multiplier, but when students see a real company reporting "ROE 25%," they have no intuition — is that high? Is it driven by operational efficiency or by leverage? Textbook examples use stylized numbers, leaving a gap between theory and real companies.

**What this tool does**: the user picks 2–4 companies, and the tool immediately shows a side-by-side DuPont decomposition. Visualizations plus natural-language commentary help the user *see through* the ROE number to understand where it comes from.

---

## 2. Data

| Item | Description |
|---|---|
| **Source** | WRDS · Compustat database · `comp.funda` table |
| **Coverage** | 10 U.S.-listed companies (see Section 3) |
| **Time range** | 2018 – 2024 (7 fiscal years, covering pre- and post-pandemic) |
| **Key fields** | `tic`, `fyear`, `sale`, `at`, `lt`, `ceq`, `ni`, `act`, `lct` |
| **Standard filters** | `datafmt='STD'` · `consol='C'` · `indfmt='INDL'` (following W5 course guidance) |

**Cleaning**: the raw query returns 70 rows. We exclude 3 rows where shareholders' equity is negative (Home Depot 2018/2019/2021), yielding 67 rows for analysis. The reason for the negative equity is discussed in the notebook.

---

## 3. Analysis Method

The core framework is the **DuPont decomposition** — breaking ROE into three factors each with a direct business meaning:

> **ROE = Profit Margin × Asset Turnover × Equity Multiplier**

- **Profit Margin**: how much of each dollar of sales becomes profit
- **Asset Turnover**: how fast the assets generate revenue
- **Equity Multiplier**: how much leverage is being used

### Case study: the Big Three U.S. retailers

The deep analysis focuses on three retail giants in the same industry but with distinctly different strategies:

| Ticker | Company | Business model positioning |
|---|---|---|
| WMT | Walmart | Scale-driven low margin |
| COST | Costco | Membership-based extreme turnover |
| TGT | Target | Mid-tier differentiated premium |

The Streamlit tool additionally preloads 7 cross-industry companies (Apple, Microsoft, Google, Home Depot, Coca-Cola, PepsiCo, Nike) for free exploration.

---

## 4. Key Findings

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

## 5. How to Run

### 5.1 Environment setup

```bash
# Clone the repo
git clone <repo URL>
cd acc102-roe-decoded

# Install dependencies
pip install -r requirements.txt
```

### 5.2 Pull WRDS data (required step)

WRDS data is not included in the repo due to licensing. First-time users need to pull it using their own WRDS account:

1. Open `notebook.ipynb` (Jupyter Lab or VS Code)
2. Run from the top through Cell 5 (the data-save step); enter your WRDS username and password when prompted
3. After it finishes, `company_financials.csv` will appear in the project root

### 5.3 Running the project

**Option A: read the full analytical narrative**

```bash
jupyter lab notebook.ipynb
```

Run all cells from top to bottom to see the full flow: WRDS query → cleaning → ratio computation → DuPont decomposition → visualizations → automatic insight generation.

**Option B: launch the interactive tool**

```bash
streamlit run app.py
```

The browser will open `http://localhost:8501`. You can freely pick any combination of companies for DuPont analysis.

---

## 6. Project Structure

```
acc102-roe-decoded/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── .gitignore                   # Excludes WRDS data and system files
│
├── notebook.ipynb               # Core analytical narrative (primary deliverable)
├── app.py                       # Streamlit interactive tool
│
├── company_financials.csv       # WRDS data (kept locally, not uploaded)
│
└── reflection.md                # 500–800 word reflection + AI use disclosure
```

---

## 7. Limitations and Future Directions

**Analytical**:
- Annual data only, cannot capture within-year seasonality
- DuPont decomposition is one perspective; it does not replace cash-flow analysis, valuation, etc.
- Cases are all U.S.-listed companies (to keep accounting conventions comparable); cross-border GAAP/IFRS differences are not considered

**Tool**:
- The rule-based insight generator has limited coverage; extreme cases (persistent losses, negative equity) fall back to generic text rather than deep analysis
- No industry-median benchmark — a future version could add peer-distribution context

**Engineering**:
- Local-only deployment limits reach; with a properly anonymized dataset the tool could be deployed to Streamlit Community Cloud for public access
- No unit tests — acceptable for a small assignment, but would be needed at larger scale

---

## 8. AI Use Declaration

This project follows the "AI-assisted analysis" workflow introduced in course W6. Claude (Anthropic) was used for coding collaboration, visualization design, and insight template drafting. All AI-generated content has been read, understood, and verified by the author. Detailed disclosure is in `reflection.md`.

---

## 9. Acknowledgments

This project builds directly on the ACC102 course material from W4–W6: WRDS connections, SQL querying, pandas processing, AI-assisted analysis, and function encapsulation.

---

*ACC102 · AI-Driven Data Analytics · 2026*
