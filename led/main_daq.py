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
    

def loop03(led, keithley, motor, channels, run_number):

    ### Determine steps for motor
    deg_per_step = 40/2000 
    
    # For controller tests
    x_steps = motor.prepare_steps(0, 180, 6*12500, deg_per_step, endpoint=True)
    y_steps = motor.prepare_steps(0, 180, 6*12500, deg_per_step, endpoint=True)
    x_angles = x_steps*deg_per_step
    y_angles = y_steps*deg_per_step

    ### N measurements per position
    N = 4
    charge = np.zeros((len(x_steps), len(y_steps), N))
    total = len(x_steps)*len(y_steps)*N
    counter = 0

    ## FIX Y STEPS AND SET TO INITIAL POSITION
    # print("Rotating Y to initial position.")
    anticlockwise = '-'
    clockwise = '+'

    # motor.change_pos('X', clockwise, str(int(10/deg_per_step)))

    # 1. Move Y 90deg anticlockwise
    # 2. Move X step-by-step clockwise
    # 3. Move X all anticlockwise
    # 4. Move Y one step clockwise.

    for i in range(0, len(x_steps)):
        if i > 0: 
            step_i = x_steps[i] - x_steps[i-1]
            motor.change_pos('X', '+', str(step_i), wait=1.)

    
    # for i in range(0, len(x_steps)):
    #     if i > 0:
    #         step_i = x_steps[i] - x_steps[i-1]
    #         motor.change_pos('X', '+', str(step_i), wait=1.)

    # Change first position to -90.
    # first_step = 90./deg_per_step
    # first_step = 4500
    # motor.change_pos('Y', anticlockwise, str(first_step))

    # time.sleep(2)
    # motor.change_pos('Y', clockwise, str(first_step))

    return

    for i in range(0, len(x_steps)):
        if i > 0:
            step_i = x_steps[i] - x_steps[i-1]
            motor.change_pos('X', '+', str(step_i), wait=1.)

        # CHANGE Y AXIS (AZIMUTHAL)
        for j in range(0, len(y_steps)):

            if j > 0:
                step_j = y_steps[j] - y_steps[j-1]
                motor.change_pos('Y', '+', str(step_j), wait=3.)

        motor.change_pos('X', '-', str(x_steps[-1]-x_steps[1]))

    time.sleep(1)
    motor.change_pos('Y', opposite_to_initial, str(first_step))

def loop02(led, keithley, motor, channels, run_number):
    
    '''Debugging polar-angle rotation, X axis'''

    time.sleep(1)
    
    deg_per_step = 40/2000 
    # x_steps = motor.prepare_steps(0, 360, 100000, deg_per_step, endpoint=True)
    x_steps = motor.prepare_steps(0, 360, 25000, deg_per_step, endpoint=True)
    x_angles = x_steps*deg_per_step

    y_steps = motor.prepare_steps(-90, 90, 12500, deg_per_step, endpoint=True )

    print(x_steps)
    print(x_angles)

    y_fixed = y_steps - y_steps[0]
    first_step = abs(y_steps[0])
    # polarity   = '+' if y_steps[0] >= 0 else '-'
    # opposite_to_initial = '-' if y_steps[0] >= 0 else '+'
    polarity = '-'
    opposite_to_initial = '+' if polarity == '-' else '+'
    time.sleep(1)
    motor.change_pos('Y', polarity, str(first_step))

    total_step_i = 0
    angle = 0
    for i in range(0, len(x_steps)-1):
        step_i = x_steps[i+1] - x_steps[i]
        if i > 0:
            angle += step_i*deg_per_step
            motor.change_pos('X', '+', str(step_i), wait=1.2)
            print("change motor")
            # time.sleep(2)
        print(angle)
        print("take data")
    motor.change_pos('X', '-', str(x_steps[-1]-x_steps[1]))

    
    motor.change_pos('Y', opposite_to_initial, str(first_step))

def loop01(led, keithley, motor, channels, run_number):

    console = Console()
    console.print("\n")
    console.rule("[bold cyan]📈 Starting DAQ Loop 📈")

    ### Determine steps for motor
    deg_per_step = 40/2000 

    # For DAQ
    x_steps = motor.prepare_steps(0, 360, 12500, deg_per_step, endpoint=True)
    y_steps = motor.prepare_steps(-90, 90, 12500, deg_per_step, endpoint=True )
    
    # For controller tests
    # x_steps = motor.prepare_steps(0, 360, 100000, deg_per_step, endpoint=True)
    # y_steps = motor.prepare_steps(-90, 90, 50000, deg_per_step, endpoint=True )
    x_angles = x_steps*deg_per_step
    y_angles = y_steps*deg_per_step

    # print(x_angles, y_angles, len(x_angles)*len(y_angles)*2100)
    # sys.exit()

    ### TAKE BASELINE READINGS
    baseline_N = 10
    baseline = np.zeros((baseline_N))
    for l in range(baseline_N):
        current = keithley.measure(wait=1)
        baseline[l] = float(current) 
    np.savez(f'./data/pd_run_{run_number:04d}_baseline.npz', baseline = baseline, allow_pickle = True)

    ### N measurements per position
    N = 4
    charge = np.zeros((len(x_steps), len(y_steps), N))
    total = len(x_steps)*len(y_steps)*N
    counter = 0

    ## FIX Y STEPS AND SET TO INITIAL POSITION
    # print("Rotating Y to initial position.")
    y_fixed = y_steps - y_steps[0]
    first_step = abs(y_steps[0])
    # polarity   = '+' if y_steps[0] >= 0 else '-'
    # opposite_to_initial = '-' if y_steps[0] >= 0 else '+'
    polarity = '-'
    opposite_to_initial = '+' if polarity == '-' else '+'
    time.sleep(1)
    motor.change_pos('Y', polarity, str(first_step))

    print(f'{polarity = }')
    # sys.exit()
    
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
                        motor.change_pos('Y', '+', str(step_j), wait=3.)
                                                
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

def loop04(led, keithley, motor, channels, run_number):

    ### TAKE BASELINE READINGS
    baseline_N = 10
    baseline = np.zeros((baseline_N))
    for l in range(baseline_N):
        current = keithley.measure(wait=1)
        baseline[l] = float(current) 
    np.savez(f'./data/pd_run_{run_number:04d}_baseline.npz', baseline = baseline, allow_pickle = True)
    print("Baseline mean:", np.mean(baseline))

    ### DEFINE ANGLES
    deg_per_step = 40/2000
    x_steps = motor.prepare_steps(0, 180, 12500, deg_per_step, endpoint=True)
    y_steps = motor.prepare_steps(0, 180, 12500, deg_per_step, endpoint=True )
    x_angles = x_steps*deg_per_step
    y_angles = y_steps*deg_per_step

    ### POLARITY DEFINITIONS
    anticlockwise = '-'
    clockwise = '+'

    if len(channels) > 1:
        print("Choose a single LED channel to take data.")
        return
    led_channel = str(channels[0])
    led.turn_on(led_channel, rate = 3)
    time.sleep(3)   

    ### MOVE LED-FEB TO INITIAL POSITION
    # Initial position (90deg on polar direction)
    # Move along the polar direction from 90deg to 0deg
    first_step = 90/deg_per_step
    motor.change_pos('Y', anticlockwise, str(int(first_step)), wait=3.)

    ### PERFORM READINGS
    N = 4
    charge = np.zeros((len(y_steps), len(x_steps), N))
    for j in range(len(y_steps)):

        for k in range(N):
            current = keithley.measure(wait=1)
            charge[j, 0, k] = float(current)
            print('Row (i, j):', 0, j, '. Measuremnt:', k, float(current))

        accumulated_steps = 0
        for i in range(len(x_steps) - 1):
            i_step = np.abs(x_steps[i+1] - x_steps[i])
            if i_step > 0:
                motor.change_pos('X', clockwise, str(int(i_step)), wait=1.)
                accumulated_steps += int(i_step)

                for k in range(N):
                    current = keithley.measure(wait=1)
                    charge[j, i+1, k] = float(current)
                    print('Row (i, j):', i, j, '. Measuremnt:', k, float(current))

        motor.change_pos('X', anticlockwise, str(int(accumulated_steps)), wait=1.)
        np.savez(f'./data/pd_run_{run_number:04d}_CH{led_channel}_temp.npz', charge = charge, x_angles = x_angles, y_angles = y_angles, x_steps = x_steps, y_steps = y_steps, allow_pickle = True)

        if j < len(y_steps) - 1:
            j_step = np.abs(y_steps[j+1] - y_steps[j])
            if j_step > 0:
                motor.change_pos('Y', clockwise, str(int(j_step)), wait=3.)

    ### SAVE FINAL DATA
    np.savez(f'./data/pd_run_{run_number:04d}_CH{led_channel}.npz', charge = charge, x_angles = x_angles, y_angles = y_angles, x_steps = x_steps, y_steps = y_steps, allow_pickle = True)
    
    ### RETURN LED-FEB TO START
    # Move along polar direction from 180deg to 90deg
    motor.change_pos('Y', anticlockwise, str(int(first_step)), wait=1.)

    return

def loop05(led, keithley, channels):

    print("LED OFF")
    baseline_N = 4
    baseline = np.zeros((baseline_N))
    for l in range(baseline_N):
        current = keithley.measure(wait=1)
        baseline[l] = float(current) 
        print(baseline[l])
    # np.savez(f'./data/pd_run_{run_number:04d}_baseline.npz', baseline = baseline, allow_pickle = True)
    # print("Baseline mean:", np.mean(baseline))

    print("LED ON")
    if len(channels) > 1:
        print("Choose a single LED channel to take data.")
        return
    led_channel = str(channels[0])
    led.turn_on(led_channel, rate = 3)
    time.sleep(3)   
    
    for l in range(baseline_N):
        current = keithley.measure(wait=1)
        baseline[l] = float(current) 
        print(baseline[l])

def loop06(led, keithley, motor, channels, run_number):

    console = Console()
    console.print("\n")
    console.rule("[bold cyan]📈 Starting DAQ Loop 📈")

    ### DEFINE ANGLES
    deg_per_step = 40/2000
    x_steps = motor.prepare_steps(0, 360, 12500, deg_per_step, endpoint=True)
    y_steps = motor.prepare_steps(0, 180, 12500, deg_per_step, endpoint=True )
    x_angles = x_steps*deg_per_step
    y_angles = y_steps*deg_per_step

    # print(x_angles, y_angles, len(x_angles)*len(y_angles)*2100)
    # sys.exit()

    ### TAKE BASELINE READINGS
    baseline_N = 10
    baseline = np.zeros((baseline_N))
    for l in range(baseline_N):
        current = keithley.measure(wait=1)
        baseline[l] = float(current) 
    np.savez(f'./data/pd_run_{run_number:04d}_baseline.npz', baseline = baseline, allow_pickle = True)

    ### N measurements per position
    N = 1
    charge = np.zeros((len(x_steps), len(y_steps), N))
    total = len(x_steps)*len(y_steps)*N
    counter = 0

    ### POLARITY DEFINITIONS
    anticlockwise = '-'
    clockwise = '+'

    move_5 = 15/deg_per_step
    motor.change_pos('X', clockwise, str(int(move_5)), wait=1.)
    motor.change_pos('X', clockwise, str(int(move_5)), wait=1.)
    motor.change_pos('X', anticlockwise, str(int(move_5)), wait=1.)
    motor.change_pos('X', anticlockwise, str(int(move_5)), wait=1.)
    motor.change_pos('X', anticlockwise, str(int(move_5)), wait=1.)
    motor.change_pos('X', anticlockwise, str(int(move_5)), wait=1.)
    motor.change_pos('X', clockwise, str(int(move_5)), wait=1.)
    motor.change_pos('X', clockwise, str(int(move_5)), wait=1.)

    ### MOVE LED-FEB TO INITIAL POSITION
    # Initial position (90deg on polar direction)
    # Move along the polar direction from 90deg to 0deg
    first_step = 90/deg_per_step
    motor.change_pos('Y', anticlockwise, str(int(first_step)), wait=3.)
    # motor.change_pos('Y', clockwise, str(int(first_step)), wait=3.)
    # return

    # Time to wait after moving motor
    wait_j = 3
    wait_i = 1

    ## TURN LED ON AND TAKE DATA
    for led_channel in channels:
        led.turn_on(led_channel, rate = 3)
        time.sleep(3)

        with Live(create_loop_table(led_channel, 0,0,0,0,0,0,0,total), refresh_per_second=4) as live:

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
                        motor.change_pos('Y', clockwise, str(step_j), wait=wait_j)
                                                
                    # TAKE MEASUREMENTS
                    for k in range(N):
                        current = keithley.measure(wait=1)
                        charge[i,j,k] = float(current)
                        counter += 1
                        live.update(create_loop_table(led_channel, x_angles[i], y_angles[j], float(current), i, j, k, counter, total))

                ## SAVE TEMPORARY DATA
                np.savez(f'./data/pd_run_{run_number:04d}_CH{led_channel:02d}_temp.npz', charge = charge, x_angles = x_angles, y_angles = y_angles, x_steps = x_steps, y_steps = y_steps, allow_pickle = True)
                motor.change_pos('Y', anticlockwise, str(int(accumulated_steps)))

        np.savez(f'./data/pd_run_{run_number:04d}_CH{led_channel:02d}.npz', charge = charge, x_angles = x_angles, y_angles = y_angles, x_steps = x_steps, y_steps = y_steps, allow_pickle = True)
        led.power_off()
        motor.change_pos('X', clockwise, str(int(accumulated_steps_i)))

    ### RETURN LED-FEB TO START
    # Move along polar direction from 180deg to 90deg
    motor.change_pos('Y', clockwise, str(int(first_step)), wait=1.)

def loop07(led, keithley, motor, channels, run_number):

    console = Console()
    console.print("\n")
    console.rule("[bold cyan]📈 Starting DAQ Loop 📈")

    for led_channel in channels:
        led.turn_on(led_channel, rate = 3)
        time.sleep(3)

    baseline_N = 10
    for l in range(baseline_N):
        current = keithley.measure(wait=1)
        print(l, current)

    # np.savez(f'./data/pd_run_{run_number:04d}_baseline.npz', baseline = baseline, allow_pickle = True)
    return

def main():

    # CLEAR SCREEN
    console = Console()
    console.clear()
    
    # PARSE ARGUMENTS AND INITIALIZE INSTRUMENTS
    run = Manager()
    args = run.parse()
    led, keithley, motor = run.initialize_devices()
    
    # ACQUIRE DATA
    print("Initialization complete. Waiting 15 seconds...")
    # time.sleep(15)
    # loop04(led, keithley, motor, args.channel, args.run_number)
    # loop05(led, keithley, args.channel)
    
   
    # Use loop06 for NXT-85 tests
    loop06(led, keithley, motor, args.channel, args.run_number)
    # loop07(led, keithley, motor, args.channel, args.run_number)

    # END RUN BY CLOSING DEVICE CONNECTIONS
    run.close_devices()

    
if __name__ == '__main__':
    main()
