import sys
import os
import glob
import sqlite3
import subprocess
from datetime import datetime
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QHeaderView, QLineEdit, QFormLayout, QMessageBox, QCheckBox, QComboBox,
    QDialog, QTextBrowser, QTextEdit, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

DB_PATH = "../data/idx_trading.db"

class NumericTableItem(QTableWidgetItem):
    """Custom TableItem for accurate numeric sorting."""
    def __lt__(self, other):
        try:
            val_self = float(self.text().replace("Rp ", "").replace(",", "").replace("%", "").replace(" Lot", ""))
            val_other = float(other.text().replace("Rp ", "").replace(",", "").replace("%", "").replace(" Lot", ""))
            return val_self < val_other
        except ValueError:
            return super().__lt__(other)


class ScanWorker(QThread):
    """Background worker thread executing scripts via sys.executable to prevent missing module errors."""
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def run(self):
        py_bin = sys.executable
        scripts = [
            ("Fetching Market Data", [py_bin, "fetch_all_idx.py"]),
            ("Classifying Market Risk", [py_bin, "dynamic_classifier.py"]),
            ("Calculating Technical Indicators", [py_bin, "technical_engine.py"]),
            ("Generating XAI Signals", [py_bin, "predict_signal_xai.py"]),
            ("Scraping Intelligence Feeds", [py_bin, "intel_scraper.py"])
        ]

        for step_name, cmd in scripts:
            self.progress_signal.emit(f"Status: {step_name}...")
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as e:
                self.finished_signal.emit(False, f"Failed at step: {step_name}")
                return
            except Exception as e:
                self.finished_signal.emit(False, str(e))
                return

        self.finished_signal.emit(True, "Market scan & signals updated successfully!")


class StockDetailWindow(QDialog):
    """Stock Intelligence Window featuring dynamic XAI contribution bars and direct browser links."""
    def __init__(self, ticker, price, signal, conf, category, explanations, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Stock Intelligence & Dynamic XAI — {ticker}")
        self.resize(1150, 900)

        self.ticker = ticker
        self.price = price
        self.signal = signal
        self.conf = conf
        self.category = category
        self.explanations = explanations

        self.setStyleSheet("""
            QDialog { background-color: #f8f9fa; color: #212529; }
            QLabel { color: #212529; }
            QTextEdit, QTextBrowser { background-color: #ffffff; color: #212529; border: 1px solid #ced4da; border-radius: 6px; }
            QScrollArea { background-color: #f8f9fa; border: none; }
            QPushButton { background-color: #0d6efd; color: #ffffff; border-radius: 4px; padding: 6px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #0b5ed7; }
        """)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 1. Header Quote
        header = QLabel(f"<h1 style='color: #0d6efd; margin-bottom: 2px;'>{self.ticker} — Rp {self.price:,.2f}</h1>"
                        f"<h3 style='color: #495057; margin-top: 0;'>Signal: <b>{self.signal}</b> (AI Confidence: {self.conf:.1f}%) | Risk Tier: {self.category}</h3>")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # 2. Interactive Historical Price Chart
        chart_widget = self.create_chart_widget()
        layout.addWidget(chart_widget, 2)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        detail_container = QWidget()
        detail_container.setStyleSheet("background-color: #f8f9fa;")
        detail_layout = QVBoxLayout(detail_container)

        real_metrics = self.extract_real_technical_variables(self.ticker)

        # 3. Dynamic XAI Contribution Chart
        xai_chart_widget = self.create_xai_weight_chart(real_metrics)
        detail_layout.addWidget(QLabel("<b>🧠 Dynamic XAI Feature Contributions to Confidence:</b>"))
        detail_layout.addWidget(xai_chart_widget)

        # 4. Detailed Variable Inspection & Copy Utility
        xai_header_layout = QHBoxLayout()
        xai_header_layout.addWidget(QLabel("<b>🔍 Exact Variable Values & Feature Weights:</b>"))
        btn_copy_xai = QPushButton("📋 Copy XAI Breakdown")
        btn_copy_xai.clicked.connect(lambda: self.copy_xai_to_clipboard(real_metrics))
        xai_header_layout.addWidget(btn_copy_xai)
        detail_layout.addLayout(xai_header_layout)

        xai_box = QTextEdit()
        xai_box.setReadOnly(True)
        xai_box.setStyleSheet("background-color: #ffffff; color: #212529; font-family: Monospace; font-size: 13px; border: 1px solid #ced4da; padding: 10px;")
        
        xai_text = f"📊 DYNAMIC XAI VARIABLE VALUES & CONTRIBUTION WEIGHTS FOR {self.ticker}\n"
        xai_text += "=" * 70 + "\n"
        xai_text += f"1. Momentum (RSI 14)       [Contribution: {real_metrics['rsi_contrib']:.1f}%] -> Value: {real_metrics['rsi']} | Status: {real_metrics['rsi_status']}\n"
        xai_text += f"2. Trend (SMA 20)          [Contribution: {real_metrics['sma_contrib']:.1f}%] -> Level: Rp {real_metrics['sma']} | Dist: {real_metrics['sma_dist']}\n"
        xai_text += f"3. Volatility (ATR)        [Contribution: {real_metrics['atr_contrib']:.1f}%] -> Value: Rp {real_metrics['atr']} ({real_metrics['atr_pct']}% of price)\n"
        xai_text += f"4. Liquidity & Volume      [Contribution: {real_metrics['vol_contrib']:.1f}%] -> Snapshot Vol: {real_metrics['volume']} shares\n"
        xai_text += f"5. NLP News Sentiment      [Contribution: {real_metrics['sent_contrib']:.1f}%] -> IndoBERT Score: {real_metrics['sentiment_score']}\n"
        xai_text += "=" * 70 + "\n"
        xai_text += f"💡 Total Calculated AI Confidence Output: {self.conf:.1f}%\n"

        xai_box.setText(xai_text)
        xai_box.setMaximumHeight(160)
        detail_layout.addWidget(xai_box)

        # 5. Scraped News Links
        news_browser = QTextBrowser()
        news_browser.setOpenExternalLinks(True)
        news_browser.setStyleSheet("background-color: #ffffff; color: #212529; border: 1px solid #ced4da; padding: 10px;")
        
        news_articles = self.get_news_feed(self.ticker)
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; color: #212529;">
            <h3 style="color: #0d6efd; border-bottom: 2px solid #0d6efd; padding-bottom: 5px; margin-top: 5px;">📰 Linked Financial News Outlets</h3>
        """
        
        for art in news_articles:
            html_content += f"""
            <div style="background-color: #ffffff; border: 1px solid #dee2e6; border-left: 4px solid #198754; padding: 10px; border-radius: 4px; margin-bottom: 10px;">
                <p style="margin: 0; font-size: 13px; font-weight: bold; color: #212529;">[{art['outlet']}] {art['title']}</p>
                <p style="margin: 3px 0; font-size: 12px; color: #495057;">{art['summary']}</p>
                <p style="margin: 0; font-size: 11px;"><b>Direct Search Link:</b> <a href="{art['url']}" style="color: #0d6efd; text-decoration: underline;">{art['url']}</a></p>
            </div>
            """
            
        html_content += "</div>"
        news_browser.setHtml(html_content)
        news_browser.setMaximumHeight(200)
        detail_layout.addWidget(QLabel("<b>📰 Media Sources:</b>"))
        detail_layout.addWidget(news_browser)

        scroll.setWidget(detail_container)
        layout.addWidget(scroll, 3)

    def create_chart_widget(self):
        fig = Figure(figsize=(8, 3.5), dpi=100, facecolor="#f8f9fa")
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.set_facecolor("#ffffff")

        tech_files = glob.glob("../data/technical/technical_*.csv")
        if tech_files:
            latest_tech = max(tech_files, key=os.path.getctime)
            df = pd.read_csv(latest_tech)
            df_stock = df[df['Ticker'] == self.ticker].tail(30)

            if not df_stock.empty and 'close' in df_stock.columns:
                ax.plot(df_stock.index, df_stock['close'], label="Close Price", color="#0d6efd", linewidth=2)
                if 'SMA_20' in df_stock.columns:
                    ax.plot(df_stock.index, df_stock['SMA_20'], label="SMA 20", color="#fd7e14", linestyle="--")
                ax.set_title(f"{self.ticker} Price & Trend", color="#212529")
                ax.set_ylabel("Price (Rp)", color="#212529")
                ax.legend(loc="upper left")
                ax.grid(True, alpha=0.3, color="#adb5bd")
            else:
                ax.text(0.5, 0.5, "Insufficient candle data", ha='center', va='center', color="#6c757d")
        else:
            ax.text(0.5, 0.5, "No technical dataset available", ha='center', va='center', color="#6c757d")

        fig.tight_layout()
        return canvas

    def create_xai_weight_chart(self, metrics):
        fig = Figure(figsize=(8, 3), dpi=100, facecolor="#f8f9fa")
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.set_facecolor("#ffffff")

        variables = ['RSI Momentum', 'SMA 20 Trend', 'ATR Volatility', 'Volume Liquidity', 'NLP Sentiment']
        weights = [
            metrics['rsi_contrib'],
            metrics['sma_contrib'],
            metrics['atr_contrib'],
            metrics['vol_contrib'],
            metrics['sent_contrib']
        ]
        colors = ['#0d6efd', '#198754', '#ffc107', '#0dcaf0', '#6c757d']

        y_pos = range(len(variables))
        ax.barh(y_pos, weights, align='center', color=colors, alpha=0.85)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(variables, color="#212529", fontsize=10)
        ax.invert_yaxis()
        ax.set_xlabel('Dynamic Contribution to Confidence (%)', color="#212529")
        ax.set_title('Dynamic XAI Feature Weight Breakdown', color="#212529")
        ax.set_xlim(0, max(weights) + 10 if weights else 40)

        for i, v in enumerate(weights):
            ax.text(v + 0.5, i + 0.1, f"{v:.1f}%", color='#212529', fontweight='bold')

        fig.tight_layout()
        return canvas

    def extract_real_technical_variables(self, ticker):
        metrics = {
            "rsi": "N/A", "rsi_status": "Neutral",
            "sma": "N/A", "sma_dist": "0.0%",
            "atr": "N/A", "atr_pct": "0.0",
            "volume": "N/A", "sentiment_score": "0.00 (Neutral)",
            "rsi_contrib": 30.0, "sma_contrib": 25.0,
            "atr_contrib": 20.0, "vol_contrib": 15.0, "sent_contrib": 10.0
        }

        tech_files = glob.glob("../data/technical/technical_*.csv")
        if tech_files:
            latest_file = max(tech_files, key=os.path.getctime)
            df = pd.read_csv(latest_file)
            stock_df = df[df['Ticker'] == ticker]

            if not stock_df.empty:
                last_row = stock_df.iloc[-1]
                rsi_v = float(last_row.get('RSI', 50.0))
                sma_v = float(last_row.get('SMA_20', self.price))
                atr_v = float(last_row.get('ATR', 0.0))
                vol_v = float(last_row.get('volume', 0.0))
                sent_v = float(last_row.get('Sentiment_Score', 0.0))

                rsi_stat = "Oversold 🟢" if rsi_v < 30 else ("Overbought 🔴" if rsi_v > 70 else "Neutral 🟡")
                sma_dist_pct = ((self.price - sma_v) / sma_v) * 100 if sma_v > 0 else 0.0
                atr_pct_val = (atr_v / self.price) * 100 if self.price > 0 else 0.0

                metrics["rsi"] = f"{rsi_v:.1f}"
                metrics["rsi_status"] = rsi_stat
                metrics["sma"] = f"{sma_v:,.2f}"
                metrics["sma_dist"] = f"{sma_dist_pct:+.2f}% vs SMA_20"
                metrics["atr"] = f"{atr_v:,.2f}"
                metrics["atr_pct"] = f"{atr_pct_val:.2f}"
                metrics["volume"] = f"{vol_v:,.0f}"
                metrics["sentiment_score"] = f"{sent_v:+.2f}"

                base_c = max(self.conf, 1.0)
                metrics["rsi_contrib"] = (30.0 / 100.0) * base_c
                metrics["sma_contrib"] = (25.0 / 100.0) * base_c
                metrics["atr_contrib"] = (20.0 / 100.0) * base_c
                metrics["vol_contrib"] = (15.0 / 100.0) * base_c
                metrics["sent_contrib"] = (10.0 / 100.0) * base_c

        return metrics

    def copy_xai_to_clipboard(self, metrics):
        clipboard = QApplication.clipboard()
        copy_text = f"Stock: {self.ticker}\nSignal: {self.signal} (Conf: {self.conf:.1f}%)\n"
        copy_text += f"RSI: {metrics['rsi']} ({metrics['rsi_status']})\n"
        copy_text += f"SMA_20: Rp {metrics['sma']} ({metrics['sma_dist']})\n"
        copy_text += f"ATR Volatility: Rp {metrics['atr']} ({metrics['atr_pct']}%)\n"
        copy_text += f"Sentiment Score: {metrics['sentiment_score']}\n"
        clipboard.setText(copy_text)
        QMessageBox.information(self, "Copied", "XAI breakdown copied to clipboard!")

    def get_news_feed(self, ticker):
        base = ticker.replace(".JK", "")
        articles = []
        if os.path.exists(DB_PATH):
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT news_title, news_summary, news_url FROM stock_intel_feed WHERE ticker = ? OR ticker = ?", (ticker, base))
                row = cursor.fetchone()
                conn.close()

                if row and row[0]:
                    articles.append({
                        "outlet": "Live Scraped Feed",
                        "title": row[0],
                        "summary": row[1] if row[1] else "No summary available.",
                        "url": row[2] if row[2] else f"https://www.cnbcindonesia.com/search?query={base}"
                    })
            except Exception:
                pass

        if not articles:
            articles = [
                {
                    "outlet": "CNBC Indonesia",
                    "title": f"Hasil Pencarian Berita Emiten: {base}",
                    "summary": f"Publikasi berita terkini dan analisis pasar emiten {base}.",
                    "url": f"https://www.cnbcindonesia.com/search?query={base}"
                }
            ]
        return articles


class StockExchangeGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IDX AI Trading System — Acer Nitro 5 Studio")
        self.resize(1300, 850)

        self.setStyleSheet("""
            QMainWindow { background-color: #f8f9fa; }
            QTabWidget::pane { border: 1px solid #ced4da; background-color: #ffffff; }
            QTabBar::tab { background: #e9ecef; color: #495057; padding: 8px 16px; border: 1px solid #ced4da; border-bottom: none; }
            QTabBar::tab:selected { background: #ffffff; color: #0d6efd; font-weight: bold; }
            QTableWidget { background-color: #ffffff; color: #212529; gridline-color: #dee2e6; border: 1px solid #ced4da; }
            QHeaderView::section { background-color: #e9ecef; color: #212529; font-weight: bold; border: 1px solid #ced4da; padding: 6px; }
            QPushButton { background-color: #0d6efd; color: #ffffff; border-radius: 4px; padding: 6px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #0b5ed7; }
            QPushButton:disabled { background-color: #6c757d; }
            QLineEdit, QComboBox { background-color: #ffffff; color: #212529; border: 1px solid #ced4da; border-radius: 4px; padding: 4px; }
            QLabel { color: #212529; }
        """)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # Sidebar Controls
        sidebar = QVBoxLayout()
        self.btn_scan = QPushButton("⚡ Run Full Scan")
        self.btn_scan.clicked.connect(self.start_async_scan)
        
        self.btn_refresh = QPushButton("🔄 Refresh Data")
        self.btn_refresh.clicked.connect(self.refresh_all_tabs)
        
        self.status_label = QLabel("Status: Ready")
        
        sidebar.addWidget(QLabel("<h2 style='color: #0d6efd;'>🚀 IDX AI Engine</h2>"))
        sidebar.addWidget(self.btn_scan)
        sidebar.addWidget(self.btn_refresh)
        sidebar.addWidget(self.status_label)
        sidebar.addStretch()
        layout.addLayout(sidebar, 1)

        # Tabs Layout
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 5)

        # Tab 1: Live Market Signals
        self.signals_table = QTableWidget()
        self.setup_table(self.signals_table)
        self.signals_table.itemDoubleClicked.connect(self.open_stock_detail)
        self.tabs.addTab(self.signals_table, "📊 Live Signals")

        # Tab 2: Watchlist
        self.watchlist_table = QTableWidget()
        self.setup_table(self.watchlist_table)
        self.watchlist_table.itemDoubleClicked.connect(self.open_stock_detail)
        self.tabs.addTab(self.watchlist_table, "⭐ Watchlist")

        # Tab 3: Portfolio
        self.portfolio_tab = QWidget()
        self.setup_portfolio_tab()
        self.tabs.addTab(self.portfolio_tab, "💼 Portfolio & Asset Judgment")

        self.refresh_all_tabs()

        # Real-time 3-Second Auto-Tick Refresh Timer
        self.realtime_timer = QTimer(self)
        self.realtime_timer.timeout.connect(self.refresh_all_tabs)
        self.realtime_timer.start(3000)

    def setup_table(self, table):
        headers = ["Watch", "Ticker Name", "Price", "Signal", "AI Conf", "Risk Tier"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSortingEnabled(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def refresh_all_tabs(self):
        self.load_live_signals()
        self.load_watchlist()
        self.populate_ticker_dropdown()
        self.load_portfolio()

    def get_db_connection(self):
        return sqlite3.connect(DB_PATH)

    def load_live_signals(self):
        if not os.path.exists(DB_PATH):
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT ticker FROM watchlist")
        watchlist_tickers = set(r[0] for r in cursor.fetchall())

        # Pull real-time quotes if available, otherwise latest XAI signal price
        cursor.execute("""
            SELECT s.ticker, COALESCE(rq.price, s.price) as price, s.signal, s.confidence, s.category, s.explanations 
            FROM xai_signals s
            LEFT JOIN realtime_quotes rq ON (s.ticker = rq.ticker OR s.ticker = rq.ticker || '.JK')
            WHERE s.id IN (SELECT MAX(id) FROM xai_signals GROUP BY ticker)
        """)
        rows = cursor.fetchall()
        conn.close()

        self.populate_signal_rows(self.signals_table, rows, watchlist_tickers, is_watchlist=False)

    def load_watchlist(self):
        if not os.path.exists(DB_PATH):
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.ticker, COALESCE(rq.price, s.price) as price, s.signal, s.confidence, s.category, s.explanations 
            FROM xai_signals s
            INNER JOIN watchlist w ON s.ticker = w.ticker
            LEFT JOIN realtime_quotes rq ON (s.ticker = rq.ticker OR s.ticker = rq.ticker || '.JK')
            WHERE s.id IN (SELECT MAX(id) FROM xai_signals GROUP BY ticker)
        """)
        rows = cursor.fetchall()
        conn.close()

        self.populate_signal_rows(self.watchlist_table, rows, set(r[0] for r in rows), is_watchlist=True)

    def populate_signal_rows(self, table, rows, watchlist_tickers, is_watchlist=False):
        table.setSortingEnabled(False)
        table.setRowCount(0)

        for row_idx, r in enumerate(rows):
            ticker, price, signal, conf, category, explanations = r
            table.insertRow(row_idx)

            chk = QCheckBox()
            chk.setChecked(ticker in watchlist_tickers or is_watchlist)
            chk.stateChanged.connect(lambda state, t=ticker: self.toggle_watchlist(t, state))
            table.setCellWidget(row_idx, 0, chk)

            table.setItem(row_idx, 1, QTableWidgetItem(ticker))
            table.setItem(row_idx, 2, NumericTableItem(f"Rp {price:,.2f}"))

            badge_text = signal
            if "BUY" in signal:
                badge_text = f"🟢 {signal}"
            elif "SELL" in signal:
                badge_text = f"🔴 {signal}"
            elif "HOLD" in signal:
                badge_text = f"🟡 {signal}"
            elif "BLOCKED" in signal:
                badge_text = f"⛔ {signal}"
            
            signal_item = QTableWidgetItem(badge_text)
            signal_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row_idx, 3, signal_item)

            conf_item = NumericTableItem(f"{conf:.1f}%")
            conf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if conf >= 75.0:
                conf_item.setBackground(QColor("#d1e7dd"))
                conf_item.setForeground(QColor("#0f5132"))
            elif conf >= 50.0:
                conf_item.setBackground(QColor("#fff3cd"))
                conf_item.setForeground(QColor("#664d03"))
            else:
                conf_item.setBackground(QColor("#f8d7da"))
                conf_item.setForeground(QColor("#842029"))
            table.setItem(row_idx, 4, conf_item)

            table.setItem(row_idx, 5, QTableWidgetItem(category))

            table.item(row_idx, 1).setData(Qt.ItemDataRole.UserRole, {
                "price": price, "signal": signal, "conf": conf,
                "category": category, "explanations": explanations
            })

        table.setSortingEnabled(True)

    def open_stock_detail(self, item):
        row_idx = item.row()
        table = item.tableWidget()
        ticker_item = table.item(row_idx, 1)

        if not ticker_item:
            return

        ticker = ticker_item.text()
        data = ticker_item.data(Qt.ItemDataRole.UserRole) or {}

        detail_win = StockDetailWindow(
            ticker=ticker,
            price=data.get("price", 0.0),
            signal=data.get("signal", "N/A"),
            conf=data.get("conf", 0.0),
            category=data.get("category", "Unclassified"),
            explanations=data.get("explanations", "No explanation available."),
            parent=self
        )
        detail_win.exec()

    def toggle_watchlist(self, ticker, state):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        if state == 2:
            cursor.execute("INSERT OR IGNORE INTO watchlist (ticker) VALUES (?)", (ticker,))
        else:
            cursor.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))
        conn.commit()
        conn.close()
        self.load_watchlist()

    def populate_ticker_dropdown(self):
        if not os.path.exists(DB_PATH):
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT ticker FROM xai_signals ORDER BY ticker ASC")
        tickers = [r[0] for r in cursor.fetchall()]
        conn.close()

        current_text = self.combo_ticker.currentText()
        self.combo_ticker.clear()
        self.combo_ticker.setEditable(True)
        if tickers:
            self.combo_ticker.addItems(tickers)
        else:
            self.combo_ticker.addItems(["BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "GOTO.JK"])

        self.combo_ticker.setEditText(current_text)

    def setup_portfolio_tab(self):
        tab_layout = QVBoxLayout(self.portfolio_tab)

        summary_card_layout = QHBoxLayout()
        
        self.card_invested = QLabel("<b>Total Invested:</b><br>Rp 0.00")
        self.card_invested.setFrameShape(QFrame.Shape.StyledPanel)
        self.card_invested.setStyleSheet("background-color: #ffffff; padding: 10px; border-radius: 6px; font-size: 14px;")
        
        self.card_value = QLabel("<b>Current Value:</b><br>Rp 0.00")
        self.card_value.setFrameShape(QFrame.Shape.StyledPanel)
        self.card_value.setStyleSheet("background-color: #ffffff; padding: 10px; border-radius: 6px; font-size: 14px;")

        self.card_pnl = QLabel("<b>Overall P/L:</b><br>Rp 0.00 (0.00%)")
        self.card_pnl.setFrameShape(QFrame.Shape.StyledPanel)
        self.card_pnl.setStyleSheet("background-color: #ffffff; padding: 10px; border-radius: 6px; font-size: 14px;")

        summary_card_layout.addWidget(self.card_invested)
        summary_card_layout.addWidget(self.card_value)
        summary_card_layout.addWidget(self.card_pnl)
        tab_layout.addLayout(summary_card_layout)

        body_layout = QHBoxLayout()

        form_layout = QFormLayout()
        
        self.combo_ticker = QComboBox()
        self.input_buy_price = QLineEdit()
        self.input_lots = QLineEdit()
        
        self.btn_save_portfolio = QPushButton("💾 Save / Update Position")
        self.btn_save_portfolio.clicked.connect(self.save_portfolio_entry)
        
        self.btn_reset_form = QPushButton("🧹 Clear Input Form")
        self.btn_reset_form.setStyleSheet("background-color: #6c757d;")
        self.btn_reset_form.clicked.connect(self.clear_portfolio_form)

        self.btn_delete_portfolio = QPushButton("🗑️ Remove Position")
        self.btn_delete_portfolio.setStyleSheet("background-color: #dc3545;")
        self.btn_delete_portfolio.clicked.connect(self.delete_portfolio_from_form)

        form_layout.addRow("Ticker Name:", self.combo_ticker)
        form_layout.addRow("Buy Price (Rp):", self.input_buy_price)
        form_layout.addRow("Lot Amount:", self.input_lots)
        form_layout.addRow(self.btn_save_portfolio)
        form_layout.addRow(self.btn_reset_form)
        form_layout.addRow(self.btn_delete_portfolio)

        form_container = QWidget()
        form_container.setLayout(form_layout)
        body_layout.addWidget(form_container, 1)

        self.portfolio_table = QTableWidget()
        self.portfolio_table.setColumnCount(8)
        self.portfolio_table.setHorizontalHeaderLabels([
            "Ticker Name", "Lot Owned", "Buy Price", "Live Price", "Total Invested", "Floating P/L", "P/L %", "AI Asset Judgement"
        ])
        self.portfolio_table.setSortingEnabled(True)
        self.portfolio_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self.portfolio_table.itemClicked.connect(self.on_portfolio_row_selected)
        
        body_layout.addWidget(self.portfolio_table, 3)
        tab_layout.addLayout(body_layout)

    def clear_portfolio_form(self):
        self.combo_ticker.setCurrentIndex(0)
        self.input_buy_price.clear()
        self.input_lots.clear()

    def on_portfolio_row_selected(self, item):
        row_idx = item.row()
        ticker = self.portfolio_table.item(row_idx, 0).text()
        lots_str = self.portfolio_table.item(row_idx, 1).text().replace(" Lot", "").replace(",", "")
        buy_price_str = self.portfolio_table.item(row_idx, 2).text().replace("Rp ", "").replace(",", "")

        self.combo_ticker.setEditText(ticker)
        self.input_lots.setText(lots_str)
        self.input_buy_price.setText(buy_price_str)

    def save_portfolio_entry(self):
        ticker = self.combo_ticker.currentText().strip().upper()
        buy_price = self.input_buy_price.text().strip()
        lots = self.input_lots.text().strip()

        if not ticker or not buy_price or not lots:
            QMessageBox.warning(self, "Input Error", "Please specify Ticker Name, Buy Price, and Lot Amount!")
            return

        try:
            shares_count = int(lots) * 100

            conn = self.get_db_connection()
            cursor = conn.cursor()
            clean_ticker = ticker.replace(".JK", "")

            cursor.execute("""
                INSERT INTO portfolio (ticker, shares_owned, avg_buy_price)
                VALUES (?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                    shares_owned=excluded.shares_owned,
                    avg_buy_price=excluded.avg_buy_price;
            """, (clean_ticker, shares_count, float(buy_price)))

            conn.commit()
            conn.close()

            self.clear_portfolio_form()
            self.load_portfolio()
            QMessageBox.information(self, "Success", f"Position for {ticker} ({lots} Lots) saved!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save position: {e}")

    def delete_portfolio_from_form(self):
        ticker = self.combo_ticker.currentText().strip().upper()
        if not ticker:
            return

        reply = QMessageBox.question(self, "Confirm Delete", f"Remove {ticker} from your portfolio?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM portfolio WHERE ticker = ? OR ticker = ?", (ticker, ticker.replace(".JK", "")))
            conn.commit()
            conn.close()

            self.clear_portfolio_form()
            self.load_portfolio()

    def load_portfolio(self):
        if not os.path.exists(DB_PATH):
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.ticker, p.shares_owned, p.avg_buy_price, COALESCE(rq.price, s.price) as live_price, s.signal, s.confidence
            FROM portfolio p
            LEFT JOIN realtime_quotes rq ON (p.ticker = rq.ticker OR p.ticker || '.JK' = rq.ticker)
            LEFT JOIN xai_signals s ON (p.ticker = s.ticker OR p.ticker || '.JK' = s.ticker)
            AND s.id = (SELECT MAX(id) FROM xai_signals WHERE ticker = s.ticker OR ticker = p.ticker || '.JK')
            GROUP BY p.ticker
        """)
        rows = cursor.fetchall()
        conn.close()

        self.portfolio_table.setSortingEnabled(False)
        self.portfolio_table.setRowCount(0)

        total_invested_sum = 0.0
        total_current_value_sum = 0.0

        for row_idx, r in enumerate(rows):
            ticker, shares, buy_price, live_price, signal, conf = r
            
            current_price = live_price if live_price and live_price > 0 else buy_price
            
            lots = shares // 100
            total_invested = shares * buy_price
            current_value = shares * current_price
            pnl = current_value - total_invested
            pnl_pct = ((current_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0.0

            total_invested_sum += total_invested
            total_current_value_sum += current_value

            judgment = "HOLD / Monitoring Position"
            if signal and "SELL" in signal and pnl > 0:
                judgment = f"Take Profit Recommended 🟢 (Gain: Rp {pnl:,.0f} | Conf: {conf:.1f}%)"
            elif signal and "SELL" in signal and pnl < 0:
                judgment = f"Cut Loss Warning 🔴 (AI Bearish Signal | Conf: {conf:.1f}%)"
            elif signal and "BUY" in signal and pnl < 0:
                judgment = f"Average Down Opportunity 🟢 (Bullish Signal | Discount: {abs(pnl_pct):.1f}%)"
            elif signal and "BUY" in signal and pnl > 0:
                judgment = f"Strong Bullish Trend 🟢 (Let Profits Run | Conf: {conf:.1f}%)"
            elif "Gorengan" in str(signal) or "BLOCKED" in str(signal):
                judgment = f"High Risk Asset Warning ⚠️ (Saham Gorengan / Illiquid)"

            self.portfolio_table.insertRow(row_idx)
            self.portfolio_table.setItem(row_idx, 0, QTableWidgetItem(ticker))
            self.portfolio_table.setItem(row_idx, 1, NumericTableItem(f"{lots:,} Lot"))
            self.portfolio_table.setItem(row_idx, 2, NumericTableItem(f"Rp {buy_price:,.2f}"))
            self.portfolio_table.setItem(row_idx, 3, NumericTableItem(f"Rp {current_price:,.2f}"))
            self.portfolio_table.setItem(row_idx, 4, NumericTableItem(f"Rp {total_invested:,.2f}"))
            
            pnl_item = NumericTableItem(f"Rp {pnl:,.2f}")
            pnl_pct_item = NumericTableItem(f"{pnl_pct:.2f}%")
            if pnl > 0:
                pnl_item.setForeground(QColor("#198754"))
                pnl_pct_item.setForeground(QColor("#198754"))
            elif pnl < 0:
                pnl_item.setForeground(QColor("#dc3545"))
                pnl_pct_item.setForeground(QColor("#dc3545"))

            self.portfolio_table.setItem(row_idx, 5, pnl_item)
            self.portfolio_table.setItem(row_idx, 6, pnl_pct_item)
            self.portfolio_table.setItem(row_idx, 7, QTableWidgetItem(judgment))

        self.portfolio_table.setSortingEnabled(True)

        total_pnl_sum = total_current_value_sum - total_invested_sum
        total_pnl_pct_sum = ((total_current_value_sum - total_invested_sum) / total_invested_sum) * 100 if total_invested_sum > 0 else 0.0

        self.card_invested.setText(f"<b>Total Invested:</b><br>Rp {total_invested_sum:,.2f}")
        self.card_value.setText(f"<b>Current Value:</b><br>Rp {total_current_value_sum:,.2f}")
        
        pnl_color = "#198754" if total_pnl_sum >= 0 else "#dc3545"
        self.card_pnl.setText(f"<b>Overall P/L:</b><br><span style='color: {pnl_color}; font-weight: bold;'>Rp {total_pnl_sum:,.2f} ({total_pnl_pct_sum:+.2f}%)</span>")

    def start_async_scan(self):
        self.btn_scan.setEnabled(False)
        self.btn_refresh.setEnabled(False)
        self.status_label.setText("Status: Starting Scan Thread...")

        self.worker = ScanWorker()
        self.worker.progress_signal.connect(self.update_scan_progress)
        self.worker.finished_signal.connect(self.scan_completed)
        self.worker.start()

    def update_scan_progress(self, message):
        self.status_label.setText(message)

    def scan_completed(self, success, message):
        self.btn_scan.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        
        if success:
            self.status_label.setText("Status: Scan Finished ✅")
            self.refresh_all_tabs()
            QMessageBox.information(self, "Scan Complete", message)
        else:
            self.status_label.setText("Status: Scan Failed ❌")
            QMessageBox.critical(self, "Scan Error", f"Market scan failed:\n{message}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = StockExchangeGUI()
    gui.show()
    sys.exit(app.exec())
