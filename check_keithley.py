import sys
import time
import serial


if len(sys.argv) != 2:
    print("Usage: python3 check_keithley.py PORT")
    print("Example: python3 check_keithley.py /dev/ttyUSB0")
    sys.exit(1)


port = sys.argv[1]

queries = [
    "*IDN?",
    ":FUNC?",
    ":CURR:RANG?",
    ":CURR:RANG:AUTO?",
    ":CURR:NPLC?",
    ":SYST:ZCH?",
    ":SYST:ZCOR?",
    ":SYST:AZER?",
    ":SOUR:VOLT?",
    ":SOUR:VOLT:STAT?",
]


try:
    with serial.Serial(
        port=port,
        baudrate=9600,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=3,
    ) as ser:

        time.sleep(0.5)

        # Discard any old response already waiting in the receive buffer.
        ser.reset_input_buffer()

        for command in queries:
            ser.write((command + "\n").encode("ascii"))
            ser.flush()

            response = ser.readline().decode(
                "ascii", errors="replace"
            ).strip()

            print(f"{command:22s} -> {response or '[no response]'}")

except Exception as exc:
    print(f"Communication error: {exc}")
    sys.exit(1)
