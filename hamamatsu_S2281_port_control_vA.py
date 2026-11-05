import serial
import time
import sys
import serial.tools.list_ports

from rich.console import Console
from rich.table import Table
from rich.live import Live

from hamamatsu_S2281_keithley_control_vA import Keithley
from led_controls import LED
from motor_controls import Motor

import argparse


class Manager:

    def __init__(self):

        self.console = Console()

        self.led = None
        self.keithley = None
        self.motor = None

        self.instruments = [
            {"name": "Keithley 6487", "status": "🔍 Waiting"},
            {"name": "LED-FEB", "status": "🔍 Waiting"},
            {"name": "Motor", "status": "🔍 Waiting"},
        ]

    def make_table(self):

        table = Table(show_lines=True)

        table.add_column("Name", style="magenta")
        table.add_column("Status", style="yellow")

        for instr in self.instruments:
            table.add_row(instr["name"], instr["status"])

        return table

    def find_devices(self):

        table = Table(show_lines=True)

        table.add_column("Name", style="magenta")
        table.add_column("Port", style="cyan", no_wrap=True)
        table.add_column("Serial Number", style="white")
        table.add_column("Description", style="green")

        PORT_MOTOR = None
        PORT_LED = None
        PORT_KEITHLEY = None

        ports = serial.tools.list_ports.comports()

        for port in ports:

            if 'FT232R' in port.description:
                PORT_MOTOR = port.device
                table.add_row(
                    "Motor",
                    PORT_MOTOR,
                    str(port.serial_number),
                    port.description
                )

            if 'TTL-234X-3V3-2MM' in port.description:
                PORT_LED = port.device
                table.add_row(
                    "LED",
                    PORT_LED,
                    str(port.serial_number),
                    port.description
                )

            if 'USB Serial Converter' in port.description:
                PORT_KEITHLEY = port.device
                table.add_row(
                    "Picoammeter",
                    PORT_KEITHLEY,
                    str(port.serial_number),
                    port.description
                )

        self.console.print(table)

        missing = []

        if PORT_MOTOR is None:
            missing.append("Motor")

        if PORT_LED is None:
            missing.append("LED")

        if PORT_KEITHLEY is None:
            missing.append("Keithley 6487")

        if missing:
            raise RuntimeError(
                "Could not find the following device(s): "
                + ", ".join(missing)
            )

        return PORT_MOTOR, PORT_LED, PORT_KEITHLEY

    def initialize_devices(self):

        self.console.print("\n")
        self.console.rule("[bold cyan]📡 Looking for Serial Devices 📡")

        PORT_MTR, PORT_LED, PORT_KLY = self.find_devices()

        self.console.print("\n")
        self.console.rule("[bold cyan]🚀 Instrument Initialization 🚀")
        self.console.print()

        with Live(
            self.make_table(),
            refresh_per_second=4,
            console=self.console
        ) as live:

            # -------------------------------------------------
            # KEITHLEY 6487
            # -------------------------------------------------

            self.instruments[0]["status"] = "⚡ Initializing"
            live.update(self.make_table())

            self.keithley = Keithley(PORT=PORT_KLY)

            # Preserve the original current measurement setup.
            self.keithley.setup(wait=2, relative=True)

            # Enable the photodiode bias before baseline readings.
            self.keithley.enable_pd_bias(
                voltage=0.010,
                current_limit=25e-6
            )

            self.instruments[0]["status"] = "✅ Ready"
            live.update(self.make_table())

            # -------------------------------------------------
            # MOTOR
            # -------------------------------------------------

            self.instruments[2]["status"] = "⚡ Initializing"
            live.update(self.make_table())

            self.motor = Motor(PORT=PORT_MTR)

            self.instruments[2]["status"] = "✅ Ready"
            live.update(self.make_table())

            # -------------------------------------------------
            # LED
            # -------------------------------------------------

            self.instruments[1]["status"] = "⚡ Initializing"
            live.update(self.make_table())

            self.led = LED(port=PORT_LED)

            time.sleep(1)
            self.led.power_off()
            time.sleep(1)

            self.instruments[1]["status"] = "✅ Ready"
            live.update(self.make_table())

        return self.led, self.keithley, self.motor

    def close_devices(self):

        self.console.print("\n")
        self.console.rule("[bold cyan]🚨 Closing Serial Connections 🚨")
        self.console.print()

        # Try to close every device even if one cleanup operation fails.
        if self.led is not None:
            try:
                self.led.power_off()
                self.led.close(wait=1)
            except Exception as error:
                print(f"LED shutdown error: {error}")

        if self.motor is not None:
            try:
                self.motor.close()
            except Exception as error:
                print(f"Motor shutdown error: {error}")

        if self.keithley is not None:
            try:
                self.keithley.close()
            except Exception as error:
                print(f"Keithley shutdown error: {error}")

        self.console.rule("[bold cyan]👋 Connections Closed 👋")

    def parse(self):

        parser = argparse.ArgumentParser(
            description="Scan LED-FEB's diffuser output."
        )

        parser.add_argument(
            "--channel",
            "-c",
            type=int,
            choices=[0, 1, 2, 3, 4, 5, 6],
            nargs='+',
            required=True,
            help="Choose one or multiple channels, e.g. --channel 4 5 6"
        )

        parser.add_argument(
            "--run-number",
            "-r",
            type=int,
            required=True,
            help="Positive integer to index data-acquisition run."
        )

        return parser.parse_args()
