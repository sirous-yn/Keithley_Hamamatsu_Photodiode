#!/usr/bin/env python3

import time
import statistics
import serial

PORT = "/dev/ttyUSB0"
NUMBER_OF_READINGS = 20


def main():
    readings = []

    print("Keithley 6487 zero-corrected test")
    print("Photodiode disconnected.")
    print("Voltage-source output must remain OFF.")
    print()

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

        # Confirm safe source state before measuring.
        ser.write(b":SOUR:VOLT:STAT?\n")
        ser.flush()
        source_state = ser.readline().decode(
            "ascii", errors="replace"
        ).strip()

        ser.write(b":SOUR:VOLT?\n")
        ser.flush()
        source_voltage = ser.readline().decode(
            "ascii", errors="replace"
        ).strip()

        print(f"Source output state: {source_state}")
        print(f"Source voltage: {source_voltage} V")

        if source_state != "0":
            raise RuntimeError(
                "Voltage-source output is not confirmed OFF. "
                "Stopping the test."
            )

        if abs(float(source_voltage)) > 1e-9:
            raise RuntimeError(
                "Source voltage is not zero. Stopping the test."
            )

        print("\nCollecting readings...\n")

        for i in range(NUMBER_OF_READINGS):
            ser.write(b":READ?\n")
            ser.flush()

            response = ser.readline().decode(
                "ascii", errors="replace"
            ).strip()

            try:
                fields = response.split(",")
                current_text = fields[0].strip().rstrip("A")
                current = float(current_text)

                readings.append(current)

                print(
                    f"{i + 1:2d}: {current:.6e} A "
                    f"({current * 1e12:.4f} pA)"
                )

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


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nERROR: {exc}")
