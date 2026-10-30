import sys

# Patching app_gui_v2.py to add QTimer for zero-delay GUI refreshes
with open('app_gui_v2.py', 'r') as f:
    code = f.read()

# Add QTimer import if missing
if "from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer" not in code:
    code = code.replace("from PyQt6.QtCore import Qt, QThread, pyqtSignal", "from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer")

# Add real-time auto-refresh timer inside __init__
timer_code = """
        # Real-time Auto-Tick Timer (Refreshes numbers every 3 seconds)
        self.realtime_timer = QTimer(self)
        self.realtime_timer.timeout.connect(self.refresh_all_tabs)
        self.realtime_timer.start(3000) # 3000 ms = 3 seconds
"""

if "self.realtime_timer" not in code:
    code = code.replace("self.refresh_all_tabs()", "self.refresh_all_tabs()\n" + timer_code)

with open('app_gui_v2.py', 'w') as f:
    f.write(code)

print("✅ Real-Time 3-Second Auto-Tick Timer successfully integrated into app_gui_v2.py!")
