#!/usr/bin/env python3

import serial
import time
import csv
import statistics
from datetime import datetime
from pathlib import Path

# ============================================================
# SETTINGS
# ============================================================

PORT = "/dev/ttyUSB0"
BAUDRATE = 9600

NPLC = 10
CURRENT_RANGE = 2.1e-9

TEST_VOLTAGE = 0.010       # +10 mV
VOLTAGE_RANGE = 10         # 10 V source range
SOURCE_CURRENT_LIMIT = 25e-6

NUMBER_OF_READINGS = 10
READING_DELAY = 0.5
SETTLING_TIME = 10

OUTPUT_DIRECTORY = Path("measurements")


# ============================================================
# COMMUNICATION
# ============================================================

def write_command(inst, command, delay=0.2):
    inst.write((command + "\n").encode("ascii"))
    inst.flush()
    time.sleep(delay)


def query(inst, command, delay=0.2):
    inst.reset_input_buffer()
    write_command(inst, command, delay)

    response = inst.readline().decode(
        "ascii", errors="replace"
    ).strip()

    if not response:
        raise RuntimeError(
            f"No response to command: {command}"
        )

    return response


def read_current(inst):
    response = query(inst, ":READ?", READING_DELAY)
    value = response.split(",")[0].strip().upper().replace("A", "")
    return float(value)


def verify(inst, description, command, expected, tolerance=1e-9):

    result = query(inst, command)

    if isinstance(expected, float):
        passed = abs(float(result) - expected) <= tolerance
    else:
        passed = result.strip().replace('"', '') == expected

    print(
        f"{description:28s}: {result:20s} "
        f"[{'OK' if passed else 'FAILED'}]"
    )

    if not passed:
        raise RuntimeError(
            f"{description} verification failed: {result}"
        )

    return result


# ============================================================
# IDENTIFICATION AND INITIAL SAFETY CHECKS
# ============================================================

def identify(inst):

    print("\nChecking Keithley 6487...")

    identity = query(inst, "*IDN?")
    print("Instrument:", identity)

    if "MODEL 6487" not in identity.upper():
        raise RuntimeError("Instrument is not a Keithley 6487.")


def initial_safety_check(inst):

    print("\nChecking initial source state...")

    # Ensure the source is OFF and at zero.
    write_command(inst, ":SOUR:VOLT 0")
    write_command(inst, ":SOUR:VOLT:STAT OFF")

    state = query(inst, ":SOUR:VOLT:STAT?")
    voltage = float(query(inst, ":SOUR:VOLT?"))

    if state != "0" or abs(voltage) > 1e-9:
        raise RuntimeError(
            "Voltage source is not safely OFF at 0 V."
        )

    interlock = query(inst, ":SOUR:VOLT:INT:FAIL?")

    print("Interlock status:", interlock)

    if interlock != "0":
        raise RuntimeError(
            "Interlock is asserted. Do not bypass it."
        )


# ============================================================
# CURRENT MEASUREMENT CONFIGURATION
# ============================================================

def configure_current_measurement(inst):

    print("\nConfiguring current measurement...")

    write_command(inst, ":FUNC 'CURR:DC'")
    write_command(inst, f":CURR:NPLC {NPLC}")

    write_command(inst, ":SYST:AZER ON")

    write_command(inst, ":CURR:RANG:AUTO OFF")
    write_command(inst, f":CURR:RANG {CURRENT_RANGE}")

    write_command(inst, ":SYST:ZCH ON")
    write_command(inst, ":SYST:ZCOR OFF")

    # Acquire fresh zero correction.
    print("\nAcquiring fresh zero correction...")

    write_command(inst, ":INIT")

    if query(inst, "*OPC?") != "1":
        raise RuntimeError(
            "Zero-check measurement did not complete."
        )

    write_command(inst, ":SYST:ZCOR:ACQ")

    write_command(inst, ":SYST:ZCOR ON")
    write_command(inst, ":SYST:ZCH OFF")

    print("Fresh zero correction acquired.")


# ============================================================
# VOLTAGE SOURCE CONFIGURATION
# ============================================================

def configure_voltage_source(inst):

    print("\nConfiguring voltage source...")

    # Use the 10 V range.
    write_command(inst, ":SOUR:VOLT:RANG 10")

    # Lowest available current limit.
    write_command(
        inst,
        f":SOUR:VOLT:ILIM {SOURCE_CURRENT_LIMIT}"
    )

    # Program zero before enabling output.
    write_command(inst, ":SOUR:VOLT 0")

    # Check interlock immediately before enabling.
    interlock = query(inst, ":SOUR:VOLT:INT:FAIL?")

    if interlock != "0":
        raise RuntimeError(
            "Interlock asserted. Voltage output will not be enabled."
        )

    input(
        "\nConfirm photodiode is covered and connections are secure.\n"
        "Press ENTER to enable the source at 0 V: "
    )

    write_command(inst, ":SOUR:VOLT:STAT ON")

    if query(inst, ":SOUR:VOLT:STAT?") != "1":
        raise RuntimeError(
            "Voltage source failed to turn ON."
        )

    # Increase to the requested reverse bias.
    write_command(inst, f":SOUR:VOLT {TEST_VOLTAGE}")

    actual_setpoint = float(
        query(inst, ":SOUR:VOLT?")
    )

    if abs(actual_setpoint - TEST_VOLTAGE) > 1e-9:
        raise RuntimeError(
            "Voltage setpoint verification failed."
        )

    print(f"\nVoltage source enabled.")
    print(f"Programmed voltage: {actual_setpoint:.6f} V")
    print(f"Current limit: {SOURCE_CURRENT_LIMIT * 1e6:.0f} µA")

    print("\nVerifying measurement settings...")

    verify(inst, "Current function", ":FUNC?", "CURR:DC")
    verify(inst, "Integration time", ":CURR:NPLC?", float(NPLC), 0.01)
    verify(inst, "Current range", ":CURR:RANG?", CURRENT_RANGE, 1e-11)
    verify(inst, "Autorange", ":CURR:RANG:AUTO?", "0")
    verify(inst, "Autozero", ":SYST:AZER?", "1")
    verify(inst, "Zero-check", ":SYST:ZCH?", "0")
    verify(inst, "Zero correction", ":SYST:ZCOR?", "1")
    verify(inst, "Source output", ":SOUR:VOLT:STAT?", "1")
    verify(inst, "Source voltage", ":SOUR:VOLT?", TEST_VOLTAGE, 1e-9)

    print("\nAll settings verified.")


# ============================================================
# DATA COLLECTION
# ============================================================

def collect_readings(inst, label):

    print("\n" + "=" * 55)
    print(label)
    print("=" * 55)

    print(f"Waiting {SETTLING_TIME} seconds...")
    time.sleep(SETTLING_TIME)

    readings = []

    for i in range(NUMBER_OF_READINGS):

        current = read_current(inst)
        readings.append(current)

        print(
            f"{i + 1:2d}: {current:+.6e} A "
            f"({current * 1e12:+.4f} pA)"
        )

    return readings


# ============================================================
# SUMMARY
# ============================================================

def summarize(label, readings):

    mean = statistics.mean(readings)
    std = statistics.stdev(readings)

    print(f"\n{label} summary:")
    print(f"Mean: {mean:.6e} A ({mean * 1e12:.4f} pA)")
    print(f"Std:  {std:.6e} A ({std * 1e12:.4f} pA)")
    print(
        f"Range: {min(readings) * 1e12:.4f} to "
        f"{max(readings) * 1e12:.4f} pA"
    )

    return mean, std


def save_data(corrected, uncorrected):

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = OUTPUT_DIRECTORY / (
        f"photodiode_{TEST_VOLTAGE}mV_{timestamp}.csv"
    )

    with open(filename, "w", newline="") as file:

        writer = csv.writer(file)

        writer.writerow([
            "Reading",
            "Corrected_Current_A",
            "Corrected_Current_pA",
            "Uncorrected_Current_A",
            "Uncorrected_Current_pA"
        ])

        for i in range(NUMBER_OF_READINGS):

            writer.writerow([
                i + 1,
                corrected[i],
                corrected[i] * 1e12,
                uncorrected[i],
                uncorrected[i] * 1e12
            ])

    print(f"\nResults saved to: {filename}")


# ============================================================
# SAFE SHUTDOWN
# ============================================================

def safe_shutdown(inst):

    print("\nReturning voltage source to 0 V...")

    try:
        write_command(inst, ":SOUR:VOLT 0")
        time.sleep(1)
        write_command(inst, ":SOUR:VOLT:STAT OFF")

        print("Voltage source OFF.")
        print("Source voltage:", query(inst, ":SOUR:VOLT?"))

        write_command(inst, ":SYST:ZCH ON")

        print("Zero-check ON.")

    except Exception as error:
        print("WARNING: Safe shutdown error:", error)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 55)
    print("KEITHLEY 6487 - S2281 DARK CURRENT AT {TEST_VOLTAGE} mV")
    print("=" * 55)

    inst = None

    try:

        inst = serial.Serial(
            PORT,
            BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=30
        )

        time.sleep(1)

        identify(inst)
        initial_safety_check(inst)
        configure_current_measurement(inst)
        configure_voltage_source(inst)

        corrected = collect_readings(
            inst,
            "ZERO-CORRECTED CURRENT"
        )

        # Preserve the same physical operating conditions,
        # but disable offset subtraction for comparison.
        print("\nDisabling zero correction for raw comparison...")
        write_command(inst, ":SYST:ZCOR OFF")

        uncorrected = collect_readings(
            inst,
            "UNCORRECTED CURRENT"
        )

        print("\n" + "=" * 55)
        print("FINAL RESULTS")
        print("=" * 55)

        corrected_mean, corrected_std = summarize(
            "Corrected",
            corrected
        )

        uncorrected_mean, uncorrected_std = summarize(
            "Uncorrected",
            uncorrected
        )

        print("\nDatasheet typical dark current: 50 pA")
        print(
            "Corrected result / datasheet typical: "
            f"{abs(corrected_mean) * 1e12 / 50:.3f}"
        )

        save_data(corrected, uncorrected)

    except Exception as error:

        print("\nERROR:", error)

    finally:

        if inst is not None and inst.is_open:
            safe_shutdown(inst)
            inst.close()

    print("\nMeasurement session finished.")


if __name__ == "__main__":
    main()
