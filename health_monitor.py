import time
import numpy as np
import board
import busio
from max30102.max30102 import MAX30102
from max30102.hrcalc import calc_hr_and_spo2
import adafruit_mlx90614

# Initialize MAX30102 sensor
max30102_sensor = MAX30102()

# Initialize MLX90614 temperature sensor
i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
temp_sensor = adafruit_mlx90614.MLX90614(i2c)

def is_human_detected():
    object_temp = temp_sensor.object_temperature
    print(f"👤 Object Temperature: {object_temp:.2f} °C")

    # Lower the threshold to 30.0°C for better detection
    if object_temp > 30.0:
        return True
    return False

def is_finger_detected(ir_value):
    return ir_value > 50000  # adjust threshold if needed

def read_pulse_oximeter():
    red_buffer = []
    ir_buffer = []

    print("📡 Reading from MAX30102...")
    while len(ir_buffer) < 100:
        red, ir = max30102_sensor.read_sequential()
        red_buffer.extend(red)
        ir_buffer.extend(ir)
        time.sleep(0.1)

    red_buffer = np.array(red_buffer[:100])
    ir_buffer = np.array(ir_buffer[:100])

    hr, hr_valid, spo2, spo2_valid = hrcalc.calc_hr_and_spo2(ir_buffer, red_buffer)
    return hr, hr_valid, spo2, spo2_valid

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
        print("🔁 Waiting 10 seconds before next reading...\n")
        time.sleep(10)

except KeyboardInterrupt:
    print("🛑 Monitoring stopped.")
