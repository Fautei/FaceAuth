import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton
from gui import MainWindow
from recognizer import InceptionResnetV1Recognizer
from database import SQLiteDatabase
from lock import LockThread
from video import VideoThread
from reader import RC522Reader
import queue as q


def main():
    db_path = "persons.db"
    # database.create_test_db(db_path)  # если нужно, раскомментируй
    db = SQLiteDatabase(db_path)
    reader = RC522Reader()
    frame_queue = q.Queue(maxsize=1)
    recognizer = InceptionResnetV1Recognizer(db)

    app = QApplication(sys.argv)
    main_w = MainWindow(db, reader)

    video_thread = VideoThread(frame_queue)
    lock_thread = LockThread(db, recognizer, reader, frame_queue)

    main_w.size_changed.connect(video_thread.change_size)
    video_thread.new_frame_change.connect(main_w.change_frame)

    main_w.show_full_screen()

    # Запускаем потоки
    lock_thread.start()
    video_thread.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

