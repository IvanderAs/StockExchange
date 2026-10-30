import customtkinter as ctk
import sqlite3
import subprocess
import os

DB_PATH = "../data/idx_trading.db"

# Konfigurasi Tema Dark Mode Desktop
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class StockExchangeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("IDX AI Trading System — Acer Nitro 5 Studio")
        self.geometry("1100x700")

        # Layout Grid Utama (Sidebar + Main View)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ------------------- SIDEBAR -------------------
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="🚀 IDX AI Engine", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_rescan = ctk.CTkButton(self.sidebar_frame, text="⚡ Run Full Scan", command=self.run_full_scan)
        self.btn_rescan.grid(row=1, column=0, padx=20, pady=10)

        self.btn_refresh = ctk.CTkButton(self.sidebar_frame, text="🔄 Refresh Table", command=self.load_signals_from_db)
        self.btn_refresh.grid(row=2, column=0, padx=20, pady=10)

        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="Status: Ready", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=3, column=0, padx=20, pady=10)

        # ------------------- MAIN VIEW -------------------
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        self.title_label = ctk.CTkLabel(self.main_frame, text="📊 Live XAI Trading Signals & Market Tiers", font=ctk.CTkFont(size=18, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")

        # Text Box / Log View untuk Menampilkan Hasil Sinyal XAI
        self.signal_display = ctk.CTkTextbox(self.main_frame, font=ctk.CTkFont(size=13, family="Monospace"))
        self.signal_display.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        # Load Data Saat Aplikasi Pertama Kali Dibuka
        self.load_signals_from_db()

    def load_signals_from_db(self):
        """Membaca sinyal XAI terbaru dari SQLite database."""
        if not os.path.exists(DB_PATH):
            self.signal_display.delete("1.0", "end")
            self.signal_display.insert("end", "⚠️ Database belum diinisialisasi. Jalankan 'Run Full Scan' terlebih dahulu.")
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT ticker, price, signal, confidence, stop_loss, take_profit, category, explanations, created_at 
                from xai_signals 
                ORDER BY id DESC LIMIT 50;
            """)
            rows = cursor.fetchall()

            self.signal_display.delete("1.0", "end")
            if not rows:
                self.signal_display.insert("end", "Tidak ada sinyal tersimpan di database.")
                return

            text_output = "=======================================================================\n"
            text_output += "            🧠 HISTORIS SINYAL XAI TERBARU (SESSIONS)\n"
            text_output += "=======================================================================\n\n"

            for r in rows:
                ticker, price, signal, conf, sl, tp, category, explanations, created_at = r
                text_output += f"Ticker        : {ticker} | Category: {category}\n"
                text_output += f" Price        : Rp {price:,.2f}\n"
                text_output += f" Signal       : {signal} (AI Confidence: {conf}%)\n"
                if sl > 0:
                    text_output += f" Risk Bounds  : SL Rp {sl:,.2f} | TP Rp {tp:,.2f}\n"
                text_output += f" Explanations : {explanations}\n"
                text_output += f" Timestamp    : {created_at}\n"
                text_output += "-----------------------------------------------------------------------\n"

            self.signal_display.insert("end", text_output)
            self.status_label.configure(text="Status: Loaded")

        except Exception as e:
            self.signal_display.insert("end", f"Error loading data: {e}")
        finally:
            conn.close()

    def run_full_scan(self):
        """Menjalankan seluruh pipeline backend secara otomatis dari aplikasi."""
        self.status_label.configure(text="Status: Scanning...")
        self.update()

        try:
            # Jalankan sequence pipeline
            subprocess.run(["python", "fetch_all_idx.py"], check=True)
            subprocess.run(["python", "dynamic_classifier.py"], check=True)
            subprocess.run(["python", "technical_engine.py"], check=True)
            subprocess.run(["python", "predict_signal_xai.py"], check=True)

            self.load_signals_from_db()
            self.status_label.configure(text="Status: Scan Finished")
        except Exception as e:
            self.status_label.configure(text="Status: Scan Failed")
            self.signal_display.insert("end", f"\n❌ Error during scan execution: {e}")

if __name__ == "__main__":
    app = StockExchangeApp()
    app.mainloop()
