from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import pyqtSignal, QProcess, QBuffer, QIODevice
from PyQt5.QtGui import QImage, QPixmap
from recognizer import FaceDetector
from messages import Message, MessageContainer
from settings import AppSettings
import database
import PIL.Image
import numpy as np
import cv2 as cv2
import queue
import io

class MainWindow(QMainWindow):
    size_changed = pyqtSignal(tuple)
    def __init__(self, db, reader):
        super(QMainWindow, self).__init__()
        self.settings = AppSettings()
        self.detector = FaceDetector()
        self.reader = reader
        self.db = db
        self.ui = uic.loadUi("app/ui/mainwindow.ui")
        self.ui.show()
        self.ui.setButton.clicked.connect(self.change_settings)
        
        self.image = None
        self.onboard_process = None  # чтобы держать процесс живым

    def change_settings(self):
        self.set_dialog = uic.loadUi("app/ui/settings.ui")
        # Немодальное окно
        self.set_dialog.setWindowModality(False)
        self.set_dialog.threshSpin.setValue(self.settings.threshold)
        self.set_dialog.modeBox.setCurrentText("Terminal only" if self.settings.mode == "multiple" else "RFID with terminal")
        self.set_dialog.timeSpin.setValue(self.settings.open_time)
        self.set_dialog.waitSpin.setValue(self.settings.wait_time)

        self.set_dialog.saveButton.clicked.connect(self._save_settings)
        self.set_dialog.cancelButton.clicked.connect(self.set_dialog.close)

        self.set_dialog.deleteButton.clicked.connect(self.open_delete_person)
        self.set_dialog.addpersonButton.clicked.connect(self.open_add_person)

        self.set_dialog.show()

    def _save_settings(self):
        self.settings.change_settings(
            self.set_dialog.threshSpin.value(),
            "multiple" if self.set_dialog.modeBox.currentText() == "Terminal only" else "single",
            self.set_dialog.timeSpin.value(),
            self.set_dialog.waitSpin.value()
        )
        self.set_dialog.close()

    def open_add_person(self):
        self.set_dialog.close()
        self.addpage = uic.loadUi("app/ui/addPerson.ui")
        self.addpage.show()

        # Подключаем события
        self.addpage.addButton.clicked.connect(self._add_person_to_db)
        self.addpage.cancelButton.clicked.connect(self._close_add_person)
        self.addpage.takephotoButton.clicked.connect(self._take_photo_for_person)

        self.reader.enable_reading()
        self.reader.new_card.connect(self.addpage.cardIdEdit.setText)

        # Запускаем процесс onboard и держим ссылку
        if self.onboard_process is None:
            self.onboard_process = QProcess(self)
            self.onboard_process.start('onboard')

    def _add_person_to_db(self):
        name = self.addpage.nameEdit.text().strip()
        card_id = self.addpage.cardIdEdit.text().strip()
        pixmap = self.addpage.photoLabel.pixmap()

        if not name:
            QMessageBox.warning(self.addpage, "Ошибка", "Введите имя пользователя")
            return
        if not card_id:
            QMessageBox.warning(self.addpage, "Ошибка", "Введите ID карты")
            return
        if pixmap is None:
            QMessageBox.warning(self.addpage, "Ошибка", "Сделайте фото пользователя")
            return

        img = self._pil_from_qt(pixmap)
        if img is None:
            QMessageBox.warning(self.addpage, "Ошибка", "Не удалось обработать фото")
            return

        person = database.Person(name=name, cardId=card_id, img=img)
        self.db.add_person(person)
        QMessageBox.information(self.addpage, "Успех", f"Пользователь {name} добавлен")
        self._close_add_person()

    def _close_add_person(self):
        self.reader.disable_reading()
        self.reader.new_card.disconnect()
        if self.onboard_process:
            self.onboard_process.kill()
            self.onboard_process = None
        self.addpage.close()

    def _take_photo_for_person(self):
        if self.image is None:
            QMessageBox.warning(self.addpage, "Ошибка", "Нет изображения с камеры")
            return
        aligned_np = self.detector.align_to_np(self.image)
        pixmap = self.pixmap_from_np(aligned_np)
        self.addpage.photoLabel.setPixmap(pixmap)

    def open_delete_person(self):
        if hasattr(self, "set_dialog"):
            self.set_dialog.close()
        self.delpage = uic.loadUi("app/ui/deletePerson.ui")
        self.delpage.show()

        self._refresh_persons_list()

        self.delpage.deleteButton.clicked.connect(self._delete_selected_person)
        self.delpage.cancelButton.clicked.connect(self.delpage.close)

    def _refresh_persons_list(self):
        self.delpage.personsList.clear()
        persons = self.db.get_all()
        for p in persons:
            self.delpage.personsList.addItem(f"name: {p.name}, card id: {p.cardId}, added: {p.date}")
        self.persons_list_cache = persons

    def _delete_selected_person(self):
        idx = self.delpage.personsList.currentRow()
        if idx < 0 or idx >= len(self.persons_list_cache):
            QMessageBox.warning(self.delpage, "Ошибка", "Выберите пользователя для удаления")
            return

        person = self.persons_list_cache[idx]
        reply = QMessageBox.question(self.delpage, 'Подтверждение удаления',
                                     f"Вы уверены, что хотите удалить пользователя {person.name}?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db.remove(person.id)
            QMessageBox.information(self.delpage, "Удалено", f"Пользователь {person.name} удалён")
            self._refresh_persons_list()

    def pixmap_from_np(self, image):
        h, w, ch = image.shape
        bytesPerLine = w * ch
        image = QImage(image.data, w, h, bytesPerLine, QImage.Format_RGB888)
        return QPixmap.fromImage(image)

    def change_frame(self, image, render):
        self.image = image
        pixmap = self.pixmap_from_np(render)
        self.ui.Videolabel.setPixmap(pixmap)

    def _pil_from_qt(self, qpixmap):
        try:
            # Более универсальный метод конвертации QPixmap в PIL.Image
            buffer = QBuffer()
            buffer.open(QIODevice.ReadWrite)
            qpixmap.save(buffer, "PNG")
            pil_im = PIL.Image.open(io.BytesIO(buffer.data()))
            return pil_im
        except Exception as e:
            print("Error processing image:", e)
            return None

    def show_full_screen(self):
        #self.ui.showFullScreen()
        self.ui.Videolabel.resize(self.ui.size())
        self.size_changed.emit((self.ui.Videolabel.size().width(), self.ui.Videolabel.size().height()))