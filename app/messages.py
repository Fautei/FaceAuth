import numpy as np
import time



class MessageContainer():
    def __init__(self):
        self.messages=[]
        self.iter=None

    def __iter__(self):
        self.iter = iter(self.messages)
        return self

    def __next__(self):
        m = next(self.iter)
        t = time.time()
        if t > m.start_time + m.duration:
            self.messages.remove(m)
            return next(self)
        m.transparency = np.sin(np.pi* (((m.start_time-t)+m.duration)/m.duration)/2)
        return m

    def __len__(self):
        return len(self.messages)

    def put(self, message):
        self.messages.append(message)

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(MessageContainer, cls).__new__(cls)
        return cls.instance

class Message():
    def __init__(self, message, color, start_time, duration):
        self.text = message
        self.color = color
        self.start_time = start_time
        self.duration = duration
        self.transparency = 1
