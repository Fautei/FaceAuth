import sqlite3
import pickle
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal
from messages import Message, MessageContainer
import time
import os


class Person:
    def __init__(self, id=-1, cardId="", name="Unknown", img=None, date=datetime.now()):
        self.id = id
        self.cardId = cardId
        self.name = name
        self.img = img
        self.date = date

    def __eq__(self, other):
        return self.id == other.id


class SQLiteDatabase(QObject):
    databaseChanged = pyqtSignal()

    def __init__(self, database_path):
        super().__init__()
        self.db_path = database_path
        self.messages = MessageContainer()
        self.sqlite_connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.sqlite_connection.cursor()
        self._ensure_schema()

    def _ensure_schema(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cardId TEXT NOT NULL,
            name TEXT NOT NULL,
            image BLOB NOT NULL,
            registered_date TEXT
        )''')
        self.sqlite_connection.commit()

    def get_all(self):
        try:
            self.cursor.execute("SELECT * FROM persons")
            return [
                Person(id, card, name, pickle.loads(img), date)
                for (id, card, name, img, date) in self.cursor.fetchall()
            ]
        except Exception as e:
            print(f"[DB ERROR] Failed to fetch all persons: {e}")
            return []

    def add_person(self, person: Person):
        if not all([person.name, person.cardId, person.img]):
            print("[DB] Invalid person data")
            return

        try:
            binary = pickle.dumps(person.img, -1)
            self.cursor.execute(
                '''INSERT INTO persons (cardId, name, image, registered_date)
                   VALUES (?, ?, ?, ?)''',
                (person.cardId, person.name, binary, datetime.now())
            )
            self.sqlite_connection.commit()
            self.databaseChanged.emit()
            self.messages.put(Message(f"Person {person.name} added", (170, 255, 150), time.time(), 6))
        except Exception as e:
            print(f"[DB ERROR] Failed to add person: {e}")
            self.messages.put(Message("Failed to add person", (255, 150, 150), time.time(), 6))

    def remove(self, id):
        try:
            person = self.get_person_by_id(id)
            self.cursor.execute("DELETE FROM persons WHERE id = ?", (id,))
            self.sqlite_connection.commit()
            self.databaseChanged.emit()
            self.messages.put(Message(f"Person {person.name} removed", (255, 130, 150), time.time(), 6))
        except Exception as e:
            print(f"[DB ERROR] Failed to remove person: {e}")
            self.messages.put(Message("Failed to remove person", (255, 150, 150), time.time(), 6))

    def get_person_by_id(self, id):
        return self._fetch_person_by("id", id)

    def get_person_by_cardid(self, cardId):
        return self._fetch_person_by("cardId", cardId)

    def _fetch_person_by(self, field, value):
        try:
            self.cursor.execute(f"SELECT * FROM persons WHERE {field} = ?", (value,))
            row = self.cursor.fetchone()
            if row:
                id, cardId, name, img, date = row
                return Person(id, cardId, name, pickle.loads(img), date)
        except Exception as e:
            print(f"[DB ERROR] Failed to fetch person by {field}: {e}")
        return Person()


def create_test_db(database_path):
    db = SQLiteDatabase(database_path)
    # Добавить демо-данные, если нужно