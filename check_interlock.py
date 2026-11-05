import serial
import time

with serial.Serial(
    "/dev/ttyUSB0",
    9600,
    timeout=3
) as ser:

    time.sleep(0.5)

    for command in [
        "*IDN?",
        ":SOUR:VOLT:STAT?",
        ":SOUR:VOLT:RANG?",
        ":SOUR:VOLT:INT:FAIL?",
        ":SYST:ERR?"
    ]:
        ser.reset_input_buffer()
        ser.write((command + "\n").encode())
        ser.flush()
        time.sleep(0.3)

        response = ser.readline().decode(
            errors="replace"
        ).strip()

        print(f"{command:25s} -> {response}")
