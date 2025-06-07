from PyQt5.QtCore import QThread, pyqtSignal
import serial
from serial.tools import list_ports
from messages import MessageContainer, Message
import time

class RC522Reader(QThread):
    new_card = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.message = MessageContainer()
        self.serial = None
        self.last_id = None
        self._enable_reading = False
        self.init_reader()

    def run(self):
        while True:
            if self.serial is None:
                self.message.put(Message("Reader not connected, retrying...", (255, 150, 150), time.time(), 3))
                print("Please connect reader")
                self.init_reader()
                time.sleep(10)
                continue

            try:
                data = self.serial.readline()
                if not data:
                    continue  # no data received in timeout period
                data = data.decode("utf-8").strip()
                print(f"Received from reader: {data}")
                if self._enable_reading:
                    self.last_id = data
                    self.new_card.emit(data)
            except serial.SerialException as e:
                self.message.put(Message(f"Serial error: {e}", (255, 150, 150), time.time(), 5))
                print(f"Serial error, resetting reader: {e}")
                self.serial = None
            except Exception as e:
                print(f"Unexpected error: {e}")
            time.sleep(0.1)

    def get_last_id(self):
        return self.last_id

    def enable_reading(self):
        self._enable_reading = True

    def disable_reading(self):
        self._enable_reading = False
        self.last_id = None

    def init_reader(self):
        ports = list_ports.comports()
        portnames = [p.device for p in ports]  # p.device — правильное имя порта
        print("Available ports:", portnames)

        for p in ports:
            print(f"Port: {p.device}, Description: {p.description}, HWID: {p.hwid}")

        try:
            if portnames:
                # Попытка открыть последний порт, можно расширить логику выбора
                print(f"Trying to open port {portnames[-1]}")
                self.serial = serial.Serial(port=portnames[-1], baudrate=115200, timeout=0.1)
                self.message.put(Message(f"Reader connected on {portnames[-1]}", (150, 255, 150), time.time(), 3))
        except serial.SerialException as e:
            self.message.put(Message(f"Cannot initialize reader: {e}", (255, 100, 100), time.time(), 5))
            print(f"Cannot initialize reader: {e}")