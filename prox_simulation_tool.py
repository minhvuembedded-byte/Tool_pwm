import sys
import time
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QPlainTextEdit, QLabel, QGroupBox, QLineEdit)
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, Qt, QTimer
from datetime import datetime

# --- GIAO DIỆN HIỆN ĐẠI (QSS) ---
STYLESHEET = """
QMainWindow { background-color: #1e1e1e; }
QWidget { color: #d4d4d4; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
QGroupBox { 
    border: 1px solid #3e3e42; border-radius: 8px; 
    margin-top: 5px; padding-top: 10px; font-weight: bold; color: #007acc; 
}
QPushButton { 
    background-color: #333333; border: none; border-radius: 5px; 
    padding: 10px; min-height: 35px; color: white; font-weight: 500;
}
QPushButton:hover { background-color: #444444; }
QPushButton#connectBtn[connected="true"] { background-color: #c42b1c; }
QPushButton#connectBtn[connected="false"] { background-color: #007acc; }

QLineEdit {
    background-color: #121212; border: 1px solid #3e3e42;
    border-radius: 4px; padding: 10px; color: #00ff00; font-family: 'Consolas';
    font-size: 14px;
}
QComboBox, QPlainTextEdit { 
    background-color: #2d2d30; border: 1px solid #3e3e42; 
    border-radius: 5px; padding: 5px; color: #d4d4d4;
}
QPlainTextEdit { font-family: 'Consolas', monospace; font-size: 12px; }
"""

class SerialWorker(QObject):
    data_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    connection_status = pyqtSignal(bool)

    def __init__(self, port, baud):
        super().__init__()
        self.port, self.baud = port, baud
        self.is_running = True
        self.ser = None

    @pyqtSlot()
    def run(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=0.1)
            self.connection_status.emit(True)
            while self.is_running:
                if self.ser.is_open and self.ser.in_waiting > 0:
                    raw = self.ser.readline()
                    line = raw.decode('utf-8', errors='replace').strip()
                    if line: self.data_received.emit(line)
                time.sleep(0.01)
        except Exception as e: self.error_occurred.emit(str(e))
        finally:
            if self.ser and self.ser.is_open: self.ser.close()
            self.connection_status.emit(False)

    def stop(self): self.is_running = False

class ModernUART(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STM32 Pulse Controller - Wide View")
        self.resize(1200, 800)
        self.setStyleSheet(STYLESHEET)
        self.worker = None
        self.worker_thread = None
        self.init_ui()
        
        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self.scan_ports)
        self.scan_timer.start(2000)

    def init_ui(self):
        central_widget = QWidget()
        main_v_layout = QVBoxLayout(central_widget) # Layout tổng theo chiều dọc

        # --- PHẦN TRÊN: SIDEBAR & MONITOR ---
        top_layout = QHBoxLayout()
        
        # Sidebar trái
        sidebar = QVBoxLayout()
        conn_group = QGroupBox("KẾT NỐI")
        conn_lyt = QVBoxLayout()
        self.cb_port = QComboBox()
        self.cb_baud = QComboBox()
        self.cb_baud.addItems(["9600", "115200", "921600"])
        self.cb_baud.setCurrentText("115200")
        self.btn_connect = QPushButton("KẾT NỐI")
        self.btn_connect.setObjectName("connectBtn")
        self.btn_connect.clicked.connect(self.handle_connection)
        conn_lyt.addWidget(QLabel("Cổng COM:"))
        conn_lyt.addWidget(self.cb_port)
        conn_lyt.addWidget(QLabel("Baudrate:"))
        conn_lyt.addWidget(self.cb_baud)
        conn_lyt.addWidget(self.btn_connect)
        conn_group.setLayout(conn_lyt)

        fast_cmd_group = QGroupBox("LỆNH NHANH")
        fast_lyt = QVBoxLayout()
        self.btn_prox_ld = QPushButton("Prox LĐ (AA)")
        self.btn_prox_bd = QPushButton("Prox BĐ (BB)")
        self.btn_prox_ld.clicked.connect(lambda: self.send_raw("AA"))
        self.btn_prox_bd.clicked.connect(lambda: self.send_raw("BB"))
        fast_lyt.addWidget(self.btn_prox_ld)
        fast_lyt.addWidget(self.btn_prox_bd)
        fast_cmd_group.setLayout(fast_lyt)

        sidebar.addWidget(conn_group)
        sidebar.addWidget(fast_cmd_group)
        sidebar.addStretch()

        # Monitor phải
        monitor_lyt = QVBoxLayout()
        status_row = QHBoxLayout()
        self.status_icon = QLabel("●")
        self.status_icon.setStyleSheet("color: #c42b1c; font-size: 18px;")
        self.status_label = QLabel("Chưa kết nối")
        status_row.addWidget(self.status_icon)
        status_row.addWidget(self.status_label)
        status_row.addStretch()

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        
        monitor_lyt.addLayout(status_row)
        monitor_lyt.addWidget(self.log_view)

        top_layout.addLayout(sidebar, 1)
        top_layout.addLayout(monitor_lyt, 4)

        # --- PHẦN DƯỚI: CẤU HÌNH XUNG NGANG (WIDE) ---
        pulse_group = QGroupBox("CẤU HÌNH CHUỖI XUNG CHI TIẾT")
        pulse_lyt = QVBoxLayout()
        
        p1_row = QHBoxLayout()
        p1_row.addWidget(QLabel("<b>PIN 1:</b>"), 1)
        self.txt_p1 = QLineEdit()
        self.txt_p1.setPlaceholderText("0,100|1,200|0,50...")
        p1_row.addWidget(self.txt_p1, 9)

        p2_row = QHBoxLayout()
        p2_row.addWidget(QLabel("<b>PIN 2:</b>"), 1)
        self.txt_p2 = QLineEdit()
        self.txt_p2.setPlaceholderText("0,100|1,200|0,50...")
        p2_row.addWidget(self.txt_p2, 9)

        self.btn_pulse_send = QPushButton("GỬI CẤU HÌNH XUNG TỔNG HỢP (&&)")
        self.btn_pulse_send.setStyleSheet("background-color: #2d5a27; font-size: 14px; font-weight: bold;")
        self.btn_pulse_send.clicked.connect(self.send_pulse_payload)

        pulse_lyt.addLayout(p1_row)
        pulse_lyt.addLayout(p2_row)
        pulse_lyt.addWidget(self.btn_pulse_send)
        pulse_group.setLayout(pulse_lyt)

        # --- ADDD ALL TO MAIN ---
        main_v_layout.addLayout(top_layout, 7) # Phần trên chiếm 7 phần
        main_v_layout.addWidget(pulse_group, 3) # Phần dưới chiếm 3 phần

        self.setCentralWidget(central_widget)

    # --- LOGIC ---
    def scan_ports(self):
        if self.worker and self.worker.is_running: return 
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if [self.cb_port.itemText(i) for i in range(self.cb_port.count())] != ports:
            self.cb_port.clear()
            self.cb_port.addItems(ports)

    def handle_connection(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.stop_worker()
        else:
            self.start_worker()

    def start_worker(self):
        port = self.cb_port.currentText()
        if not port: return
        self.worker_thread = QThread()
        self.worker = SerialWorker(port, int(self.cb_baud.currentText()))
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.data_received.connect(self.append_log_rx)
        self.worker.connection_status.connect(self.update_ui_state)
        self.worker_thread.start()

    def stop_worker(self):
        if self.worker:
            self.worker.stop()
            self.worker_thread.quit()
            self.worker_thread.wait()

    def send_raw(self, text):
        if self.worker and self.worker.ser and self.worker.ser.is_open:
            msg = text + "\n"
            self.worker.ser.write(msg.encode('utf-8'))
            self.append_log_sys(f"TX -> {text}")

    def send_pulse_payload(self):
        p1 = self.txt_p1.text().strip() or "0,0"
        p2 = self.txt_p2.text().strip() or "0,0"
        payload = f"PULSE:1:{p1}&&2:{p2}"
        self.send_raw(payload)

    def update_ui_state(self, connected):
        self.btn_connect.setText("NGẮT KẾT NỐI" if connected else "KẾT NỐI")
        self.btn_connect.setProperty("connected", "true" if connected else "false")
        self.status_icon.setStyleSheet(f"color: {'#4caf50' if connected else '#c42b1c'}; font-size: 18px;")
        self.status_label.setText(f"Đang kết nối: {self.cb_port.currentText()}" if connected else "Chưa kết nối")
        self.btn_connect.style().unpolish(self.btn_connect)
        self.btn_connect.style().polish(self.btn_connect)

    def append_log_rx(self, text):
        self.log_view.appendPlainText(f"[{datetime.now().strftime('%H:%M:%S')}] RX <- {text}")

    def append_log_sys(self, text):
        self.log_view.appendPlainText(f"[{datetime.now().strftime('%H:%M:%S')}] SYS: {text}")

    def closeEvent(self, event):
        self.stop_worker()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernUART()
    window.show()
    sys.exit(app.exec_())