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


    # console = Console()
    # console.print("\n")
    # console.rule("[bold cyan]📈 Starting DAQ Loop 📈")

# FOR DAQ:

# print("FOR DAQ:")
# deg_per_step = 40/2000 
# # x_steps = motor.prepare_steps(0, 360, 100000, deg_per_step, endpoint=True)
# x_steps = motor.prepare_steps(0, 180, 12500, deg_per_step, endpoint=True)
# y_steps = motor.prepare_steps(0, 180, 12500, deg_per_step, endpoint=True )
# x_angles = x_steps*deg_per_step
# y_angles = y_steps*deg_per_step

# print('x:', x_steps)
# print('x:', x_angles)
# print('x:', x_angles.shape)

# print('y:', y_steps)
# print('y:', y_angles)
# print('y:', y_angles.shape)

# wait = 0.5
# N = 1
# print("Time estimation:", f"{(wait+N)*len(x_steps)*len(y_steps)/60:4.2f}", "minutes")

# print("\n")
# FOR TESTING
print("FOR TESTING:")
deg_per_step = 40/2000 
x_steps = motor.prepare_steps(0, 360, 36*12500, deg_per_step, endpoint=True)
y_steps = motor.prepare_steps(0, 180, 12*12500, deg_per_step, endpoint=True )
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

# sys.exit()
### POLARITY DEFINITIONS
anticlockwise = '-'
clockwise = '+'

### MOVE LED-FEB TO INITIAL POSITION
# Initial position (90deg on polar direction)
# Move along the polar direction from 90deg to 0deg
first_step = 90/deg_per_step
motor.change_pos('Y', anticlockwise, str(int(first_step)), wait=3.)


## CHANGE X AXIS (POLAR)
accumulated_steps_i = 0
for i in range(0, len(x_steps)):
    if i > 0:
        step_i = x_steps[i] - x_steps[i-1]
        accumulated_steps_i += step_i
        motor.change_pos('X', anticlockwise, str(step_i), wait=1.)

    # CHANGE Y AXIS (AZIMUTHAL)
    accumulated_steps = 0
    for j in range(0, len(y_steps)):

        if j > 0:
            step_j = y_steps[j] - y_steps[j-1]
            accumulated_steps += step_j
            motor.change_pos('Y', clockwise, str(step_j), wait=3.)
                                    
    motor.change_pos('Y', anticlockwise, str(int(accumulated_steps)))

motor.change_pos('X', clockwise, str(int(accumulated_steps_i)))

### RETURN LED-FEB TO START
# Move along polar direction from 180deg to 90deg
motor.change_pos('Y', clockwise, str(int(first_step)), wait=1.)
motor.close()