#!/usr/bin/env python3

import time
import serial

PORT = "/dev/ttyUSB0"
BAUDRATE = 9600


def send(ser, command, delay=0.3):
    """Send a command to the Keithley."""
    ser.write((command + "\n").encode("ascii"))
    ser.flush()
    time.sleep(delay)


def query(ser, command):
    """Send a query and return the response."""
    send(ser, command)

    response = ser.readline().decode(
        "ascii", errors="replace"
    ).strip()

    print(f"{command:24s} -> {response}")
    return response


def main():

    print("=" * 60)
    print("Keithley 6487 - Hamamatsu S2281 configuration")
    print("=" * 60)

    print("\nIMPORTANT:")
    print("- Photodiode must remain disconnected.")
    print("- Voltage-source output must remain OFF.")
    print("- Voltage source will remain at 0 V.")

    with serial.Serial(
        port=PORT,
        baudrate=BAUDRATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=3,
    ) as ser:

        time.sleep(0.5)
        ser.reset_input_buffer()

        # --------------------------------------------------
        # 1. Verify instrument identity
        # --------------------------------------------------

        print("\n1. Instrument identification")

        identity = query(ser, "*IDN?")

        if "MODEL 6487" not in identity:
            raise RuntimeError(
                "Keithley 6487 was not identified. "
                "Configuration stopped."
            )

        # --------------------------------------------------
        # 2. Keep voltage source disabled
        # --------------------------------------------------

        print("\n2. Voltage source")

        send(ser, ":SOUR:VOLT:STAT OFF")
        send(ser, ":SOUR:VOLT 0")

        # --------------------------------------------------
        # 3. Configure current measurement
        # --------------------------------------------------

        print("\n3. Current measurement configuration")

        send(ser, ":FUNC 'CURR'")
        send(ser, ":CURR:NPLC 10")
        send(ser, ":SYST:AZER ON")

        # Disable averaging.
        send(ser, ":CURR:AVER:STAT OFF")

        # Select the 2 nA range for zero correction.
        send(ser, ":CURR:RANG:AUTO OFF")
        send(ser, ":CURR:RANG 2E-9")

        # --------------------------------------------------
        # 4. Perform zero correction
        # --------------------------------------------------

        print("\n4. Acquiring a fresh zero correction")

        # Enable zero check.
        send(ser, ":SYST:ZCH ON", delay=1.0)

        # Ensure zero correction is OFF before acquisition.
        send(ser, ":SYST:ZCOR OFF", delay=0.5)

        # Trigger a reading with zero check enabled.
        send(ser, ":INIT", delay=1.0)

        # Acquire the triggered reading as zero correction.
        send(ser, ":SYST:ZCOR:ACQ", delay=1.0)

        # Disable zero check.
        send(ser, ":SYST:ZCH OFF", delay=0.5)

        # Enable zero correction.
        send(ser, ":SYST:ZCOR ON", delay=0.5)

        # --------------------------------------------------
        # 5. Enable automatic ranging
        # --------------------------------------------------

        print("\n5. Enable automatic current ranging")

        send(ser, ":CURR:RANG:AUTO ON")

        # --------------------------------------------------
        # 6. Verify final settings
        # --------------------------------------------------

        print("\n6. Final configuration verification")
        print("-" * 60)

        query(ser, ":FUNC?")
        query(ser, ":CURR:NPLC?")
        query(ser, ":CURR:RANG:AUTO?")
        query(ser, ":SYST:ZCH?")
        query(ser, ":SYST:ZCOR?")
        query(ser, ":SYST:AZER?")
        query(ser, ":SOUR:VOLT?")
        query(ser, ":SOUR:VOLT:STAT?")

        print("\n" + "=" * 60)
        print("Configuration sequence completed.")
        print("Photodiode must remain disconnected.")
        print("=" * 60)


if __name__ == "__main__":

    try:
        main()

    except Exception as exc:
        print(f"\nERROR: {exc}")
