import time 
import os, sys
import numpy as np

import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt

from math import *
import argparse

# --- ARGUMENT PARSING ---
parser = argparse.ArgumentParser(description='Process quality check for specific runs.')
parser.add_argument('--run', nargs='+', required=True, help='List of run numbers (e.g., 14 15 16)')
args = parser.parse_args()

# This replaces your hardcoded list. 
# It takes the input from the terminal and stores it in 'runs'
runs = args.run

# Dictionaries to contain angle and measurement information
readings = {}
x = {}
y = {}

# Load up data
for run in runs:

    data = np.load(f'./data/pd_run_00{run}_CH04.npz')
    x[run] = data['x_angles']
    y[run] = data['y_angles']

    # Calculate mean of measurements for every angle
    measurements = np.zeros([len(y[run]), len(x[run])], dtype='float')
    for i in range(len(x[run])):
        baseline = ( np.mean(data['charge'][i][0]) + np.mean(data['charge'][i][-1]) )*0.5
        for j in range(len(y[run])):
            measurements[j][i] = ( np.mean(data['charge'][i][j]) - baseline )*1.e12

    readings[run] = measurements

# Checking shape/ size of arrays
print("Checking dimensionality of arrays.")
for i in runs:
    print(f"Run: {i}. readings: {readings[i].shape}. x: {x[i].shape}. y: {y[i].shape}.")

# Angle span
# x goes from 0 to 360
# y goes from -90 to 90

# Pick a run for individual plots
for run in runs:

    fig1, ax = plt.subplots(1, 1, figsize=(8, 4))
    im1 = ax.imshow(readings[run],cmap='YlGnBu', extent=[x[run][0], x[run][-1], y[run][0], y[run][-1]],)
    fig1.colorbar(im1, ax = ax)
    ax.set_xlabel('Degree')
    ax.set_ylabel('Degree')
    plt.tight_layout()
    plt.savefig(f'./plots/images_{run}_all.png')
    # plt.show()
    # plt.close()

    # sys.exit()

    fig2, ax = plt.subplots(1, 1, figsize=(8, 4))

    N_min = 10 
    N_max = 10
    x_min = x[run][N_min]
    x_max = x[run][len(x[run])-N_max - 1]

    ax.set_title(f'{x_min:3.1f} to {x_max:3.1f}')
    for i in range(N_min, len(x[run])-N_max):
        ax.plot(y[run],readings[run][:,i])
    ax.set_xlabel("Zenith angle (deg.)")
    plt.savefig(f'./plots/images_{run}_azimuthal.png')
    plt.show()
    # plt.close()


