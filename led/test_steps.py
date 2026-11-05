import pyvisa as visa
import serial.tools.list_ports as port_list
import serial, sys
import numpy as np
import time

def prepare_steps(initial_theta, final_theta, M, deg_per_step, endpoint=False):
    interval = M*deg_per_step
    initial_theta = initial_theta/deg_per_step
    final_theta = final_theta/deg_per_step
    if endpoint:
        return np.arange(initial_theta, final_theta + interval, interval, dtype="int")
    return np.arange(initial_theta, final_theta, interval, dtype="int")

def change_pos(motor, axis, direction, step, wait = 0.):
    command_string = f"{axis}{direction}{step}\r".encode()
    motor.write(command_string)
    if wait > 0.:
        time.sleep(wait)
    return motor.readline().decode()

def query(motor, command_string):
    motor.write(command_string)
    return motor.readline().decode()

# Find motor
# print("Looking for motor...")
# ports = serial.tools.list_ports.comports()
# for port in ports:
#     print(port)
#     if 'FT232R' in port.description:
#         print("Found FT232R")
#         PORT_MOTOR = port.device
#     else:
#         print("Motor not found.")
#         sys.exit()

# PORT_MOTOR = '/dev/ttyUSB0'

# print("Connecting to motor...")
# motor = serial.Serial(PORT_MOTOR)
# motor.write(b"?R\r")
# print(motor.readline().decode())

# sys.exit()

#### USE THIS ONE TO BRING FROM -90 deg to 0 deg on Y
# time.sleep(10)
# change_pos(motor, 'Y', '+', 4500)

deg_per_step = 40/2000
x_steps = prepare_steps(0, 360, 12500, deg_per_step, endpoint=True)
x_angles = x_steps*deg_per_step
print(x_angles)

# ret = query(motor, b'?X\r')
# print(ret)

# for i in range(0, len(x_angles)):
#     if i > 0:
#         step_i = x_steps[i] - x_steps[i-1]
#         ret = change_pos(motor, 'X', '+', str(step_i), wait=1.5)
#         ret = query(motor, b'?R\r')
#         print(ret)


# y_steps = prepare_steps(-90, 90, 100000, deg_per_step, endpoint=True )
# y_angles = y_steps*deg_per_step
# print(y_angles) 
