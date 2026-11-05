from dataclasses import dataclass
from time import sleep
from led_firmware.Python.led_feb import Mach_II

@dataclass 
class LED:

    port:str    | None = '/dev/serial/by-id/usb-FTDI_TTL-234X-3V3-2MM_FT80EFAX-if00-port0'
    feb:Mach_II | None = None

    def __post_init__(self) -> None:
        self.feb  = Mach_II(self.port, print_messages = False)
        sleep(1)

    def turn_on(self, channel:str = "", voltage:float = 15, rate:float = 8) -> None:
        self.feb.select_channel("all")
        self.feb.channel_disable()
        sleep(1)
        self.feb.power_on()
        self.feb.set_bias_voltage(voltage)
        self.feb.set_pulsing_frequency(rate)
        self.feb.set_int_trigger()
        self.feb.pulses_enable()
        self.feb.select_channel(channel)
        self.feb.channel_enable()
        sleep(1)

    def set_voltage(self, channel:str = "", voltage:float = 15) -> None:
        self.feb.select_channel(channel)
        self.feb.set_bias_voltage(voltage)

    def set_frequency(self, channel:str = "", rate:float = 8) -> None:
        self.feb.select_channel(channel)
        self.feb.set_pulsing_frequency(rate)

    def disable(self, channel:str = "") -> None:
        self.feb.select_channel(channel)
        self.feb.channel_disable()

    def power_off(self) -> None:
        self.feb.select_channel("all")
        self.feb.channel_disable()
        sleep(1)
        self.feb.pulses_disable()
        self.feb.power_off()

    def close(self, wait=1) -> None:
        self.feb.power_off()
        sleep(wait)
        self.feb.close()









