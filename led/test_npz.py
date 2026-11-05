import numpy as np 
import sys

data = np.load(sys.argv[1])

print(data.keys())
for file in data.keys():
    print(f'{file = } :', f'{data[file] = }')