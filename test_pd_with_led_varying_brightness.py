#!/usr/bin/env python3

import sys
import csv
import time
import statistics
from datetime import datetime
from pathlib import Path

import serial


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from led_controls import LED


# ============================================================
# USER SETTINGS
# ============================================================

# Serial ports
KEITHLEY_PORT = "/dev/ttyUSB2"
LED_PORT = "/dev/ttyUSB0"

BAUDRATE = 9600

# Keithley settings (unchanged)
PD_BIAS_VOLTAGE = 0.01
PD_bias_volt=10
CURRENT_RANGE = 2.1e-9
CURRENT_LIMIT = 25e-6
NPLC = 10

# LED settings
LED_CHANNEL = "4"
LED_WAVELENGTH_NM = 470
LED_FREQUENCY_HZ = 3

# LED bias scan (volts)
#LED_VOLTAGES = [6, 8, 10, 12, 15]
LED_VOLTAGES = [15]


# Measurement sequence at each voltage
DARK_BEFORE_READINGS = 30
LED_ON_READINGS = 50
DARK_AFTER_READINGS = 30

LED_SETTLING_TIME = 5

# Output
OUTPUT_DIRECTORY = Path("measurements/led_brightness_scan")


# ============================================================
# KEITHLEY COMMUNICATION
# ============================================================

def send_command(instrument, command, delay=0.15):

    instrument.write((command + "\n").encode("ascii"))
    instrument.flush()

    if delay:
        time.sleep(delay)


def query(instrument, command, delay=0.15):

    instrument.reset_input_buffer()
    send_command(instrument, command, delay)

    response = instrument.readline().decode(
        "ascii",
        errors="replace"
    ).strip()

    if not response:
        raise RuntimeError(
            f"No response from Keithley for command: {command}"
        )

    return response


def parse_current(response):

    fields = response.split(",")

    if not fields:
        raise ValueError(f"Invalid reading: {response}")

    current_string = fields[0].strip().upper().replace("A", "")

    return float(current_string)


# ============================================================
# KEITHLEY CONFIGURATION
# ============================================================

def configure_keithley(instrument):

    print("\nChecking Keithley 6487...")

    idn = query(instrument, "*IDN?")
    print("Instrument:", idn)

    if "6487" not in idn:
        raise RuntimeError(
            "Connected instrument is not a Keithley 6487."
        )

    print("\nConfiguring Keithley...")

    # Voltage source OFF during configuration
    send_command(instrument, ":SOUR:VOLT:STAT OFF")
    send_command(instrument, ":SOUR:VOLT 0")

    # Current measurement configuration
    send_command(instrument, ":FUNC 'CURR:DC'")
    send_command(instrument, f":CURR:NPLC {NPLC}")
    send_command(instrument, f":CURR:RANG {CURRENT_RANGE}")
    send_command(instrument, ":CURR:RANG:AUTO OFF")
    send_command(instrument, ":AVER:STAT OFF")
    send_command(instrument, ":SYST:AZER ON")

    # Fresh zero correction
    print("\nPerforming fresh zero correction...")

    send_command(instrument, ":SYST:ZCH ON")
    send_command(instrument, ":SYST:ZCOR OFF")

    time.sleep(3)

    send_command(instrument, ":INIT")
    query(instrument, "*OPC?")

    send_command(instrument, ":SYST:ZCOR:ACQ")
    send_command(instrument, ":SYST:ZCOR ON")

    time.sleep(1)

    send_command(instrument, ":SYST:ZCH OFF")

    # Voltage source configuration
    send_command(instrument, ":SOUR:VOLT:RANG 10")
    send_command(instrument, f":SOUR:VOLT:ILIM {CURRENT_LIMIT}")
    send_command(instrument, f":SOUR:VOLT {PD_BIAS_VOLTAGE}")
    send_command(instrument, ":SOUR:VOLT:STAT ON")

    time.sleep(2)

    # Verify important settings
    print("\nVerifying settings...")

    checks = {
        "NPLC": (":CURR:NPLC?", float(NPLC)),
        "Current range": (":CURR:RANG?", CURRENT_RANGE),
        "Zero check": (":SYST:ZCH?", "0"),
        "Zero correction": (":SYST:ZCOR?", "1"),
        "Source voltage": (":SOUR:VOLT?", PD_BIAS_VOLTAGE),
        "Source output": (":SOUR:VOLT:STAT?", "1"),
    }

    for name, (command, expected) in checks.items():

        result = query(instrument, command)

        if isinstance(expected, float):

            tolerance = max(abs(expected) * 0.02, 1e-12)

            passed = (
                abs(float(result) - expected) <= tolerance
            )

        else:

            passed = result.strip() == expected

        print(
            f"{name:20s}: {result:20s} "
            f"[{'OK' if passed else 'FAILED'}]"
        )

        if not passed:
            raise RuntimeError(
                f"Keithley setting verification failed: {name}"
            )

    print("\nKeithley configuration completed.")


# ============================================================
# DATA COLLECTION
# ============================================================

def collect_readings(
    instrument,
    writer,
    csv_file,
    phase,
    voltage,
    number_of_readings,
    start_time
):

    readings = []

    print("\n" + "=" * 60)
    print(f"PHASE: {phase}")
    print(f"LED bias: {voltage:.2f} V")
    print("=" * 60)

    print(f"Collecting {number_of_readings} readings...\n")

    for i in range(number_of_readings):

        response = query(
            instrument,
            ":READ?",
            delay=0.05
        )

        current = parse_current(response)

        timestamp = datetime.now().isoformat(
            timespec="milliseconds"
        )

        elapsed = time.monotonic() - start_time
        current_pa = current * 1e12

        readings.append(current)

        writer.writerow([
            timestamp,
            elapsed,
            voltage,
            phase,
            i + 1,
            current,
            current_pa,
            response
        ])

        csv_file.flush()

        print(
            f"{i + 1:3d}/{number_of_readings}: "
            f"{current_pa:+.4f} pA"
        )

    mean_current = statistics.mean(readings)

    std_current = (
        statistics.stdev(readings)
        if len(readings) > 1
        else 0.0
    )

    print("\nPhase summary:")
    print(f"Mean: {mean_current * 1e12:+.4f} pA")
    print(f"SD:   {std_current * 1e12:.4f} pA")

    return readings


# ============================================================
# RESULTS
# ============================================================

def summarize_phase(name, voltage, readings):

    mean_current = statistics.mean(readings)

    std_current = (
        statistics.stdev(readings)
        if len(readings) > 1
        else 0.0
    )

    return {
        "LED_Bias_V": voltage,
        "Phase": name,
        "Number_of_Readings": len(readings),
        "Mean_A": mean_current,
        "Mean_pA": mean_current * 1e12,
        "SD_A": std_current,
        "SD_pA": std_current * 1e12,
        "Minimum_pA": min(readings) * 1e12,
        "Maximum_pA": max(readings) * 1e12,
    }


def save_summary(results, filename):

    with open(filename, "w", newline="") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(results[0].keys())
        )

        writer.writeheader()
        writer.writerows(results)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("PHOTODIODE / LED BRIGHTNESS SCAN")
    print("=" * 60)

    print(f"Photodiode bias: {PD_BIAS_VOLTAGE * 1000:.1f} mV")
    print(f"LED channel:     {LED_CHANNEL}")
    print(f"LED wavelength:  {LED_WAVELENGTH_NM} nm")
    print(f"LED frequency:   {LED_FREQUENCY_HZ} Hz")

    print("\nLED bias scan:")
    for voltage in LED_VOLTAGES:
        print(f"  {voltage} V")

    print("\nMeasurement sequence at each voltage:")
    print(f"  LED OFF: {DARK_BEFORE_READINGS} readings")
    print(f"  LED ON:  {LED_ON_READINGS} readings")
    print(f"  LED OFF: {DARK_AFTER_READINGS} readings")

    print("\nIMPORTANT:")
    print("- Keep the optical geometry unchanged.")
    print("- Keep the photodiode in its dark enclosure.")
    print("- Do not change the wiring during the test.")
    print("- PD bias remains fixed at 10 mV.")
    print("- LED frequency remains fixed at 3 Hz.")

    input("\nPress ENTER when everything is ready...")

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    data_filename = (
        OUTPUT_DIRECTORY / f"PD_LED_scan_{timestamp}.csv"
    )

    summary_filename = (
        OUTPUT_DIRECTORY / f"PD_LED_scan_summary_PD_{PD_bias_volt}mV_{timestamp}.csv"
    )

    instrument = None
    led = None

    all_results = []

    try:

        # ----------------------------------------------------
        # Connect to Keithley
        # ----------------------------------------------------

        print("\nConnecting to Keithley...")

        instrument = serial.Serial(
            port=KEITHLEY_PORT,
            baudrate=BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=5
        )

        time.sleep(1)

        configure_keithley(instrument)

        # ----------------------------------------------------
        # Connect to LED board
        # ----------------------------------------------------

        print("\nConnecting to LED board...")

        led = LED(port=LED_PORT)

        # Make sure LED is initially OFF
        led.power_off()

        print("\nLED is OFF.")

        start_time = time.monotonic()

        # ----------------------------------------------------
        # Open raw data file
        # ----------------------------------------------------

        with open(data_filename, "w", newline="") as csv_file:

            writer = csv.writer(csv_file)

            writer.writerow([
                "Timestamp",
                "Elapsed_s",
                "LED_Bias_V",
                "Phase",
                "Reading",
                "Current_A",
                "Current_pA",
                "Raw_Keithley_Response"
            ])

            csv_file.flush()

            # ================================================
            # BRIGHTNESS SCAN
            # ================================================

            for index, voltage in enumerate(LED_VOLTAGES):

                print("\n\n")
                print("#" * 60)
                print(f"LED BIAS POINT {index + 1}/{len(LED_VOLTAGES)}")
                print(f"LED BIAS VOLTAGE: {voltage} V")
                print("#" * 60)

                # --------------------------------------------
                # DARK BEFORE
                # --------------------------------------------

                print("\nLED OFF: measuring dark current.")

                dark_before = collect_readings(
                    instrument,
                    writer,
                    csv_file,
                    "DARK_BEFORE",
                    voltage,
                    DARK_BEFORE_READINGS,
                    start_time
                )

                # --------------------------------------------
                # LED ON
                # --------------------------------------------

                print(f"\nTurning ON LED at {voltage} V...")

                led.turn_on(
                    channel=LED_CHANNEL,
                    voltage=voltage,
                    rate=LED_FREQUENCY_HZ
                )

                print(
                    f"\nWaiting {LED_SETTLING_TIME} seconds..."
                )

                time.sleep(LED_SETTLING_TIME)

                illuminated = collect_readings(
                    instrument,
                    writer,
                    csv_file,
                    "LED_ON",
                    voltage,
                    LED_ON_READINGS,
                    start_time
                )

                # --------------------------------------------
                # LED OFF
                # --------------------------------------------

                print("\nTurning OFF LED...")

                led.power_off()

                print(
                    f"\nWaiting {LED_SETTLING_TIME} seconds "
                    "before dark measurement..."
                )

                time.sleep(LED_SETTLING_TIME)

                dark_after = collect_readings(
                    instrument,
                    writer,
                    csv_file,
                    "DARK_AFTER",
                    voltage,
                    DARK_AFTER_READINGS,
                    start_time
                )

                # --------------------------------------------
                # CALCULATE PHOTOCURRENT
                # --------------------------------------------

                mean_dark_before = statistics.mean(dark_before)
                mean_illuminated = statistics.mean(illuminated)
                mean_dark_after = statistics.mean(dark_after)

                mean_dark = (
                    mean_dark_before + mean_dark_after
                ) / 2.0

                photocurrent = mean_illuminated - mean_dark

                print("\n" + "-" * 60)
                print(f"RESULT AT {voltage} V")
                print("-" * 60)

                print(
                    f"Dark before:    "
                    f"{mean_dark_before * 1e12:+.4f} pA"
                )

                print(
                    f"LED illuminated: "
                    f"{mean_illuminated * 1e12:+.4f} pA"
                )

                print(
                    f"Dark after:     "
                    f"{mean_dark_after * 1e12:+.4f} pA"
                )

                print(
                    f"Net photocurrent: "
                    f"{photocurrent * 1e12:+.4f} pA"
                )

                # Store results
                all_results.append({
                    "LED_Bias_V": voltage,
                    "Dark_Before_pA": mean_dark_before * 1e12,
                    "LED_On_pA": mean_illuminated * 1e12,
                    "Dark_After_pA": mean_dark_after * 1e12,
                    "Average_Dark_pA": mean_dark * 1e12,
                    "Photocurrent_pA": photocurrent * 1e12,
                    "LED_On_SD_pA": (
                        statistics.stdev(illuminated) * 1e12
                    ),
                })

                # Also save individual phase statistics
                all_results.append(
                    summarize_phase(
                        "DARK_BEFORE",
                        voltage,
                        dark_before
                    )
                )

                all_results.append(
                    summarize_phase(
                        "LED_ON",
                        voltage,
                        illuminated
                    )
                )

                all_results.append(
                    summarize_phase(
                        "DARK_AFTER",
                        voltage,
                        dark_after
                    )
                )

        # ----------------------------------------------------
        # SAVE SUMMARY
        # ----------------------------------------------------

        with open(summary_filename, "w", newline="") as file:

            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "LED_Bias_V",
                    "Dark_Before_pA",
                    "LED_On_pA",
                    "Dark_After_pA",
                    "Average_Dark_pA",
                    "Photocurrent_pA",
                    "LED_On_SD_pA",
                ]
            )

            writer.writeheader()

            # Keep only the photocurrent summary rows
            for row in all_results:

                if "Photocurrent_pA" in row:
                    writer.writerow(row)

        # ----------------------------------------------------
        # FINAL RESULTS
        # ----------------------------------------------------

        print("\n\n")
        print("=" * 70)
        print("FINAL PHOTOCURRENT RESULTS")
        print("=" * 70)

        print(
            f"{'LED Bias (V)':>15s} "
            f"{'Photocurrent (pA)':>20s} "
            f"{'LED SD (pA)':>15s}"
        )

        print("-" * 70)

        for result in all_results:

            if "Photocurrent_pA" not in result:
                continue

            print(
                f"{result['LED_Bias_V']:15.2f} "
                f"{result['Photocurrent_pA']:20.4f} "
                f"{result['LED_On_SD_pA']:15.4f}"
            )

        print("\nSaved files:")
        print(data_filename)
        print(summary_filename)

        print("\nBrightness scan completed successfully.")

    except KeyboardInterrupt:

        print("\n\nMeasurement interrupted by user.")

    except Exception as error:

        print("\nERROR:")
        print(error)

    finally:

        # ----------------------------------------------------
        # SAFE LED SHUTDOWN
        # ----------------------------------------------------

        if led is not None:

            try:
                print("\nTurning LED OFF...")
                led.power_off()
                led.close()

            except Exception as error:
                print(
                    "WARNING: LED shutdown problem:",
                    error
                )

        # ----------------------------------------------------
        # SAFE KEITHLEY SHUTDOWN
        # ----------------------------------------------------

        if instrument is not None and instrument.is_open:

            try:

                print(
                    "Setting Keithley source to 0 V and OFF..."
                )

                send_command(instrument, ":SOUR:VOLT 0")
                send_command(instrument, ":SOUR:VOLT:STAT OFF")
                send_command(instrument, ":SYST:ZCH ON")

                print(
                    "Keithley source OFF; zero-check ON."
                )

            except Exception as error:

                print(
                    "WARNING: Keithley shutdown problem:",
                    error
                )

                print(
                    "Please verify the front panel manually."
                )

            finally:

                instrument.close()

        print("\nTest script finished.")


if __name__ == "__main__":
    main()
