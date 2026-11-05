#!/usr/bin/env python3

import serial
import time

PORT = "/dev/ttyUSB0"
BAUDRATE = 9600

TEST_VOLTAGE = 0.100


def send(ser, command, delay=0.3):
    ser.write((command + "\n").encode())
    ser.flush()
    time.sleep(delay)


def query(ser, command):
    ser.reset_input_buffer()
    send(ser, command)
    return ser.readline().decode(errors="replace").strip()


def main():

    ser = None

    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=3)
        time.sleep(1)

        print("Instrument:", query(ser, "*IDN?"))

        # Confirm output is OFF
        if query(ser, ":SOUR:VOLT:STAT?") != "0":
            raise RuntimeError("Voltage output must be OFF.")

        # Confirm 10 V range
        print("Voltage range:", query(ser, ":SOUR:VOLT:RANG?"))

        # Correct interlock query
        interlock = query(ser, ":SOUR:VOLT:INT:FAIL?")
        print("Interlock:", interlock)

        if interlock != "0":
            raise RuntimeError("Interlock is asserted.")

        # Clear old errors
        while True:
            error = query(ser, ":SYST:ERR?")
            print("Error queue:", error)

            if error.startswith("0,"):
                break

        print("\nConfiguring source...")

        send(ser, ":SOUR:VOLT:STAT OFF")
        send(ser, ":SOUR:VOLT:RANG 10")
        send(ser, ":SOUR:VOLT:ILIM 2.5E-5")
        send(ser, f":SOUR:VOLT {TEST_VOLTAGE}")

        print("Programmed voltage:", query(ser, ":SOUR:VOLT?"))
        print("Current limit:", query(ser, ":SOUR:VOLT:ILIM?"))

        input("\nPress ENTER to enable +0.100 V: ")

        send(ser, ":SOUR:VOLT:STAT ON", delay=1)

        state = query(ser, ":SOUR:VOLT:STAT?")
        print("Output state:", state)

        if state != "1":
            raise RuntimeError("Output did not turn ON.")

        print("\nMEASURE THE VOLTAGE AT THE BNC CONNECTOR")
        print("Expected: approximately +0.100 V")
        input("\nPress ENTER after recording your multimeter reading: ")

    except Exception as error:
        print("\nERROR:", error)

    finally:
        if ser is not None and ser.is_open:
            print("\nTurning source OFF...")
            try:
                send(ser, ":SOUR:VOLT:STAT OFF")
                send(ser, ":SOUR:VOLT 0")
                print("Output state:", query(ser, ":SOUR:VOLT:STAT?"))
                print("Source voltage:", query(ser, ":SOUR:VOLT?"))
            except Exception as error:
                print("Shutdown warning:", error)

            ser.close()


if __name__ == "__main__":
    main()
