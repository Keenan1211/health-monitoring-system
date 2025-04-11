import time
import board
import busio
import adafruit_mlx90614
import max30102
import firebase_admin
from firebase_admin import credentials, db
import RPi.GPIO as GPIO  # GPIO import added

# ============ Buzzer Setup ============
BUZZER_PIN = 17  # GPIO17 (Pin 11 on Pi)
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# ============ Firebase Setup ============
cred = credentials.Certificate("smart-health-monitoring-87119-firebase-adminsdk-y178i-8f2138caa7.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://smart-health-monitoring-87119-default-rtdb.asia-southeast1.firebasedatabase.app/'  # Replace with your URL
})

# ============ GY-906 (MLX90614) Setup ============
i2c = busio.I2C(board.SCL, board.SDA)
mlx = adafruit_mlx90614.MLX90614(i2c)

# ============ MAX30102 Setup ============
m = max30102.MAX30102()
m.setup()
m.set_leds_pulse_amplitude(0x0A, 0x0A, 0x0A, 0)

# Function to send data to Firebase
def send_to_firebase(temp, pulse_rate, spo2):
    ref = db.reference("health_data")
    ref.set({
        "temperature": temp,
        "pulse_rate": pulse_rate,
        "SpO2": spo2
    })

# Main Loop to read sensor data and send to Firebase
try:
    print("Starting health monitoring system...")
    while True:
        # === Read from GY-906 ===
        ambient_temp = mlx.ambient_temperature
        object_temp = mlx.object_temperature

        # === Read from MAX30102 ===
        red, ir = m.read_sequential()

        # Check if data exists
        if len(ir) > 0:
            ir_signal = ir[-1]
            red_signal = red[-1]

            print(f"Ambient: {ambient_temp:.2f} °C | Object: {object_temp:.2f} °C")
            print(f"IR: {ir_signal} | RED: {red_signal}")

            # === Process to Pulse Rate and SpO2 ===
            # For simplicity, we assume SpO2 and Pulse Rate are based on signal strength
            pulse_rate = ir_signal // 1000  # Placeholder for heart rate
            spo2 = 100 - (red_signal // 1000)  # Placeholder for SpO2 (simplified)

            print(f"Pulse Rate: {pulse_rate} bpm | SpO2: {spo2}%")

            # === Send Data to Firebase ===
            send_to_firebase(object_temp, pulse_rate, spo2)

            # === Alert condition: Buzzer on if high temperature or low SpO2 ===
            if object_temp > 38.0 or pulse_rate < 50:  # Example of low pulse rate
                print("🚨 ALERT: Temp high or Pulse low!")
                GPIO.output(BUZZER_PIN, GPIO.HIGH)
                time.sleep(0.5)
                GPIO.output(BUZZER_PIN, GPIO.LOW)
            else:
                GPIO.output(BUZZER_PIN, GPIO.LOW)

        else:
            print("Waiting for MAX30102 data...")

        print("-" * 40)
        time.sleep(1)

except KeyboardInterrupt:
    print("Stopping monitoring...")

finally:
    GPIO.cleanup()
