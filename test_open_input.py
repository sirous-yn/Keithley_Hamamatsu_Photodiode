import time
import statistics
import serial


PORT = "/dev/ttyUSB0"
NUMBER_OF_READINGS = 20


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

        print("Keithley 6487 open-input test")
        print("Photodiode disconnected.")
        print("Collecting readings...\n")

        readings = []

        for i in range(NUMBER_OF_READINGS):
            ser.write(b":READ?\n")
            ser.flush()

            response = ser.readline().decode(
                "ascii", errors="replace"
            ).strip()

            fields = response.split(",")

            try:
                current_text = fields[0].strip().rstrip("A")
                current = float(current_text)
                readings.append(current)

                print(
                    f"{i + 1:2d}: "
                    f"{current:.6e} A "
                    f"({current * 1e12:.4f} pA)"
                )

                if i == 0:
                    print(f"    Full response: {response}")

            except (ValueError, IndexError):
                print(f"{i + 1:2d}: Invalid response: {response!r}")

            time.sleep(0.5)

        if readings:
            mean = statistics.mean(readings)

            print("\n========== SUMMARY ==========")
            print(f"Valid readings: {len(readings)}/{NUMBER_OF_READINGS}")
            print(f"Mean current: {mean:.6e} A ({mean * 1e12:.4f} pA)")

            if len(readings) > 1:
                std = statistics.stdev(readings)
                print(
                    f"Standard deviation: {std:.6e} A "
                    f"({std * 1e12:.4f} pA)"
                )

except Exception as exc:
    print(f"Error: {exc}")
