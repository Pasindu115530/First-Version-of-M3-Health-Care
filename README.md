# 👁️ Safe Warner – AI Health Assistant

This is my **first AI project** built while learning Python.  
It focuses on **user health while using a computer** by reminding users to take breaks, check sitting posture, and do simple **eye exercises** every 20 minutes.  

---

## 🚀 Features

- **Auto Mode**
  - Starts with Windows boot (auto-start).
  - At launch, checks if the user is sitting at a safe distance from the screen.
  - Stops the camera once the position is correct.
  - Every **20 minutes**, automatically shows eye exercises on screen.
  - Sends **real-time notifications** about breaks, posture, and health reminders.

- **Manual Mode**
  - User can start/stop the app manually.
  - Option to switch between Manual and Auto mode.

- **Health Rules Implemented**
  - **20-20-20 Rule** → Every 20 minutes, look at something 20 feet away for 20 seconds.
  - **Eye Blinking Reminder** → Prevents eye strain by reminding you to blink.
  - **Distance Monitoring** → Ensures you sit at a safe distance from your laptop/PC.

---

## 📂 Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/safe_warner.git
cd safe_warner
```

### 2️⃣ Create and Activate Virtual Environment
> Works with **Python 3.10 or below**

```bash
# Create environment
python -m venv myenv

# Activate environment (Windows)
myenv\Scripts\activate

# Activate environment (Linux/Mac)
source myenv/bin/activate
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Run the Application
```bash
python main.py
```

---

## 📜 Requirements

All dependencies are listed in `requirements.txt`:

```txt
PyQt5>=5.15.0
opencv-python>=4.5.0
numpy>=1.21.0
psutil>=5.8.0
mediapipe>=0.10.0
plyer>=2.1.0
pywin32>=300; sys_platform == 'win32'  # Windows only
win10toast>=0.9; sys_platform == 'win32'
```

---

## 🧑‍💻 About the Project

- 💡 **This is my first AI health project while learning Python.**
- 🎯 **Main goal:** To make computer usage healthier and safer.
- 📸 **Uses:** OpenCV + MediaPipe for real-time monitoring.
- 🔔 **Notifications:** Provides fast system notifications.

---

## 🌍 Future Scope

- Cross-platform compatibility.
- More intelligent posture detection.
- Customizable break timers.
- Integration with wearable devices.

---

## 📌 Author

- 👤 **Pasindu Udana Mendis**  
- 🎓 Faculty of Computing, University of Sri Jayewardenepura
