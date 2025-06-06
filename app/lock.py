from PyQt5.QtCore import QThread
import time
from database import SQLiteDatabase, Person
from reader import RC522Reader
from settings import AppSettings
from messages import MessageContainer, Message
from queue import Queue, Empty

gpio_available = True
try:
    import Jetson.GPIO as GPIO
except ImportError:
    gpio_available = False
    print("GPIO unavailable")


class Lock:
    """Controls a physical door lock via GPIO"""
    def __init__(self):
        self.door_pin = 12
        self.settings = AppSettings()
        self.messages = MessageContainer()

        if gpio_available:
            try:
                GPIO.setmode(GPIO.BOARD)
                GPIO.setup(self.door_pin, GPIO.OUT, initial=GPIO.LOW)
            except Exception as e:
                print(f"GPIO initialization error: {e}")

    def open(self):
        if gpio_available:
            try:
                GPIO.output(self.door_pin, GPIO.HIGH)
                print("The door is open")
            except Exception as e:
                print(f"Error opening door: {e}")
        self.messages.put(Message("The door is open", (170, 255, 150), time.time(), self.settings.open_time))

    def close(self):
        if gpio_available:
            try:
                GPIO.output(self.door_pin, GPIO.LOW)
                print("The door is closed")
            except Exception as e:
                print(f"Error closing door: {e}")
        self.messages.put(Message("The door is closed", (255, 170, 150), time.time(), 3))


class LockThread(QThread):
    """Background thread managing recognition and access control logic"""
    def __init__(self, db: SQLiteDatabase, recognizer, reader: RC522Reader, frame_queue: Queue):
        super().__init__()
        self.settings = AppSettings()
        self.db = db
        self.recognizer = recognizer
        self.reader = reader
        self.queue = frame_queue
        self.lock = Lock()
        self.messages = MessageContainer()

        self.default_name = Person().name
        self.reader.start()

    def run(self):
        while True:
            try:
                image = self.queue.get(timeout=1)
            except Empty:
                continue

            if self.settings.mode == "multiple":
                persons = self.recognizer.recognize_all(image)
                self.process_multiple(persons)
            elif self.settings.mode == "single":
                person = self.recognizer.recognize_single(image)
                self.process_single(person)

    def process_single(self, person: Person):
        if person.name == self.default_name:
            self.messages.put(Message("Access denied: person wasn't recognized", (255, 150, 150), time.time(), 3))
            print("Access denied: unknown face")
            return

        print(f"Face recognized as {person.name}")
        self.messages.put(Message(f"Recognized: {person.name}", (150, 255, 150), time.time(), 10))
        self.reader.enable_reading()
        self.messages.put(Message("Please scan your card", (150, 150, 255), time.time(), self.settings.wait_time))

        card_id = None
        for _ in range(self.settings.wait_time):
            card_id = self.reader.get_last_id()
            if card_id:
                break
            time.sleep(1)

        self.reader.disable_reading()

        if not card_id:
            self.messages.put(Message("Timeout: card not scanned", (255, 150, 150), time.time(), 5))
            print("Card scan timeout")
            return

        if card_id == person.cardId:
            self.messages.put(Message(f"Access granted: {person.name}", (150, 255, 150), time.time(), 5))
            self.lock.open()
            time.sleep(self.settings.open_time)
            self.lock.close()
        else:
            self.messages.put(Message("Access denied: wrong card", (255, 100, 150), time.time(), 5))
            print("Access denied: card mismatch")

    def process_multiple(self, persons):
        names = [p.name for p in persons]
        print("Recognized persons:", names)

        if self.default_name not in names:
            self.messages.put(Message("Access granted for all", (150, 255, 150), time.time(), 5))
            self.lock.open()
            time.sleep(self.settings.open_time)
            self.lock.close()
        else:
            self.messages.put(Message("Access denied: unknown person in group", (255, 150, 150), time.time(), 5))
            print("Access denied: some persons were not recognized")