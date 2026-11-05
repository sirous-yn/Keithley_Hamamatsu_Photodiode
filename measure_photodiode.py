#!/usr/bin/env python3

import serial
import time
import csv
import statistics
from datetime import datetime
from pathlib import Path


# ============================================================
# USER SETTINGS
# ============================================================

PORT = "/dev/ttyUSB0"
BAUDRATE = 9600

NPLC = 10
CURRENT_RANGE = 2.1e-9

NUMBER_OF_READINGS = 20
READING_DELAY = 0.5

SETTLING_TIME = 10

OUTPUT_DIRECTORY = Path("measurements")


# ============================================================
# KEITHLEY COMMUNICATION
# ============================================================

def send_command(instrument, command, delay=0.2):

    instrument.write((command + "\n").encode("ascii"))
    instrument.flush()
    time.sleep(delay)


def query(instrument, command, delay=0.2):

    instrument.reset_input_buffer()

    send_command(instrument, command, delay)

    response = instrument.readline().decode(
        "ascii", errors="replace"
    ).strip()

    if not response:
        raise RuntimeError(
            f"No response received for command: {command}"
        )

    return response


def parse_current(response):

    fields = response.split(",")

    if not fields:
        raise ValueError(f"Invalid response: {response}")

    current_string = (
        fields[0].strip().upper().replace("A", "")
    )

    return float(current_string)


def verify_setting(instrument, name, command, expected):

    result = query(instrument, command)

    if isinstance(expected, float):
        passed = abs(float(result) - expected) < 1e-12

    elif expected == "CURR:DC":
        passed = "CURR:DC" in result.upper()

    else:
        passed = result.strip().replace('"', '') == expected

    status = "OK" if passed else "FAILED"

    print(f"{name:25s}: {result:20s} [{status}]")

    if not passed:
        raise RuntimeError(
            f"Verification failed for {name}: {result}"
        )

    return result


# ============================================================
# INSTRUMENT IDENTIFICATION
# ============================================================

def identify_instrument(instrument):

    print("\nChecking Keithley 6487...")

    identity = query(instrument, "*IDN?")

    print("Instrument:", identity)

    if "MODEL 6487" not in identity.upper():
        raise RuntimeError(
            "Connected instrument is not a Keithley 6487."
        )


# ============================================================
# INSTRUMENT CONFIGURATION
# ============================================================

def configure_instrument(instrument):

    print("\nConfiguring instrument...")

    # --------------------------------------------------------
    # Safety: voltage source OFF and programmed to 0 V
    # --------------------------------------------------------

    send_command(instrument, ":SOUR:VOLT:STAT OFF")
    send_command(instrument, ":SOUR:VOLT 0")

    # Verify source is safe before continuing
    source_state = query(instrument, ":SOUR:VOLT:STAT?")
    source_voltage = float(
        query(instrument, ":SOUR:VOLT?")
    )

    if source_state != "0":
        raise RuntimeError("Voltage source is not OFF.")

    if abs(source_voltage) > 1e-9:
        raise RuntimeError("Voltage source is not at 0 V.")

    # --------------------------------------------------------
    # Configure DC current measurement
    # --------------------------------------------------------

    send_command(instrument, ":FUNC 'CURR:DC'")
    send_command(instrument, f":CURR:NPLC {NPLC}")

    # Disable measurement averaging
    send_command(instrument, ":AVER:STAT OFF")

    # Enable autozero
    send_command(instrument, ":SYST:AZER ON")

    # Use fixed 2 nA range
    send_command(instrument, ":CURR:RANG:AUTO OFF")
    send_command(instrument, f":CURR:RANG {CURRENT_RANGE}")

    # --------------------------------------------------------
    # Fresh zero correction
    # --------------------------------------------------------

    print("\nAcquiring a fresh zero correction...")

    print("""
The photodiode can remain physically connected.

Please ensure:
- Photodiode is covered.
- Voltage source is OFF.
- Source voltage is 0 V.
""")

    # Enable internal zero-check
    send_command(instrument, ":SYST:ZCH ON")

    # Disable previously stored zero correction
    send_command(instrument, ":SYST:ZCOR OFF")

    # Trigger a reading with zero-check enabled
    send_command(instrument, ":INIT")

    # Wait for the instrument operation to complete
    completion = query(instrument, "*OPC?", delay=0.2)

    if completion != "1":
        raise RuntimeError(
            "Instrument did not complete zero-check acquisition."
        )

    # Acquire new zero-correction value
    send_command(instrument, ":SYST:ZCOR:ACQ")

    # Enable the newly acquired correction
    send_command(instrument, ":SYST:ZCOR ON")

    # Disable zero-check for actual measurement
    send_command(instrument, ":SYST:ZCH OFF")

    print("Fresh zero correction acquired successfully.")

    # --------------------------------------------------------
    # Verify final settings
    # --------------------------------------------------------

    print("\nVerifying settings...")

    verify_setting(
        instrument,
        "Measurement function",
        ":FUNC?",
        "CURR:DC"
    )

    verify_setting(
        instrument,
        "Integration time",
        ":CURR:NPLC?",
        float(NPLC)
    )

    verify_setting(
        instrument,
        "Current range",
        ":CURR:RANG?",
        CURRENT_RANGE
    )

    verify_setting(
        instrument,
        "Current autorange",
        ":CURR:RANG:AUTO?",
        "0"
    )

    verify_setting(
        instrument,
        "Autozero",
        ":SYST:AZER?",
        "1"
    )

    verify_setting(
        instrument,
        "Zero-check",
        ":SYST:ZCH?",
        "0"
    )

    verify_setting(
        instrument,
        "Zero correction",
        ":SYST:ZCOR?",
        "1"
    )

    verify_setting(
        instrument,
        "Voltage source",
        ":SOUR:VOLT:STAT?",
        "0"
    )

    verify_setting(
        instrument,
        "Source voltage",
        ":SOUR:VOLT?",
        0.0
    )

    print("\nAll instrument settings verified.")


# ============================================================
# PHOTODIODE MEASUREMENT
# ============================================================

def measure_photodiode(instrument):

    print("\n" + "=" * 55)
    print("PHOTODIODE MEASUREMENT")
    print("=" * 55)

    print("""
1. Keep the photodiode connected.
2. Keep the photodiode covered.
3. Keep the voltage source OFF.
4. Keep the source voltage at 0 V.

A fresh zero correction has already been acquired.
Zero-check is now OFF.
Zero correction is ON.
""")

    input("Press ENTER when ready to measure: ")

    # Allow instrument and photodiode to settle
    print(f"\nWaiting {SETTLING_TIME} seconds for settling...")

    time.sleep(SETTLING_TIME)

    print(f"\nCollecting {NUMBER_OF_READINGS} readings...\n")

    readings = []

    for i in range(NUMBER_OF_READINGS):

        response = query(
            instrument,
            ":READ?",
            delay=READING_DELAY
        )

        try:

            current = parse_current(response)

            readings.append(current)

            print(
                f"{i + 1:2d}: {current:+.6e} A "
                f"({current * 1e12:+.4f} pA)"
            )

        except ValueError as error:

            print(f"{i + 1:2d}: Invalid reading: {response}")
            print("Reason:", error)

    if len(readings) != NUMBER_OF_READINGS:

        raise RuntimeError(
            f"Expected {NUMBER_OF_READINGS} readings, "
            f"received {len(readings)}."
        )

    return readings


# ============================================================
# RESULTS AND CSV OUTPUT
# ============================================================

def save_results(readings):

    mean_current = statistics.mean(readings)

    std_current = (
        statistics.stdev(readings)
        if len(readings) > 1
        else 0.0
    )

    minimum = min(readings)
    maximum = max(readings)

    print("\n" + "=" * 55)
    print("PHOTODIODE MEASUREMENT SUMMARY")
    print("=" * 55)

    print(
        f"Valid readings:       "
        f"{len(readings)}/{NUMBER_OF_READINGS}"
    )

    print(f"Mean current:         {mean_current:.6e} A")
    print(f"Mean current:         {mean_current * 1e12:.4f} pA")

    print(f"Standard deviation:   {std_current:.6e} A")
    print(f"Standard deviation:   {std_current * 1e12:.4f} pA")

    print(f"Minimum current:      {minimum * 1e12:.4f} pA")
    print(f"Maximum current:      {maximum * 1e12:.4f} pA")

    # Create output directory
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = OUTPUT_DIRECTORY / (
        f"photodiode_{timestamp}.csv"
    )

    with open(filename, "w", newline="") as file:

        writer = csv.writer(file)

        writer.writerow([
            "Reading",
            "Current_A",
            "Current_pA"
        ])

        for index, current in enumerate(readings, start=1):

            writer.writerow([
                index,
                current,
                current * 1e12
            ])

        writer.writerow([])

        writer.writerow(["Mean_A", mean_current])
        writer.writerow(["Standard_Deviation_A", std_current])

    print(f"\nResults saved to: {filename}")


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 55)
    print("KEITHLEY 6487 - PHOTODIODE MEASUREMENT")
    print("=" * 55)

    instrument = None

    try:

        instrument = serial.Serial(
            PORT,
            BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=30
        )

        time.sleep(1)

        identify_instrument(instrument)

        configure_instrument(instrument)

        readings = measure_photodiode(instrument)

        save_results(readings)

        print("\nMeasurement completed successfully.")

    except Exception as error:

        print("\nERROR:")
        print(error)

        if instrument is not None and instrument.is_open:

            try:

                send_command(instrument, ":SOUR:VOLT:STAT OFF")
                send_command(instrument, ":SOUR:VOLT 0")
                send_command(instrument, ":SYST:ZCH ON")

                print(
                    "Safety state restored: "
                    "source OFF, 0 V, zero-check ON."
                )

            except Exception:

                print(
                    "WARNING: Could not fully restore "
                    "the instrument safety state."
                )

    finally:

        if instrument is not None and instrument.is_open:

            instrument.close()


if __name__ == "__main__":
    main()
