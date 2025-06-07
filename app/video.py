
from PyQt5.QtCore import QThread, pyqtSignal
import cv2 as cv2
from PIL import Image
import numpy as np
import time
import queue
from recognizer import FaceDetector
from messages import MessageContainer
from messages import Message

class VideoThread(QThread):
    new_frame_change = pyqtSignal(np.ndarray, np.ndarray)
    def __init__(self, frame_queue):
        super().__init__()
        self.queue = frame_queue
        self.detector = FaceDetector()
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise Exception("Could not open video device")
        #camera resolution
        self.cwidth = 270
        self.cheight = 480
        #display resolution
        self.width = 270
        self.height = 480
        self.renderer = Renderer(self.cwidth,self.cheight,self.width,self.height)

    def run(self):
        process = True
        faces,_ = None,None
        while True:
            #keep original camera frame for detecting and recognizing
            #and resized for drawing and showing
            _ , frame=self.cap.read()
            if not _:
                continue
            frame = frame[:,185:455]
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            image = cv2.resize(frame,(self.width,self.height), interpolation = cv2.INTER_AREA)

            if process:
                faces,_ = self.detector.detect_faces(frame)
            if faces is not None:
                try:
                    self.queue.put_nowait(frame)
                except queue.Full:
                    self.queue.get_nowait()
                    self.queue.put_nowait(frame)
            else:
                if not self.queue.empty():
                    self.queue.get_nowait()

            self.renderer.render(image, faces)
            self.new_frame_change.emit(frame,image)


    def change_size(self, size):
        self.width, self.height = size
        self.renderer.width, self.renderer.height = size
      
class Renderer():
    def __init__(self, cw,ch,w,h):
        self.message_queue = MessageContainer()
        self.cwidth = cw
        self.cheight = ch
        self.width = w
        self.height = h
    
    def render(self, image, faces):
        if faces is not None:
            self.render_boxes(image, faces)
        for n,m in enumerate(self.message_queue):
            self.render_message(image,n,m)

    def render_message(self,image, number,message:Message):
        mes_height=60
        font = cv2.FONT_HERSHEY_SIMPLEX 
        color = message.color
        font_color = (255,255,255)
        txt_w,txt_h = cv2.getTextSize(message.text, font, 1, 2)[0]
        w,h =  self.width,self.height
        txt_scale = min(w/txt_w,h/txt_h)*0.9
        painting_rect = np.zeros((mes_height,w,3),dtype = np.uint8)
        cv2.rectangle(painting_rect,(0,0),(w,mes_height),color,cv2.FILLED)
        txt_y = int((mes_height+txt_h*txt_scale)/2)
        txt_x = int((w - txt_w*txt_scale)/2)
        cv2.putText(painting_rect,message.text, (txt_x, txt_y), font,txt_scale, font_color, 2)
        if (number+1)*mes_height < image.shape[0]:
            image[number*mes_height:(number+1)*mes_height,:,:] = image[number*mes_height:(number+1)*mes_height,:,:] * (1-message.transparency) + painting_rect*message.transparency  

    def render_boxes(self, image, faces, color=(170,170,170)):
        if faces is None:
            return
        for box in faces:
            x1, y1, x2, y2 = box
            w = x2 - x1
            h = y2 - y1
            scale_x = self.width / self.cwidth
            scale_y = self.height / self.cheight

            x1 = int(x1 * scale_x)
            y1 = int(y1 * scale_y)
            x2 = int(x2 * scale_x)
            y2 = int(y2 * scale_y)

            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)


    
    def render_boxes_with_names(self,image,faces,names):
        for (x,y,w,h),name in zip(faces,names):
            x = int(x); y = int(y); w = int(w); h =int(h)
            color = (130,170,100) if name !="Unknown" else (170,100,130)
            font_color = (255, 255, 255)
            cv2.rectangle(image,(x,y),(w,h),color,2)
            border =  int(h*0.1)
            y2 = h - border
            if(name is not None):
                cv2.rectangle(image, (x, y2),(w,h), color, cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                scale_text=border/50
                cv2.putText(image, name, (x + 3, h-3), font, scale_text, font_color, 1)
