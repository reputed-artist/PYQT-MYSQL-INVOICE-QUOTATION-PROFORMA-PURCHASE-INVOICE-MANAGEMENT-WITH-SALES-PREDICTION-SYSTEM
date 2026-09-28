# C4 PyQt — Desktop Replica

A **PyQt6 desktop application** that replicates the CodeIgniter 4 C4
invoice/quotation management system (`c:\xampp\htdocs\C4`) **keeping the same
AdminLTE UI** (dark sidebar, blue header, stat boxes, DataTables-style lists)
and the **same MySQL database** (`db` on localhost, per the original `.env`).

The PHP project remains untouched — all PyQt files live in this folder only.

## Run

```powershell
cd c:\xampp\htdocs\C4\pyqt_app
pip install -r requirements.txt   # PyQt6, PyMySQL (already installed)
python main.py
```

Login uses the `admin` table, e.g. `admin@gmail.com` / `admin@123`.

## Branding / icons

- **Title bar + taskbar**: every window of the app (splash, login, main window,
  dialogs, message boxes) shows the **Sales Aura** mark, not the legacy CodeTech
  logo. `ui/app_icon.py` resolves it in this order:

  1. `C4_APP_ICON` (environment variable) - override for testing
  2. `dist/img/sales-aura-icon.png` - the brand mark (white chip + blue/violet "S",
     ascending bars and rising arrow), rasterised at 16/20/24/32/48/64/128/256 px
  3. the company logo on the `admin` row (`picturelogo`), then `APP_ICON_NAMES`
  4. a QPainter-drawn mark, so a branded icon always exists

  `dist/img/sales-aura.png` (plain mark, transparent) is what the splash screen
  draws. Both PNGs are generated - re-run this after changing the mark:

  ```powershell
  python tools/make_brand_logo.py              # writes both PNGs
  python tools/make_brand_logo.py --preview %TEMP%\aura   # size previews
  ```

- **Message boxes carry the icon of their kind**, drawn vector-style by
  `ui/icons.py` (`kind_icon()`) and applied through `ui.app_icon.apply(window, icon)`:

  | helper | title bar | dialog body |
  |--------|-----------|-------------|
  | `W.confirm()` | blue disc + `?` | Question |
  | `W.success()` | green disc + tick | green tick pixmap |
  | `W.info()` | aqua disc + `i` | Information |
  | `W.warning()` | amber disc + `!` | Warning |
  | `W.error()` | red disc + `x` | Critical |

  Dialog windows that are not message boxes (crud dialog, invoice View, print
  previews, ledger, info-page view) call `apply()`/`W.apply()` so their title bar
  carries the brand mark too.

## Replicated modules (PHP → PyQt)

| Original (CodeIgniter)                      | PyQt file                                    |
|---------------------------------------------|----------------------------------------------|
| `Login.php` (AdminLTE login page)           | `ui/login_window.py`                         |
| `Include/header.php` + `Include/sidebar.php`| `ui/main_window.py`                          |
| `Dashboard` controller + layout             | `ui/pages/dashboard_page.py`                 |
| `Client.php` (Manage Clients)               | `ui/pages/master_pages.py` (`ClientsPage`)   |
| `supplier.php` (Suppliers)                  | `ui/pages/master_pages.py` (`SuppliersPage`) |
| `Product.php` (Products)                    | `ui/pages/master_pages.py` (`ProductsPage`)  |
| `Taxinv.php` (Gen. Tax Invoice / List)      | `ui/pages/invoice_pages.py` (doc="tax")      |
| `Proinv.php` (Proforma Invoice)             | `ui/pages/invoice_pages.py` (doc="proforma") |
| `Quote.php` (Gen. Quotation / List)         | `ui/pages/invoice_pages.py` (doc="quote")    |
| `Purchaseinv.php` (Add Purchase / List)     | `ui/pages/invoice_pages.py` (doc="purchase") |
| `Quickquote.php` (Quick Quotation)          | `ui/pages/quickquote_page.py`                |
| `Transaction.php` (Transactions/payments)   | `ui/pages/transaction_page.py`               |
| Sale/Purchase/Quote reports (9 views)       | `ui/pages/reports_page.py`                   |
| `Account.php` (Accounts, types, ledger)     | `ui/pages/accounts_page.py`                  |
| `Salesprediction.php`                       | `ui/pages/sales_prediction_page.py`          |
| `Profile.php` (Settings)                    | `ui/pages/settings_page.py`                  |
| `print taxinv/quote/quickq*.php` views      | `utils/invoice_print.py` (print preview/PDF) |
| `getclientinfo.php` /                    | `ui/pages/info_pages.py`                     |
| `getsupplierinfo.php` /                  |                                              |
| `getproductinfo.php` (Info layout)       |                                              |
| All `*_model.php` models                    | `database/db_manager.py`                     |
| helpers (money_format, FY logic)            | `utils/helpers.py`                           |

## Notes

- **Database**: reads `config.py` (`localhost` / `db` / `root` / empty
  password) — same tables as `db.sql` (invtest/invtest2, protest/protest2,
  quote/quote2, purchaseinv/purchaseinv2, quickquote, client, products,
  paidhistory, account, acc_type, admin, bankdetails, techsps).
- **Invoice numbering** follows the original financial-year logic
  (`INV/24-25/0007`, `QT/…`, `PI/…`, `PUR/…`, `QUICKT/…`).
- **Quotation items table** has no HSN/Description columns in the original
  schema; the app adapts automatically.
- **DataTables behaviour** on every list page (Accounts, Manage Clients,
  Suppliers, Products, all invoice lists, Transactions, Quick Quote and all
  reports):
  - **Sr No** column numbered from 1 and continuing across pages
    (page 2 starts at 11 when 10 rows per page)
  - **Pagination bar**: First / ‹ / page numbers / › / Last, with an
    ellipsis window when there are many pages, and the current page
    highlighted in AdminLTE blue
  - **"Showing X to Y of Z entries"** counter
  - **Rows-per-page selector**: 10 / 25 / 50 / 100 / All
  - Page clicks re-render instantly from cached rows (no DB round-trip);
    the date-range/search filters re-query the database
  - In-table **totals row** = totals of the visible page;
    the **footer label** = overall totals for all filtered records
- Invoices support View / Print (print preview + PDF) / Edit / Delete.
- **Info pages** (the per-row *Info* button on Manage Clients / Suppliers /
  Products) port `getclientinfo.php` / `getsupplierinfo.php` /
  `getproductinfo.php`: a details box + an FY summary box, then one box per
  document type holding a paginated invoice table (with the DataTables
  totals row).

## Tests

- `python smoke_test.py` — boots the login window, signs in against the live
  database, builds the main window and every page, then verifies:
  - header/sidebar layout geometry (header spans the top, sidebar below-left)
  - all **29 navigation targets** plus the 3 **info pages** build cleanly
  - the dashboard `refresh()` runs twice in a row. This is a regression
    guard: the dashboard body lives inside a `QScrollArea`, so the scroll
    area **must** be wired into the page layout (`scroll.setWidget(inner)` /
    `lay.addWidget(scroll)`). While it was not, every child `QLabel` was
    orphaned and collected, and `refresh()` died with *"wrapped C/C++ object
    of type QLabel has been deleted"*.
  - Clients-table pagination (numbered page buttons, Next/Prev, rows-per-page,
    Last, and Sr No continuing across pages)
  - the info-page invoice tables (visible page rows + the totals row)

  Results go to `smoke_result.txt` (UTF-8). Current status: **0 failures**.
- `python test_app_icons.py` — headless title-bar icon test (**no database
  needed**): the brand mark resolves and rasterises at every icon size, every
  message kind draws a *distinct* icon, `confirm / success / info / warning /
  error` put that kind's icon on the message-box **title bar** (while the success
  dialog keeps its green right-tick in the body), and `apply()` brands the login
  window, the splash and plain dialogs. Add `--preview DIR` to dump the drawn
  icons as PNGs. Results go to `icon_test_result.txt`. Current status: **0
  failures**.
- `python write_test.py` — exercises the write path against the live database
  (insert → read-back → update → list search → item report → delete) and
  cleans up after itself (`write_test_result.txt`).
