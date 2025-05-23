import time
from max30102.max30102 import MAX30102
import numpy as np
import RPi.GPIO as GPIO
import board
import busio
import adafruit_mlx90614
import firebase_admin
from firebase_admin import credentials, db

# ---------- CONFIGURATION ----------

# Buzzer pin
BUZZER_PIN = 17

# Thresholds
TEMP_THRESHOLD = 38.0       # °C
HEART_RATE_LOW = 50
HEART_RATE_HIGH = 120
SPO2_LOW = 95

# Firebase config
cred = credentials.Certificate("/home/asus/health-monitoring-system/smart-health-monitoring-87119-firebase-adminsdk-y178i-a44383a0ef.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://smart-health-monitoring-87119-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

# ---------- HARDWARE SETUP ----------

# MAX30102 sensor
m = MAX30102()

# Temperature sensor (MLX90614)
i2c = busio.I2C(board.SCL, board.SDA)
mlx = adafruit_mlx90614.MLX90614(i2c)

# Buzzer
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# ---------- FUNCTIONS ----------

def buzz(duration=0.2):
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(BUZZER_PIN, GPIO.LOW)

def get_heart_rate_spo2():
    red, ir = m.read_sequential()
    if len(red) < 100 or len(ir) < 100:
        return None, None

    red_mean = np.mean(red)
    ir_mean = np.mean(ir)

    # Use IR mean to detect if finger is placed
    if ir_mean < 50000:
        return None, None

    # Dummy calculations (replace with real algorithm if needed)
    heart_rate = int(60 + 40 * np.random.rand())  # mock value
    spo2 = int(95 + 3 * np.random.rand())         # mock value
    return heart_rate, spo2

def get_temperature():
    return mlx.object_temperature

def send_to_firebase(heart_rate, spo2, temperature):
    ref = db.reference("realtime")
    ref.set({
        "heart_rate": heart_rate,
        "spo2": spo2,
        "temperature": temperature,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

# ---------- MAIN LOOP ----------

print("💡 Waiting for finger to be detected...")

try:
    while True:
        heart_rate, spo2 = get_heart_rate_spo2()

        if heart_rate is None:
            print("👉 Place your finger on the sensor.")
            time.sleep(1)
            continue

        temperature = get_temperature()

        print(f"💓 HR: {heart_rate} bpm | SpO₂: {spo2}% | 🌡️ Temp: {temperature:.2f}°C")

        # Check for abnormal values
        abnormal = (
            temperature > TEMP_THRESHOLD or
            heart_rate < HEART_RATE_LOW or heart_rate > HEART_RATE_HIGH or
            spo2 < SPO2_LOW
        )

        if abnormal:
            print("⚠️  Abnormal reading detected!")
            buzz(0.5)

        # Send data to Firebase
        send_to_firebase(heart_rate, spo2, temperature)
        time.sleep(5)

except KeyboardInterrupt:
    print("\n🛑 Exiting program.")
finally:
    GPIO.cleanup()
