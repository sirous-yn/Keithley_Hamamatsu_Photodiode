import numpy as np

class Motor():

    def __init__(self, PORT:str = None):

        if PORT == None:
            print("Provide path to motor's port.")
            return

        # self.motor = serial.Serial(PORT, 9600) 
        # self.motor.write(b"?R\r")
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

motor = Motor(PORT="test")

deg_per_step = 40/2000 
# x_steps = motor.prepare_steps(0, 360, 100000, deg_per_step, endpoint=True)
# y_steps = motor.prepare_steps(-90, 90, 25000, deg_per_step, endpoint=True )
x_steps = motor.prepare_steps(0, 360, 12500, deg_per_step, endpoint=True)
# y_steps = motor.prepare_steps(-90, 90, 12500/2, deg_per_step, endpoint=True )
x_angles = x_steps*deg_per_step
# y_angles = y_steps*deg_per_step

print(x_steps)
print(x_angles)

# print(len(x_angles), x_angles)
# print(len(y_angles), y_angles)