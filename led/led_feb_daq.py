import serial
import time, sys
import serial.tools.list_ports
from rich.console import Console
from rich.table import Table
from rich.live import Live
import argparse
from keithley_controls import Keithley
from led_controls import LED
from motor_controls import Motor
from port_controls import Manager
import numpy as np


def create_loop_table(led_channel, x_angle, y_angle, current, i, j, k, counter, total):
    """Return a Rich Table displaying the current angles, measurement, and progress."""

    table = Table()
    table.add_column("Step",          justify="right")
    table.add_column("CH",            justify="right", style="blue")
    table.add_column("X Angle (deg)", justify="right", style="magenta")
    table.add_column("Y Angle (deg)", justify="right", style="cyan")
    table.add_column("Measurement #", justify="right", style="green")
    table.add_column("Current",       justify="right")
    table.add_column("Progress",      justify="left",  style="yellow", no_wrap = True, width = 10)

    percent = counter / total
    progress_text = f"{percent*100:.1f}%"

    table.add_row(
        f"{i}-{j}-{k}",
        f"{led_channel}",
        f"{x_angle:.2f}",
        f"{y_angle:.2f}",
        str(k+1),
        f"{current:e}",
        progress_text
    )
    return table
    

def loop02(led, keithley, motor, channels, run_number):
    
    '''Debugging polar-angle rotation, X axis'''

    time.sleep(1)
    
    deg_per_step = 40/2000 
    # x_steps = motor.prepare_steps(0, 360, 100000, deg_per_step, endpoint=True)
    x_steps = motor.prepare_steps(0, 360, 25000, deg_per_step, endpoint=True)
    x_angles = x_steps*deg_per_step

    print(x_steps)
    print(x_angles)

    total_step_i = 0
    angle = 0
    for i in range(0, len(x_steps)-1):
        step_i = x_steps[i+1] - x_steps[i]
        if i > 0:
            angle += step_i*deg_per_step
            motor.change_pos('X', '+', str(step_i), wait=1.2)
            print("change motor")
            time.sleep(2)
        print(angle)
        print("take data")
    motor.change_pos('X', '-', str(x_steps[-1]-x_steps[1]))
    

def loop01(led, keithley, motor, channels, run_number):

    console = Console()
    console.print("\n")
    console.rule("[bold cyan]📈 Starting DAQ Loop 📈")

    ### Determine steps for motor
    deg_per_step = 40/2000 
    x_steps = motor.prepare_steps(0, 360, 100000, deg_per_step, endpoint=True)
    y_steps = motor.prepare_steps(-90, 90, 25000, deg_per_step, endpoint=True )
    # x_steps = motor.prepare_steps(0, 360, 25000, deg_per_step, endpoint=True)
    # y_steps = motor.prepare_steps(-90, 90, 12500/2, deg_per_step, endpoint=True )
    x_angles = x_steps*deg_per_step
    y_angles = y_steps*deg_per_step


    ### TAKE BASELINE READINGS
    baseline_N = 10
    baseline = np.zeros((baseline_N))
    for l in range(baseline_N):
        current = keithley.measure(wait=1)
        baseline[l] = float(current) 
    np.savez(f'./data/pd_run_{run_number:04d}_baseline.npz', baseline = baseline, allow_pickle = True)
    # print(baseline)
    # sys.exit()

    ### N measurements per position
    N = 2
    charge = np.zeros((len(x_steps), len(y_steps), N))
    total = len(x_steps)*len(y_steps)*N
    counter = 0

    ## FIX Y STEPS AND SET TO INITIAL POSITION
    # print("Rotating Y to initial position.")
    y_fixed = y_steps - y_steps[0]
    first_step = abs(y_steps[0])
    polarity   = '+' if y_steps[0] >= 0 else '-'
    opposite_to_initial = '-' if y_steps[0] >= 0 else '+'
    time.sleep(1)
    motor.change_pos('Y', polarity, str(first_step))
    
    ## TURN LED ON AND TAKE DATA
    for led_channel in channels:
        led.turn_on(led_channel, rate = 3)
        time.sleep(3)

        with Live(create_loop_table(led_channel, 0,0,0,0,0,0,0,total), refresh_per_second=4) as live:

            ## CHANGE X AXIS (POLAR)
            for i in range(0, len(x_steps)):
                if i > 0:
                    step_i = x_steps[i] - x_steps[i-1]
                    motor.change_pos('X', '+', str(step_i), wait=1.)

                # CHANGE Y AXIS (AZIMUTHAL)
                for j in range(0, len(y_steps)):

                    if j > 0:
                        step_j = y_steps[j] - y_steps[j-1]
                        motor.change_pos('Y', '+', str(step_j), wait=1.)
                                                
                    # TAKE MEASUREMENTS
                    for k in range(N):
                        current = keithley.measure(wait=1)
                        charge[i,j,k] = float(current)
                        counter += 1
                        live.update(create_loop_table(led_channel, x_angles[i], y_angles[j], float(current), i, j, k, counter, total))

                ## SAVE TEMPORARY DATA
                np.savez(f'./data/pd_run_{run_number:04d}_CH{led_channel:02d}_temp.npz', charge = charge, x_angles = x_angles, y_angles = y_angles, x_steps = x_steps, y_steps = y_steps, allow_pickle = True)
                motor.change_pos('Y', '-', str(abs(y_fixed[-1])) )

        np.savez(f'./data/pd_run_{run_number:04d}_CH{led_channel:02d}.npz', charge = charge, x_angles = x_angles, y_angles = y_angles, x_steps = x_steps, y_steps = y_steps, allow_pickle = True)
        led.power_off()
        motor.change_pos('X', '-', str(x_steps[-1]-x_steps[1]))

    time.sleep(1)
    motor.change_pos('Y', opposite_to_initial, str(first_step))

def loop03(led, keithley, motor, channels, run_number):

    pass
    # led.turn_on('3', rate = 3)

    # reading = keithley.measure(wait=1)
    # print(reading)

def main():

    # CLEAR SCREEN
    console = Console()
    console.clear()
    
    # PARSE ARGUMENTS AND INITIALIZE INSTRUMENTS
    run = Manager()
    args = run.parse()
    led, keithley, motor = run.initialize_devices()
    
    # ACQUIRE DATA
    loop01(led, keithley, motor, args.channel, args.run_number)
    
    # TEST LOOPS
    # loop02(led, keithley, motor, args.channel, args.run_number)

    # END RUN BY CLOSING DEVICE CONNECTIONS
    run.close_devices()

    
if __name__ == '__main__':
    main()
