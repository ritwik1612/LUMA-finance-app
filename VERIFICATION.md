# Feature verification — 7 October 2026

Verified business workflow: UI -> FastAPI -> SQLite -> displayed balances and reports.

| Feature | Evidence | Status |
|---|---|---|
| Registration, login/logout | API tests; live browser login/logout | Pass |
| Business isolation | Cross-business account use rejected; separate transaction data | Pass |
| Income/expense/funding/transfer | Balanced journal tests; live income, expense and transfer | Pass |
| Accounts and opening balances | Live $2,500.45 balance; API precision and funding classification | Pass |
| Dashboard calculations and charts | Frontend arithmetic tests; live chart in initial build | Pass |
| Search | Live Rent filter returns only expense | Pass |
| Forecast | 12 months, three scenarios; mathematical tests and live values | Pass |
| Budget | Live $100.10 against $90 produces $10.10 over-budget warning | Pass |
| Persistence | Reload retains balances; logout/login preserves plan | Pass |
| PDF export | Authenticated HTTP 200, valid six-page PDF, rendered layout inspected | Pass |
| CSV export | Valid per-report CSV and all-report ZIP with five tables | Pass |
| Excel export | Six sheets, numeric financial values, valid workbook | Pass |
| JSON export | Complete data, no passwords or sessions | Pass |

Three backend integration tests cover the listed workflows and rejection cases. Frontend totals, month grouping and forecast scenario tests pass. JavaScript syntax passes. Live export controls all display Download ready; all export API requests returned HTTP 200; console errors empty. The browser automation download event timed out, so the resulting browser download file path was not inspected; generated file bytes were validated directly through API tests.

Fixed during audit: whitespace-only account names and transaction descriptions; Excel amount types.

Temporary QA workspace removed. Existing businesses and source documents retained. Prototype excludes invoice management, transaction edits/deletion, payroll/tax, bank sync and JSON restore.
