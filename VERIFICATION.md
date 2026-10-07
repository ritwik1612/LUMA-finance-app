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
| PDF export | Authenticated HTTP 200, summary cards and vector forecast chart; rendered pages inspected | Pass |
| CSV export | Valid per-report CSV and all-report ZIP with six tables | Pass |
| Excel export | Seven sheets, numeric financial values, valid workbook | Pass |
| JSON export | Complete data, no passwords or sessions | Pass |

Four backend integration tests cover the listed workflows, account management, appearance settings, target isolation, compressed backups, balanced restore and rejection cases. Frontend totals, month grouping and forecast scenario tests pass. JavaScript syntax passes. Generated export bytes are validated through API tests.

UI update verification: light theme with custom teal accent and dark theme with blue accent; saved settings; live projection changed to $7,158.77 before saving; growth output labels update; target creation and persistence. All seven workspace routes fit a 390px viewport without page-wide horizontal overflow. Navigation becomes a two-row touch grid. Device emulation verifies responsive layout, not every physical phone/browser combination.

Fixed during audit: whitespace-only account names and transaction descriptions; Excel amount types.

Prototype excludes invoice management, transaction edits/deletion, payroll processing/tax filing and bank sync. Restoring version-2 Settings backups is supported. Google Drive integration and real-time push synchronization are not implemented.
