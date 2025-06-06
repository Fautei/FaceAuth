# 🧠 FaceAuth – Biometric Face Recognition Access System

**FaceAuth** is a modern biometric authentication system using real-time face recognition, equipped with a user-friendly GUI. Ideal for access control systems, attendance management, or tech showcases. Built with Python and Qt, and Docker-compatible for deployment.

---

## 🚀 Features

- 👤 Real-time face detection and recognition
- 🧑‍💼 Add or remove users with just a few clicks
- 🔐 Integration with physical locks or access mechanisms (relay output via GPIO)
- 🖥️ Graphical interface built with PyQt5
- 🐳 Docker support for easy deployment
- 🗃️ Persistent user database
- ⚙️ Configurable settings via JSON file

---

## 📷 Screenshots


![Main Window](./screenshots/mainwindow.png)
*Main interface of the application*

## 🛠️ Installation

### 🔧 Run Locally

1. **Clone the repository:**

```bash
git clone https://github.com/Fautei/FaceAuth
cd FaceAuth
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python app/main.py
```

🐳 Run with Docker

docker build -t FaceAuth .
docker run -p 8000:8000 FaceAuth