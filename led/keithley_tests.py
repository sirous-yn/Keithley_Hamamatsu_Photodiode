from keithley_controls import Keithley
import serial.tools.list_ports

ports = serial.tools.list_ports.comports()
for port in ports:
    if 'FT232R' in port.description:
        PORT_MOTOR = port.device
    if 'TTL-234X-3V3-2MM' in port.description:
        PORT_LED = port.device
    if 'USB Serial Converter' in port.description:
        PORT_KEITHLEY = port.device

keithley = Keithley(PORT = PORT_KEITHLEY)
keithley.setup(wait=2, relative = True)