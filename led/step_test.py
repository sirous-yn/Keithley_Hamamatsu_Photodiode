import numpy as np
import serial, sys
import time

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

motor = Motor(PORT='/dev/ttyUSB1')
time.sleep(4)

# FOR DAQ:

print("FOR DAQ:")
deg_per_step = 40/2000 
# x_steps = motor.prepare_steps(0, 360, 100000, deg_per_step, endpoint=True)
x_steps = motor.prepare_steps(0, 180, 1*12500, deg_per_step, endpoint=True)
y_steps = motor.prepare_steps(0, 180, 2*12500, deg_per_step, endpoint=True )
x_angles = x_steps*deg_per_step
y_angles = y_steps*deg_per_step

print('x:', x_steps)
print('x:', x_angles)
print('x:', x_angles.shape)

print('y:', y_steps)
print('y:', y_angles)
print('y:', y_angles.shape)

wait = 0.5
N = 1
print("Time estimation:", f"{(wait+N)*len(x_steps)*len(y_steps)/60:4.2f}", "minutes")

print("\n")
# FOR TESTING
print("FOR TESTING:")
deg_per_step = 40/2000 
# x_steps = motor.prepare_steps(0, 360, 100000, deg_per_step, endpoint=True)
# x_steps = motor.prepare_steps(0, 180, 6*12500, deg_per_step, endpoint=True)
# y_steps = motor.prepare_steps(0, 180, 6*12500, deg_per_step, endpoint=True )
x_angles = x_steps*deg_per_step
y_angles = y_steps*deg_per_step

print('x:', x_steps)
print('x:', x_angles)
print('x:', x_angles.shape)

print('y:', y_steps)
print('y:', y_angles)
print('y:', y_angles.shape)

print("Time estimation:", f"{(wait+N)*len(x_steps)*len(y_steps)/60:4.2f}", "min")

# sys.exit()

print("First step:")
first_step = -30/deg_per_step

anticlockwise = '-'
clockwise = '+'

# Initial position (90deg on polar direction)
# Move along the polar direction from 90deg to 0deg
motor.change_pos('Y', anticlockwise, str(int(first_step)), wait=1.)

# Use the full range of y_steps to ensure every row is visited
# for j in range(len(y_steps)):

#     # 1. ALWAYS perform the X-axis scan first for the current Y position
#     accumulated_steps = 0
#     for i in range(len(x_steps) - 1):
#         i_step = np.abs(x_steps[i+1] - x_steps[i])
#         if i_step > 0:
#             motor.change_pos('X', clockwise, str(int(i_step)), wait=0.5)
#             accumulated_steps += int(i_step)

#     # 2. Return X to the start of the line
#     motor.change_pos('X', anticlockwise, str(int(accumulated_steps)), wait=0.5)

#     # 3. ONLY move to the next Y position if we aren't on the last row yet
#     if j < len(y_steps) - 1:
#         j_step = np.abs(y_steps[j+1] - y_steps[j])
#         if j_step > 0:
#             motor.change_pos('Y', clockwise, str(int(j_step)), wait=0.5)

# # Move along polar direction from 180deg to 90deg
# motor.change_pos('Y', anticlockwise, str(int(first_step)), wait=1.)

# Close connection and delete object
motor.close()
