import time
import serial
import statistics

PORT = "/dev/ttyUSB2"


def read_current(ser):
    ser.write(b":INIT\n")
    ser.flush()
    time.sleep(1)

    ser.write(b":FETCH?\n")
    ser.flush()

    response = ser.readline().decode(
        "ascii", errors="replace"
    ).strip()

    try:
        # The Keithley may return multiple comma-separated fields.
        # The first field is the current reading.
        current_text = response.split(",")[0].strip()
        current_text = current_text.rstrip("A")
        return float(current_text)

    except (ValueError, IndexError):
        print(f"Could not parse response: {response!r}")
        return None


def take_readings(ser, condition, number=10):
    input(
        f"\nSet the photodiode condition to {condition} "
        "and press Enter when ready..."
    )

    readings = []

    print(f"\nTaking {number} readings: {condition}")

    for i in range(number):
        current = read_current(ser)

        if current is not None:
            readings.append(current)
            print(f"{i + 1:2d}: {current * 1e12:.6f} pA")

    if readings:
        print(f"\nMean: {statistics.mean(readings) * 1e12:.6f} pA")

        if len(readings) > 1:
            print(
                "Standard deviation: "
                f"{statistics.stdev(readings) * 1e12:.6f} pA"
            )

    return readings


try:
    with serial.Serial(
        port=PORT,
        baudrate=9600,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=3,
    ) as ser:

        time.sleep(0.5)
        ser.reset_input_buffer()

        print("Connected to Keithley 6487.")
        print("No instrument configuration commands will be sent.")

        dark = take_readings(ser, "DARK")
        light = take_readings(ser, "ROOM LIGHT ON")

        if dark and light:
            dark_mean = statistics.mean(dark)
            light_mean = statistics.mean(light)

            print("\n========== COMPARISON ==========")
            print(f"Dark mean:  {dark_mean * 1e12:.6f} pA")
            print(f"Light mean: {light_mean * 1e12:.6f} pA")
            print(
                f"Difference: {(light_mean - dark_mean) * 1e12:.6f} pA"
            )

except Exception as exc:
    print(f"\nError: {exc}")
