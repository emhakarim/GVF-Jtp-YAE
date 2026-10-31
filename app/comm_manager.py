"""
Modul Manajemen Komunikasi Hardware ESP32
Mendukung koneksi Serial UART (prioritas latensi rendah) dan Wi-Fi WebSocket.
Menggunakan sinyal PySide6 untuk integrasi asinkron dengan GUI.
"""

import json
import time
import threading
from typing import Optional
from PySide6.QtCore import QObject, Signal

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

try:
    import websocket
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False


class CommManager(QObject):
    # Sinyal status komunikasi
    connection_status = Signal(str, bool, str)   # (protocol, is_connected, message)
    release_confirmed = Signal(str, int, float)  # (target, t_esp_micros, pc_timestamp)
    log_message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.serial_port: Optional[serial.Serial] = None
        self.ws_app = None
        self.ws_thread = None
        
        self.is_serial_connected = False
        self.is_wifi_connected = False
        
        self.running = True
        self.serial_read_thread = None

    # ================= KONEKSI SERIAL UART =================
    def list_serial_ports(self):
        """Mendeteksi daftar port COM serial yang tersedia."""
        if not SERIAL_AVAILABLE:
            return []
        ports = serial.tools.list_ports.comports()
        return [p.device for p in ports]

    def connect_serial(self, port: str, baud_rate: int = 115200) -> bool:
        """Membuka koneksi UART ke ESP32."""
        if not SERIAL_AVAILABLE:
            self.connection_status.emit("UART", False, "Pustaka pyserial tidak terpasang.")
            return False
            
        try:
            self.disconnect_serial()
            self.serial_port = serial.Serial(port, baud_rate, timeout=0.1)
            self.is_serial_connected = True
            
            # Start background reader thread
            self.serial_read_thread = threading.Thread(target=self._serial_reader_loop, daemon=True)
            self.serial_read_thread.start()
            
            self.connection_status.emit("UART", True, f"Terhubung ke {port} @ {baud_rate}")
            self.log_message.emit(f"[UART] Berhasil terhubung ke {port}")
            return True
        except Exception as e:
            self.is_serial_connected = False
            self.connection_status.emit("UART", False, str(e))
            self.log_message.emit(f"[UART] Gagal terhubung: {e}")
            return False

    def disconnect_serial(self):
        """Memutus koneksi UART."""
        self.is_serial_connected = False
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception:
                pass
        self.serial_port = None
        self.connection_status.emit("UART", False, "Terputus.")

    def _serial_reader_loop(self):
        """Loop pembaca pesan JSON dari ESP32 via Serial."""
        while self.is_serial_connected and self.serial_port and self.serial_port.is_open:
            try:
                line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    self._parse_incoming_payload(line)
            except Exception:
                break
            time.sleep(0.002)

    # ================= KONEKSI WI-FI WEBSOCKET =================
    def connect_wifi(self, esp_ip: str, port: int = 81):
        """Membuka koneksi WebSocket ke ESP32."""
        ws_url = f"ws://{esp_ip}:{port}/"
        self.log_message.emit(f"[WIFI] Menghubungkan ke {ws_url}...")
        
        # Threaded WebSocket client connection
        def run_ws():
            try:
                import websocket
                self.ws_app = websocket.WebSocketApp(
                    ws_url,
                    on_open=self._on_ws_open,
                    on_message=self._on_ws_message,
                    on_error=self._on_ws_error,
                    on_close=self._on_ws_close
                )
                self.ws_app.run_forever()
            except Exception as e:
                self.connection_status.emit("WIFI", False, str(e))

        self.ws_thread = threading.Thread(target=run_ws, daemon=True)
        self.ws_thread.start()

    def disconnect_wifi(self):
        if self.ws_app:
            try:
                self.ws_app.close()
            except Exception:
                pass
        self.is_wifi_connected = False
        self.connection_status.emit("WIFI", False, "Terputus.")

    def _on_ws_open(self, ws):
        self.is_wifi_connected = True
        self.connection_status.emit("WIFI", True, "WebSocket Terhubung.")
        self.log_message.emit("[WIFI] WebSocket Terhubung ke ESP32.")

    def _on_ws_message(self, ws, message):
        self._parse_incoming_payload(message)

    def _on_ws_error(self, ws, error):
        self.log_message.emit(f"[WIFI] Error: {error}")

    def _on_ws_close(self, ws, close_status_code, close_msg):
        self.is_wifi_connected = False
        self.connection_status.emit("WIFI", False, "WebSocket Ditutup.")

    # ================= PROTOKOL PENGIRIMAN PERINTAH =================
    def send_command(self, cmd_dict: dict) -> bool:
        """Mengirimkan payload JSON via UART (prioritas) atau Wi-Fi."""
        payload_str = json.dumps(cmd_dict)
        sent = False
        
        # Prioritaskan USB UART karena latensi sub-milidetik deterministik
        if self.is_serial_connected and self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write((payload_str + "\n").encode('utf-8'))
                sent = True
            except Exception as e:
                self.log_message.emit(f"[UART] Gagal kirim: {e}")

        # Jika UART tidak aktif atau gagal, kirim via WebSocket
        elif self.is_wifi_connected and self.ws_app:
            try:
                self.ws_app.send(payload_str)
                sent = True
            except Exception as e:
                self.log_message.emit(f"[WIFI] Gagal kirim: {e}")

        return sent

    def trigger_drop_feather(self):
        """Servo 1: Lepas bulu."""
        t_pc = time.perf_counter()
        if self.send_command({"cmd": "DROP_FEATHER", "t_pc": t_pc}):
            self.log_message.emit("[COMMAND] Pelepasan BULU diinstruksikan.")

    def trigger_drop_ball(self):
        """Servo 2: Lepas bola besi."""
        t_pc = time.perf_counter()
        if self.send_command({"cmd": "DROP_BALL", "t_pc": t_pc}):
            self.log_message.emit("[COMMAND] Pelepasan BOLA BESI diinstruksikan.")

    def trigger_drop_both(self):
        """Servo 3: Lepas keduanya secara simultan."""
        t_pc = time.perf_counter()
        if self.send_command({"cmd": "DROP_BOTH", "t_pc": t_pc}):
            self.log_message.emit("[COMMAND] Pelepasan SIMULTAN (Bulu & Bola) diinstruksikan.")

    def reset_servos(self):
        """Reset semua posisi servo ke hold."""
        if self.send_command({"cmd": "RESET"}):
            self.log_message.emit("[COMMAND] Reset posisi servo.")

    # ================= PARSING RESPON HARDWARE =================
    def _parse_incoming_payload(self, text: str):
        try:
            data = json.loads(text)
            event = data.get("event")
            if event == "RELEASED":
                target = data.get("target", "UNKNOWN")
                t_micros = data.get("t_drop_micros", 0)
                pc_now = time.perf_counter()
                self.release_confirmed.emit(target, t_micros, pc_now)
                self.log_message.emit(f"[HARDWARE] Konfirmasi lepas {target} pada t_esp={t_micros} us")
        except json.JSONDecodeError:
            # Mengabaikan pesan debug non-JSON dari Serial
            pass
