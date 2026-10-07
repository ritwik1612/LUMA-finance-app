# LUMA Finance App

A business finance dashboard with a dark liquid-glass interface. Record income and expenses, track cash and bank balances, compare twelve-month forecasts, monitor a monthly budget, and export reports.

**Live application:** https://luma-finance-beta.vercel.app

LUMA is a cash-based finance prototype. You enter figures manually. It has no document analysis, bank feeds, Gemini calls or other AI dependencies. New business workspaces start empty.

## First-time usage

1. Open the live application or start a local instance using the installation instructions below.
2. Enter a business name, email and password of at least eight characters. Choose USD, INR, EUR or GBP and select **Create workspace**.
3. Visit **Accounts** to add cash/bank accounts with opening balances. Alternatively, record **Owner funding** into the default Business bank or Cash wallet. Do not enter the same initial funds twice.
4. Use **Add transaction** to record money received, money paid, funding or transfers.
5. Check **Overview** to see updated balances and performance.
6. Enter assumptions on **Forecast**, then select **Save assumptions**.
7. Set your monthly target on **Budget** and compare it with actual expenses.
8. Use **Export reports** to download your financial reports.

Returning users choose **Already have a workspace? Sign in**. **Sign out** ends the current session. Each business login has its own accounts, transactions and plan. Team invitations and multiple user roles are not implemented.

## Page-by-page guide

### Registration and sign-in

The entry page creates a business workspace or signs into an existing one. Registration creates two zero-balance cash accounts: Business bank and Cash wallet. Internal revenue, expense and equity accounts support the balanced journal behind the scenes.

Choose the reporting currency carefully: there is no currency-switching interface or foreign exchange conversion. Passwords are salted and hashed rather than stored as plain text. Password reset, email verification and multi-factor authentication are not available in this prototype.

### Overview — `/dashboard`

This is the daily snapshot of your recorded business finances.

| Metric | Calculation |
| --- | --- |
| Available cash | Combined balance of all cash and bank accounts, across all recorded dates. |
| Revenue | Income received during the current calendar month. |
| Expenses | Expenses paid during the current calendar month. |
| Net cash profit | Current-month revenue minus current-month expenses. |

**Cash performance** compares revenue and expenses over the last six calendar months. Hover over chart points to see values. **Spending breakdown** groups current-month expenses by category and displays each category's share. **Recent activity** shows the six most recent transactions, ordered by transaction date and then entry order.

Funding and transfers are excluded from revenue and profit. Cash and profit answer different questions: an owner contribution increases cash without increasing sales. Empty workspaces display guidance until you enter transactions.

### Transactions — `/transactions`

This page lists the transaction journal: description, date, category, type and amount. Search matches descriptions and categories without regard to letter case.

The **Add transaction** button is available across the workspace:

| Type | Use | Accounting effect |
| --- | --- | --- |
| Income | Customer payment or other business receipt. | Increases the chosen cash/bank account and revenue. |
| Expense | Payment for rent, supplies or another business cost. | Decreases the chosen cash/bank account and increases expenses. |
| Owner funding | Initial funds or additional owner contributions. | Increases cash/bank and owner equity; excluded from revenue. |
| Transfer | Movement between two cash/bank accounts. | Decreases the source and increases the destination; combined cash and profit are unchanged. |

Enter a positive amount with at most two decimal places, a date of today or earlier, an account and a description. Transfers require a different destination account. Categories are free text; blank categories become General. Future planned activity belongs in Forecast.

Every transaction generates equal debit and credit entries. The current interface cannot edit/delete transactions, import statements, attach documents or schedule recurring entries. Check the details before saving.

### Accounts — `/accounts`

Account cards show the balances of your recorded cash and bank accounts. Select **Add account**, enter a name and optionally provide an opening balance. The opening balance creates an owner-funding entry dated today, so it does not inflate revenue.

Use separate accounts for a business bank, petty cash or other cash holdings. Balances come from journal entries, not a live bank connection. Negative balances are permitted and may indicate an overdraft or missing entries. Account renaming, deletion and bank reconciliation are not implemented.

### Forecast — `/forecast`

This page projects twelve months beginning with the next calendar month. Starting cash is the current combined cash/bank balance. The assumption form contains:

- **Monthly revenue:** expected receipts in the first projected month.
- **Monthly expenses:** expected payments in the first projected month.
- **Revenue growth:** percentage change in revenue each subsequent month.
- **Cost growth:** percentage change in expenses each subsequent month.
- **Monthly spending budget:** the target also used by Budget.

Select **Save assumptions** to persist the plan. The cash chart and monthly table show projected revenue, expenses and closing cash. Forecast and Budget use the same saved assumption record.

| Scenario | Revenue growth | Cost growth |
| --- | --- | --- |
| Base | Saved revenue growth. | Saved cost growth. |
| Optimistic | Saved revenue growth plus 3 percentage points. | Saved cost growth. |
| Cautious | Saved revenue growth minus 3 percentage points. | Saved cost growth. |

For month index `i`, beginning at zero:

```text
revenue[i] = first-month revenue × (1 + scenario revenue growth / 100)^i
expenses[i] = first-month expenses × (1 + cost growth / 100)^i
closing cash[i] = previous closing cash + revenue[i] − expenses[i]
```

Amounts are rounded to cents. For example, revenue of 1,000 and expenses of 800 add 200 to cash in the first month. With 5% revenue growth and 2% cost growth, month two has revenue of 1,050 and expenses of 816.

If projected cash falls below zero, the page highlights the funding gap. These are mathematical scenarios, not predictions. They assume same-month collection/payment and exclude taxes, debt schedules, interest, capital expenditure and payment delays.

### Budget — `/budgets`

Budget compares current-calendar-month expenses with your saved monthly spending target. It shows spending, percentage used, a progress bar, and the amount remaining or over budget. The spending category breakdown identifies where recorded expenses went.

The progress bar stops at 100%, but the percentage and overspend figure still show excess spending. A zero target prompts you to set a budget. Funding and transfers are excluded. This is one monthly total target; category budgets and historical budget planning are not implemented.

The **Budget & forecast settings** form edits the same revenue, expense, growth and budget assumptions used on Forecast. Changes affect both pages.

### Export center — available on every workspace page

Select **Export reports**, choose All reports or a specific scope (Summary, Accounts, Transactions, Forecast or Budget), then choose a format.

| Format | Output |
| --- | --- |
| PDF | Printable report tables. Charts are not embedded. |
| Excel / XLSX | Workbook with separate sheets and numeric financial cells. |
| CSV | Single table for a specific scope; All reports downloads a ZIP of tables and a README. |
| JSON | Structured data snapshot without passwords or session tokens. Restore/import is not implemented. |

Forecast exports include all three scenarios using saved assumptions. Downloads require sign-in and use the current business's data. Export means generated financial reports, not original testing documents.

## Local installation

Requirements: Python 3.10 or newer, pip and a modern browser. Node.js is optional for frontend tests. No AI API keys are needed.

Windows PowerShell, inside the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\start.ps1
```

Open http://127.0.0.1:8000/dashboard. If PowerShell blocks the startup script, start the server directly:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Stop the server with Ctrl+C. Local mode creates `data/finance.sqlite3` automatically. To back up the full local database, stop the server and copy this file to a safe location. JSON downloads are readable snapshots, but the app cannot restore them yet.

## PostgreSQL and Vercel

Without DATABASE_URL, local mode uses SQLite. With DATABASE_URL, it uses PostgreSQL. An `.env` file is not automatically loaded; set the variable in your shell or hosting configuration before starting the server.

```powershell
$env:DATABASE_URL = '<your PostgreSQL connection URL>'
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Never commit a real connection URL. `.env.example` contains only a placeholder. Tables initialize when the app starts. Switching DATABASE_URL does not migrate existing SQLite records.

The live application is hosted in Vercel project `ritweakk/luma-finance`, connected to a Neon Free PostgreSQL database. Hosted mode refuses ephemeral SQLite and uses Secure session cookies. Local and hosted accounts/data are separate.

To deploy your own instance:

1. Sign in with the Vercel CLI and link this directory to the intended project/team.
2. Provision PostgreSQL and configure DATABASE_URL for the intended Vercel environments.
3. Deploy with `npx vercel --prod` under that team.
4. Verify registration, sign-in, transaction persistence, forecasts and every export format.

`vercel.json` selects FastAPI. `.vercelignore` excludes local data, testing documents, credentials, virtual environments and tests. Deployment protection is controlled by Vercel project settings; the app also has its own login.

## Architecture and files

```text
Browser: HTML + CSS + vanilla JavaScript
    → same-origin FastAPI endpoints
    → business-scoped queries and balanced journal
    → SQLite locally / PostgreSQL when DATABASE_URL is configured

Exports → ReportLab PDF / openpyxl XLSX / CSV ZIP / JSON
```

| File | Purpose |
| --- | --- |
| app.py | Routes, authentication, sessions, validation, journal posting and workspace API. |
| database.py | PostgreSQL query adapter. |
| exports.py | Report data and PDF/CSV/XLSX/JSON generation. |
| static/index.html | Entry screen, navigation and dialogs. |
| static/app.js | Metrics, charts, forecasts, navigation, forms and downloads. |
| static/style.css | Responsive dark liquid-glass design. |
| tests/test_finance.py | Backend isolation, validation, journal and export checks. |
| tests/frontend.cjs | Totals, calendar grouping and forecast calculations. |
| start.ps1 | Windows startup helper. |

The database contains businesses, sessions, accounts, journal records, debit/credit entries and plans. Journal amounts are integer cents. Aggregate balances are normalized to integer cents in API output.

| Method | API | Purpose |
| --- | --- | --- |
| POST | /api/register | Create workspace and session. |
| POST | /api/login | Start session. |
| POST | /api/logout | End current session. |
| GET | /api/workspace | Read signed-in business data. |
| POST | /api/accounts | Add account and optional opening balance. |
| POST | /api/transactions | Post balanced transaction. |
| POST | /api/plan | Save forecast/budget assumptions. |
| GET | /api/export/{format}?scope=all | Export pdf, csv, xlsx or json. |

## Tests and verification

Run tests with DATABASE_URL unset so backend tests use temporary SQLite databases:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node tests/frontend.cjs
node --check static/app.js
```

The hosted PostgreSQL flow has been checked for registration, sign-in, persisted transactions, saved assumptions, chart rendering and all four export formats. Temporary deployment verification records were removed. These checks are not a security or accounting compliance audit.

## Limitations and troubleshooting

- Cash-based management reporting only: no accrual accounting, invoices, receivables/payables, payroll, tax filing, inventory or bank connections.
- No transaction editing/deletion, recurring entries, account renaming/deletion, imports, JSON restore or password recovery.
- No team roles, approval workflow or complete audit-log interface.
- One reporting currency per business; no foreign exchange conversion.
- Calendar-month views use browser dates; transaction validation/export dates use the server date. These may differ near timezone boundaries.
- Password hashing, business isolation, HTTP-only sessions and cross-origin checks exist. Rate limiting, email verification and recovery remain future production-hardening work.
- Forecasts reflect entered assumptions and exclude several real financing/tax effects.

If the app cannot start, confirm dependencies are installed and port 8000 is available. If hosted requests fail, check DATABASE_URL and the hosting logs. If data appears missing, confirm you are using the correct business login and storage environment. If a transaction is rejected, check the date, positive two-decimal amount, description and transfer destination. Save forecast assumptions before exporting them.

## Documents and repository hygiene

The original `TESTING DOCUMENTS` folder stays in the local workspace for manual reference. No figures or documents are preloaded. Testing documents, uploaded copies, databases, screenshots, credentials, virtual environments and local integration metadata are excluded from this repository. The former FIN-DOC implementation is backed up outside the active project and is not part of LUMA's runtime.

No project license has been selected. Review ownership and licensing before redistributing third-party documents or distributing this project for reuse.
