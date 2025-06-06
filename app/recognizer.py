import torch
import numpy as np
from facenet_pytorch import MTCNN, InceptionResnetV1
from PyQt5.QtCore import QObject, pyqtSignal
from settings import AppSettings
from database import Person


class FaceDetector(QObject):
    """Singleton class for face detection and alignment."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FaceDetector, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.mtcnn = MTCNN(image_size=160, margin=20, device=self.device, keep_all=True)
        self.settings = AppSettings()
        self._initialized = True

    def detect_faces(self, image):
        return self.mtcnn.detect(image)

    def align_single(self, image):
        return self.mtcnn(image)[0]

    def align_multiple(self, image):
        return self.mtcnn(image)

    def align_to_np(self, image):
        tensor = self.align_single(image)
        if tensor is None:
            return np.zeros((160, 160, 3), np.uint8)
        return ((tensor.permute(1, 2, 0).cpu().numpy() * 128) + 127.5).astype(np.uint8).copy()


class InceptionResnetV1Recognizer(QObject):
    """Recognizer class that uses face embeddings to identify persons."""
    def __init__(self, database):
        super().__init__()
        self.database = database
        self.settings = AppSettings()

        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
        self.detector = FaceDetector()

        self.db_encodings = {}
        self.database.databaseChanged.connect(self.initialize_encodings)
        self.initialize_encodings()

    def initialize_encodings(self):
        """Load and encode all persons from the database."""
        self.db_encodings.clear()
        for person in self.database.get_all():
            encoding = self._get_encoding(person.img)
            if encoding is not None:
                self.db_encodings[person.id] = encoding
        print(f"[Recognizer] Encoded {len(self.db_encodings)} faces.")

    def recognize_single(self, image):
        """Recognize the most likely person in an image."""
        encoding = self._get_encoding(image)
        if encoding is None:
            return Person()
        return self._match_encoding(encoding)

    def recognize_all(self, image):
        """Recognize all detected faces in an image."""
        encodings = self._get_encodings(image)
        if encodings is None or len(self.db_encodings) == 0:
            return [Person()]
        return [self._match_encoding(e) for e in encodings]

    def _match_encoding(self, encoding):
        """Find the best match for a single encoding."""
        if not self.db_encodings:
            return Person()
        
        distances = {pid: torch.norm(encoding - enc).item() for pid, enc in self.db_encodings.items()}
        best_id, best_dist = min(distances.items(), key=lambda item: item[1])

        if best_dist > self.settings.threshold:
            return Person()
        return self.database.get_person_by_id(best_id)

    def _get_encodings(self, image):
        """Align and encode all faces in image."""
        try:
            cropped_imgs = self.detector.align_multiple(image)
            if cropped_imgs is None:
                return None
            return self.resnet(cropped_imgs.to(self.device)).cpu()
        except Exception as e:
            print(f"[Recognizer ERROR] Failed to get encodings: {e}")
            return None

    def _get_encoding(self, image):
        """Align and encode a single face in image."""
        try:
            cropped = self.detector.align_single(image)
            if cropped is None:
                return None
            return self.resnet(cropped.unsqueeze(0).to(self.device)).cpu()[0]
        except Exception as e:
            print(f"[Recognizer ERROR] Failed to get encoding: {e}")
            return None