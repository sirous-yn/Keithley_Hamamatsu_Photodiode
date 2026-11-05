import serial.tools.list_ports as port_list
import serial, sys
import numpy as np
import time
from led_controls import LED
import argparse

class Motor():

    def __init__(self, PORT:str = None):

        if PORT == None:
            print("Provide path to motor's port.")
            return

        self.motor = serial.Serial(PORT, 9600) 
        self.motor.write(b"?R\r")
        print(self.motor.readline().decode('ascii', errors='ignore').strip())
        return
        
    def change_pos(self, axis, direction, step, wait:float = None):
        command_string = f"{axis}{direction}{step}\r".encode()
        self.motor.write(command_string)
        if wait != None: 
            time.sleep(wait)
        return self.motor.readline().decode('ascii', errors='ignore').strip()

    def prepare_steps(self, initial_theta, final_theta, M, deg_per_step, endpoint=False):
        interval = M*deg_per_step
        initial_theta = initial_theta/deg_per_step
        final_theta = final_theta/deg_per_step
        if endpoint:
            return np.arange(initial_theta, final_theta + interval, interval, dtype="int")
        return np.arange(initial_theta, final_theta, interval, dtype="int")

    def close(self):
            """Manually close the serial port."""
            if hasattr(self, 'motor') and self.motor.is_open:
                self.motor.close()
                # print("Serial port closed.")

    def __del__(self):
        """Destructor to ensure port is closed when object is destroyed."""
        self.close()