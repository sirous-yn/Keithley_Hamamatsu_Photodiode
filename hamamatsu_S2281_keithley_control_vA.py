import serial
import time
import sys
import serial.tools.list_ports
from rich.console import Console
from rich.table import Table


class Keithley:

    def __init__(self, PORT: str = None) -> None:
        if PORT is None:
            print("Provide path to Keithley's port.")
            return

        self.port = PORT

        self.ser = serial.Serial(
            port=self.port,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=3
        )

        time.sleep(0.5)

    def idn(self) -> str:
        idn = self.query("*IDN?")
        print(f"{idn}")
        return idn

    def send(self, cmd: str, delay: float = 0.1) -> None:
        """Send an SCPI command terminated with newline."""
        self.ser.write((cmd + '\n').encode('ascii'))
        time.sleep(delay)
        return None

    def query(self, cmd: str, delay: float = 0.1) -> str:
        """Send a query and return the response string."""
        self.send(cmd, delay)
        return self.ser.readline().decode('ascii', errors='ignore').strip()

    def setup(self, wait: float = None, relative: bool = None) -> None:

        # --- Initialization Sequence ---
        self.send("*RST")
        self.send("*CLS")
        self.send(":FUNC 'CURR'")

        # --- Zero Correction Sequence ---
        self.send(":SYST:ZCH ON")
        time.sleep(4)

        self.send(":CURR:RANG 2E-9")
        time.sleep(1)

        # self.send(":SYST:ZCOR:ACQ")
        self.send(":SYST:ZCOR ON")
        time.sleep(1)

        self.send(":SYST:ZCH OFF")
        time.sleep(1)

        # --- Measurement Configuration ---
        self.send(":CURR:NPLC 10")
        time.sleep(1)

        self.send(":CURR:AVER:STAT OFF")
        time.sleep(1)

        self.send(":CURR:RANG:AUTO OFF")
        time.sleep(1)

        self.send(":FORM:ELEM READ")
        self.send(":SYST:AZER ON")
        time.sleep(1)

        if wait is not None:
            time.sleep(wait)

        return

    # ---------------------------------------------------------
    # Photodiode bias control
    # ---------------------------------------------------------

    def enable_pd_bias(
        self,
        voltage: float = 0.010,
        current_limit: float = 25e-6
    ) -> None:
        """
        Apply the photodiode bias using the Keithley 6487 voltage source.

        Default settings:
            Bias voltage: 10 mV
            Current limit: 25 uA
        """

        print("\nConfiguring photodiode bias...")

        # Ensure the source is OFF before configuring it.
        self.send(":SOUR:VOLT:STAT OFF")
        self.send(":SOUR:VOLT 0")

        # Configure voltage source.
        self.send(":SOUR:VOLT:RANG 10")
        self.send(f":SOUR:VOLT:ILIM {current_limit}")
        self.send(f":SOUR:VOLT {voltage}")

        # Enable the voltage source.
        self.send(":SOUR:VOLT:STAT ON")

        time.sleep(2)

        print(f"Photodiode bias enabled: {voltage * 1000:.2f} mV")
        print(f"Source current limit: {current_limit * 1e6:.2f} uA")

    def disable_pd_bias(self) -> None:
        """Set photodiode bias to zero and disable the source."""

        try:
            self.send(":SOUR:VOLT 0")
            self.send(":SOUR:VOLT:STAT OFF")
            print("Photodiode bias disabled.")

        except Exception as error:
            print(f"Could not disable photodiode bias: {error}")

    # ---------------------------------------------------------
    # Current measurement
    # ---------------------------------------------------------

    def measure(self, wait: float = 0.2):

        self.send(":INIT")
        time.sleep(wait)

        reading = self.query(":FETCH?")

        return reading

    def close(self):

        try:
            # Safety: turn off the photodiode voltage source.
            self.disable_pd_bias()

        finally:
            self.ser.close()

        return
