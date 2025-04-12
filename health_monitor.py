import time
import numpy as np
import board
import busio
from max30102.max30102 import MAX30102
from max30102.hrcalc import calc_hr_and_spo2
import adafruit_mlx90614
import firebase_admin
from firebase_admin import credentials, firestore
import RPi.GPIO as GPIO

# Initialize MAX30102 sensor
max30102_sensor = MAX30102()

# Initialize MLX90614 temperature sensor
i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
temp_sensor = adafruit_mlx90614.MLX90614(i2c)

# Initialize Firebase
cred = credentials.Certificate("/home/asus/health-monitoring-system/smart-health-monitoring-87119-firebase-adminsdk-y178i-8f2138caa7.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Initialize Buzzer (GPIO pin 17)
BUZZER_PIN = 17
GPIO.setmode(GPIO.BOARD)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# Heart rate and SpO2 thresholds
LOW_HEART_RATE_THRESHOLD = 50  # beats per minute
HIGH_HEART_RATE_THRESHOLD = 100
LOW_SPO2_THRESHOLD = 90  # percentage
HIGH_SPO2_THRESHOLD = 100

def is_human_detected():
    try:
        object_temp = temp_sensor.object_temperature
        print(f"👤 Object Temperature: {object_temp:.2f} °C")
        return object_temp > 30.0
    except Exception as e:
        print(f"Error detecting human: {e}")
        return False

def is_finger_detected(ir_value):
    return ir_value > 50000  # Adjust threshold if needed

def read_pulse_oximeter():
    red_buffer = []
    ir_buffer = []
    print("📡 Reading from MAX30102...")
    timeout = 5  # Timeout in seconds
    start_time = time.time()

    while len(ir_buffer) < 100:
        red, ir = max30102_sensor.read_sequential()
        red_buffer.extend(red)
        ir_buffer.extend(ir)
        if time.time() - start_time > timeout:
            print("⏱ Timeout reached, stopping data read.")
            break
        time.sleep(0.1)

    red_buffer = np.array(red_buffer[:100])
    ir_buffer = np.array(ir_buffer[:100])
    hr, hr_valid, spo2, spo2_valid = hrcalc.calc_hr_and_spo2(ir_buffer, red_buffer)
    return hr, hr_valid, spo2, spo2_valid

def send_data_to_firebase(hr, spo2, object_temp):
    if hr is not None and spo2 is not None:
        data = {
            'heart_rate': hr,
            'spo2': spo2,
            'body_temperature': object_temp,
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        db.collection('health_data').add(data)
        print("📤 Data sent to Firebase.")

def sound_buzzer():
    GPIO.output(BUZZER_PIN, GPIO.HIGH)  # Turn on buzzer
    time.sleep(0.5)  # Buzzer duration
    GPIO.output(BUZZER_PIN, GPIO.LOW)   # Turn off buzzer

try:
    print("🔄 Waiting for human presence...")

    while True:
        # Check GY-906 (temperature) for body heat
        if not is_human_detected():
            print("⛔ No body temperature detected. Waiting...")
            time.sleep(1)
            continue

        # Check MAX30102 for finger IR detection
        ir_val = max30102_sensor.read_sequential()[1][-1]  # get latest IR value
        if not is_finger_detected(ir_val):
            print("☝️ Finger not detected on sensor. Waiting...")
            time.sleep(1)
            continue

        print("✅ Human detected! Measuring health data...")

        # Read HR & SpO2
        hr, hr_valid, spo2, spo2_valid = read_pulse_oximeter()

        # Read temperature
        object_temp = temp_sensor.object_temperature

        # Print results
        if hr_valid:
            print(f"❤️ Heart Rate: {hr:.2f} bpm")
        else:
            print("❌ Heart rate not valid")

        if spo2_valid:
            print(f"🩸 SpO₂: {spo2:.2f}%")
        else:
            print("❌ SpO₂ not valid")

        print(f"🌡 Body Temperature: {object_temp:.2f} °C")

        # Check for abnormal heart rate and SpO2
        if hr_valid and (hr < LOW_HEART_RATE_THRESHOLD or hr > HIGH_HEART_RATE_THRESHOLD):
            print("⚠️ Abnormal Heart Rate detected!")
            sound_buzzer()

        if spo2_valid and (spo2 < LOW_SPO2_THRESHOLD or spo2 > HIGH_SPO2_THRESHOLD):
            print("⚠️ Abnormal SpO₂ detected!")
            sound_buzzer()

        # Send data to Firebase
        if hr_valid and spo2_valid:
            send_data_to_firebase(hr, spo2, object_temp)

        print("🔁 Waiting 10 seconds before next reading...\n")
        time.sleep(10)

except KeyboardInterrupt:
    print("🛑 Monitoring stopped.")
    GPIO.cleanup()  # Clean up GPIO settings when done
