"""
Sales Prediction & Repurchase Intelligence page.

Features:
- Summary KPI Cards: Active Clients, Churn-Risk Clients, Repeat Buyer Rate,
  90-Day Expected Purchases, Immediate Next (30-day).
- Search & Filter Controls: Filter by Risk Status and Buyer Type, search
  client name.
- Interactive Repurchase DataTable with full BG/NBD predictions.
- Pagination & Page-Size Selector with Showing X to Y of Z entries.
- Multi-format Export (CSV, Excel, TXT, Clipboard, etc.).
- Monthly Sales Bar Chart & Moving Average Forecast (with a forecast bar
  for the next month so the user sees the prediction visually).
"""
from datetime import date
import pandas as pd

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QComboBox, QPushButton, QHeaderView, QScrollArea
)

from database import db_manager
from ui import widgets as W
from ui.pages.dashboard_page import BarChart
from ui.pages.master_pages import DTTopBar, DTFooter, _TableState
from utils.helpers import money
from utils.prediction_engine import predict_repurchase


# --------------------------------------------------------------------------- #
# KPI card
# --------------------------------------------------------------------------- #
class MetricCard(QFrame):
    """AdminLTE small-box KPI card with icon, value, title, and footer."""

    def __init__(self, title: str, value: str, subtext: str, color: str,
                 icon_name: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(105)
        self.setStyleSheet(
            f"QFrame {{ background: {color}; border-radius: 4px;"
            f" border: none; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 8)
        lay.setSpacing(2)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)

        vl = QVBoxLayout()
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(2)

        self.val_label = QLabel(value)
        self.val_label.setStyleSheet(
            "color: white; background: transparent; font-size: 22px;"
            " font-weight: bold;")
        vl.addWidget(self.val_label)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            "color: rgba(255,255,255,0.9); background: transparent;"
            " font-size: 13px; font-weight: 600;")
        vl.addWidget(self.title_label)
        top.addLayout(vl, 1)

        ic = QLabel()
        ic.setPixmap(W.theme_icon(icon_name, "rgba(255,255,255,0.75)", 36)
                     .pixmap(36, 36))
        top.addWidget(ic, 0, Qt.AlignmentFlag.AlignRight |
                            Qt.AlignmentFlag.AlignVCenter)
        lay.addLayout(top, 1)

        self.sub_label = QLabel(subtext)
        self.sub_label.setStyleSheet(
            "color: rgba(255,255,255,0.75); background: transparent;"
            " font-size: 11px;")
        lay.addWidget(self.sub_label)

    def set_value(self, val: str, sub: str = None):
        self.val_label.setText(str(val))
        if sub is not None:
            self.sub_label.setText(str(sub))


# --------------------------------------------------------------------------- #
# Main page
# --------------------------------------------------------------------------- #
class SalesPredictionPage(QWidget):
    title = "Sales Prediction"

    def __init__(self, main):
        super().__init__()
        self.main = main
        self._all_predictions = []
        self._filtered_predictions = []
        self._state = _TableState()
        self._summary = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lay.addWidget(W.PageHeader(
            "Sales Prediction & Repurchase Intelligence",
            "BG/NBD Statistical Repeat-Purchase Forecasts, Churn Risk & RFM Metrics",
            breadcrumb="Sales Prediction"
        ))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }")
        inner = QWidget()
        self.body_layout = QVBoxLayout(inner)
        self.body_layout.setContentsMargins(14, 10, 14, 14)
        self.body_layout.setSpacing(12)

        self._build_kpi_row()
        self._build_prediction_card()
        self._build_legacy_chart_card()

        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)

        self.refresh()

    # ---------------------------------------------------------------- KPI
    def _build_kpi_row(self):
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)

        self.kpi_active = MetricCard(
            "Active Clients", "0", "P(alive) >= 60%", "#00a65a", "user", self)
        self.kpi_churn = MetricCard(
            "Churn-Risk", "0", "P(alive) < 40%", "#dd4b39", "bell", self)
        self.kpi_rate = MetricCard(
            "Repeat Rate", "0.0%", "2+ purchases", "#3c8dbc", "exchange", self)
        self.kpi_exp90 = MetricCard(
            "Exp. Purchases (90d)", "0.0", "Expected client orders",
            "#f39c12", "cartplus", self)
        self.kpi_high30 = MetricCard(
            "Immediate Next (30d)", "0", "P(buy 30d) >= 50%",
            "#605ca8", "linechart", self)

        for c in (self.kpi_active, self.kpi_churn, self.kpi_rate,
                  self.kpi_exp90, self.kpi_high30):
            kpi_row.addWidget(c)
        self.body_layout.addLayout(kpi_row)

    # ---------------------------------------------------------------- table
    def _build_prediction_card(self):
        pred_box = W.Box("Client Repurchase Predictions (BG/NBD Model)",
                         "primary")

        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        filter_bar.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(
            ["All Statuses", "Active", "At-Risk", "Churn-Risk"])
        self.status_filter.currentIndexChanged.connect(self._apply_filters)
        filter_bar.addWidget(self.status_filter)

        filter_bar.addWidget(QLabel("Buyer Type:"))
        self.type_filter = QComboBox()
        self.type_filter.addItems(
            ["All Buyers", "Repeat Clients (2+)", "Single Purchase (1)"])
        self.type_filter.currentIndexChanged.connect(self._apply_filters)
        filter_bar.addWidget(self.type_filter)

        filter_bar.addStretch()

        self.top_bar = DTTopBar(
            self,
            on_search=self._apply_filters,
            on_page_size=self._set_page_size,
            search_placeholder="Search client name..."
        )
        filter_bar.addWidget(self.top_bar)

        btn_export = QPushButton("Export CSV")
        btn_export.setObjectName("btnDefault")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.clicked.connect(self._export)
        filter_bar.addWidget(btn_export)

        pred_box.addLayout(filter_bar)

        headers = [
            "Sr No", "Client Name", "Purchases", "Total Revenue",
            "Last Invoice", "Avg Gap", "P(Alive)", "Status",
            "P(Buy 30d)", "P(Buy 60d)", "P(Buy 90d)", "Exp. 90d",
            "Est. Next Date", "Confidence"
        ]
        self.table = W.DataTable(headers, stretch_all=False)
        self.table.setMinimumHeight(380)

        h = self.table.horizontalHeader()
        h.setStretchLastSection(False)
        h.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 48)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for c in range(2, len(headers)):
            h.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)

        pred_box.add(self.table, 1)

        self.footer = DTFooter(self, on_goto=self._goto_page)
        pred_box.add(self.footer, 0)
        self.body_layout.addWidget(pred_box)

    # ---------------------------------------------------------------- chart
    def _build_legacy_chart_card(self):
        chart_box = W.Box(
            f"Monthly Invoice Sales & Trend ({date.today().year})", "info")

        top_info = QHBoxLayout()
        self.pred_label = QLabel("Computing...")
        self.pred_label.setStyleSheet(
            "font-size: 14px; color: #444; font-weight: 500;")
        top_info.addWidget(self.pred_label)
        top_info.addStretch()
        chart_box.addLayout(top_info)

        self.chart = BarChart([0] * 12, "#605ca8")
        self.chart.setFixedHeight(180)
        chart_box.add(self.chart)
        self.body_layout.addWidget(chart_box)

    # ================================================================ refresh
    def refresh(self):
        """Fetch transactions, run the BG/NBD engine, and refresh the UI."""
        try:
            year = date.today().year

            # ---- 1. Chart data (this year, Jan..Dec) -------------------
            values = db_manager.monthly_sales("invtest2", "created", year) \
                     or [0] * 12
            # guarantee exactly 12
            values = (list(values) + [0] * 12)[:12]

            # ---- 2. Forecast via trailing 3 months ---------------------
            forecast, window_desc = self._compute_forecast(values, year)

            # ---- 3. Render the chart with the forecast bar ------------
            chart_values = list(values)
            # next month index (0-based)
            next_month_idx = date.today().month          # month is 1-based;
                                                         # +0 == next month
            if next_month_idx >= 12:
                next_month_idx = 11                      # clamp in December
            # Only put the forecast in that slot if it's currently empty
            if chart_values[next_month_idx] == 0:
                chart_values[next_month_idx] = forecast

            self.chart.set_values(chart_values)

            self.pred_label.setText(
                f"Next Month Invoice Forecast: <b>{money(forecast)}</b> "
                f"({window_desc})"
            )

            # ---- 4. BG/NBD repurchase predictions ----------------------
            tx_data = db_manager.get_client_invoice_transactions()
            if tx_data:
                df = pd.DataFrame(tx_data)
                self._all_predictions, self._summary = predict_repurchase(df)
            else:
                self._all_predictions, self._summary = [], {}

            self._update_kpi_cards()
            self._apply_filters()

        except Exception as exc:
            import traceback
            W.error(self, f"Prediction error: {exc}\n"
                          f"{traceback.format_exc()}")

    # ------------------------------------------------- forecast helpers
    def _compute_forecast(self, values, year):
        """Return (forecast_value, description_string).

        Priority:
          1. If db_manager.last_n_months_sales() exists, use it (Option B).
          2. Otherwise use the current-year values up to this month (Option A).
          3. Otherwise fall back to the last 3 non-zero values in the year.

        This makes the code work today and auto-upgrade if you later add
        `last_n_months_sales` to db_manager.
        """
        # --- Option B: try the DB helper first ---
        helper = getattr(db_manager, "last_n_months_sales", None)
        if callable(helper):
            try:
                trailing = helper("invtest2", "created", n=3) or []
                if len(trailing) >= 1:
                    vals = [t for _, _, t in trailing[-3:]]
                    forecast = sum(vals) / len(vals)
                    labels = [
                        f"{self._month_abbr(m)} {str(y)[-2:]}"
                        for y, m, _ in trailing[-3:]
                    ]
                    return forecast, f"avg of {', '.join(labels)}"
            except Exception:
                pass    # fall through to Option A

        # --- Option A: current year, up to current month ---
        current_month = date.today().month       # 1..12
        past_values = values[:current_month]     # Jan..Sep when month == 9
        last3 = [v for v in past_values[-3:] if v is not None]

        # --- Fallback: last 3 non-zero values anywhere in the year ---
        if not last3 or all(v == 0 for v in last3):
            non_zero = [v for v in values if v and v > 0]
            last3 = non_zero[-3:]

        if not last3:
            return 0.0, "no data available"

        forecast = sum(last3) / len(last3)
        return forecast, "3-month moving average basis"

    @staticmethod
    def _month_abbr(m: int) -> str:
        return ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m - 1]

    # ---------------------------------------------------------------- KPIs
    def _update_kpi_cards(self):
        s = self._summary
        tot = s.get("total_clients", 0)
        act = s.get("active_clients", 0)
        churn = s.get("churn_risk_clients", 0)
        rate = s.get("repeat_rate_pct", 0.0)
        exp90 = s.get("expected_sales_90d", 0.0)
        h30 = s.get("high_prob_30d", 0)

        self.kpi_active.set_value(f"{act}", f"{act}/{tot} alive")
        self.kpi_churn.set_value(f"{churn}", "Action recommended")
        self.kpi_rate.set_value(
            f"{rate:.1f}%", f"{s.get('repeat_clients', 0)} repeat buyers")
        self.kpi_exp90.set_value(f"{exp90:.1f}",
                                 "Cumulative expected count")
        self.kpi_high30.set_value(f"{h30}", "High buy likelihood")

    # ---------------------------------------------------------------- filters
    def _apply_filters(self):
        search_txt = self.top_bar.search.text().strip().lower()
        st_filter = self.status_filter.currentText()
        type_filter = self.type_filter.currentText()

        filtered = []
        for r in self._all_predictions:
            if search_txt and search_txt not in r["client"].lower():
                continue
            if st_filter != "All Statuses" and r["status"] != st_filter:
                continue
            if type_filter == "Repeat Clients (2+)" and r["n_purchases"] < 2:
                continue
            if type_filter == "Single Purchase (1)" and r["n_purchases"] != 1:
                continue
            filtered.append(r)

        self._filtered_predictions = filtered
        self._state.current = 1
        self._render()

    def _set_page_size(self, size):
        self._state.per_page = int(size) if size else 0
        self._state.current = 1
        self._render()

    def _goto_page(self, page):
        self._state.current = max(1, page)
        self._render()

    # ---------------------------------------------------------------- render
    def _render(self):
        rows = self._filtered_predictions
        count = len(rows)
        total_pages = self._state.total_pages(count)
        if self._state.current > total_pages:
            self._state.current = total_pages

        start, end = self._state.page_range(count)
        page_rows = rows[start:end]

        self.table.clear_rows()
        for i, r in enumerate(page_rows):
            sr_no = start + i + 1
            client_name = r["client"]
            n_purchases = r["n_purchases"]
            tot_rev = money(r["total_amount"])
            last_date = r["last_purchase"]
            avg_gap = (f"{r['avg_gap_days']:.0f} d"
                       if r["n_purchases"] >= 2 else "-")
            p_alive = f"{r['p_alive']:.2f}"
            status = r["status"]
            p_30 = f"{r['p_purchase_30d']:.2f}"
            p_60 = f"{r['p_purchase_60d']:.2f}"
            p_90 = f"{r['p_purchase_90d']:.2f}"
            exp_90 = f"{r['expected_purchases_90d']:.2f}"
            next_date = r["likely_next_date"]
            conf = r["confidence"]

            row_idx = self.table.add_row([
                sr_no, client_name, n_purchases, tot_rev,
                last_date, avg_gap, p_alive, status,
                p_30, p_60, p_90, exp_90,
                next_date, conf
            ], data=r)

            for col_idx in [0, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]:
                item = self.table.item(row_idx, col_idx)
                if item:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item_rev = self.table.item(row_idx, 3)
            if item_rev:
                item_rev.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight |
                    Qt.AlignmentFlag.AlignVCenter)

        self.footer.update_state(
            self._state.current, total_pages,
            self._state.per_page or count or 1, count
        )

    # ---------------------------------------------------------------- export
    def _export(self):
        rows = self._filtered_predictions
        if not rows:
            W.info(self, "No prediction records to export.")
            return

        headers = [
            "Client Name", "Purchases", "Total Revenue", "First Purchase",
            "Last Purchase", "Avg Gap Days", "P(Alive)", "Status",
            "P(Buy 30d)", "P(Buy 60d)", "P(Buy 90d)",
            "Expected Purchases (90d)",
            "Likely Next Date", "Window Start", "Window End", "Confidence"
        ]

        data = []
        for r in rows:
            data.append([
                r["client"],
                r["n_purchases"],
                r["total_amount"],
                r["first_purchase"],
                r["last_purchase"],
                r["avg_gap_days"],
                r["p_alive"],
                r["status"],
                r["p_purchase_30d"],
                r["p_purchase_60d"],
                r["p_purchase_90d"],
                r["expected_purchases_90d"],
                r["likely_next_date"],
                r["window_start"],
                r["window_end"],
                r["confidence"]
            ])

        W.export_csv(
            self,
            headers,
            data,
            default_name=f"repurchase_predictions_"
                         f"{date.today().isoformat()}.csv"
        )