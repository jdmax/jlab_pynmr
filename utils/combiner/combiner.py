'''Combines multiple eventfile signals into one file, averaging weighted by number of sweeps. J. Maxwell 7/2022

    Needs arguments -d for the directory of the eventfiles to search, -b for beginning datetime, -e for ending datetime. WIll default to combining the polysub signal, unless you pass -r to ask for the raw. Datetime format is the same as the screenshot name.
'''

import sys
import os
import json
import getopt
from datetime import datetime
from dateutil.parser import parse
import glob
import re
import pytz
import numpy as np


type = 'fitsub'  
dir = ''
utc=pytz.UTC

# Get comannd line options
try:
    opts, args = getopt.getopt(sys.argv[1:],"hrd:b:e:")
except getopt.GetoptError:
    print('Usage: combiner.py -d <directory> -b "<begin time eg. 2022-07-18 19:41:16>" -e "<end time>"')
    sys.exit(2)      
for opt, arg in opts:
    if opt in ['-h',]:
        print('Usage: combiner.py -d <directory> -b "<begin time eg. 2022-07-18 19:41:16>" -e "<end time>"')
        sys.exit()
    elif opt in ("-d"):
        dir = arg  
    elif opt in ("-b"):
        begin_dt = parse(arg).replace(tzinfo=utc)
    elif opt in ("-e"):
        end_dt = parse(arg).replace(tzinfo=utc)   
    elif opt in ("-r"):
        type = 'raw'   
        
#print(begin_dt, end_dt,  begin_dt < end_dt)     

# Get files with data in the range specified
selected = []
files = glob.glob(dir + '/20*.txt')

for file in files:
    head, tail = os.path.split(file)
    name = tail.split(".")[0]
    start_str, end_str = name.split("__")
    
    start = datetime.strptime(start_str, "%Y-%m-%d_%H-%M-%S").replace(tzinfo=utc)
    stop = datetime.strptime(end_str, "%Y-%m-%d_%H-%M-%S").replace(tzinfo=utc)
    if begin_dt < stop and start < end_dt:
        selected.append(file)    

# Go though files to selected data in the range specified and average together sweeps

averaged = np.zeros(512)
number = 0

for name in selected:
    with open(name, 'r') as file:
        for line in file:
            json_dict = json.loads(line.rstrip('\n|\r'))
            data = np.array(json_dict[type])
            freq_list = json_dict['freq_list']
            num_sweep = json_dict['sweeps']
            time = parse(json_dict['stop_time'])
            if begin_dt < time  and time < end_dt:               
                averaged = (averaged*number + data*num_sweep)/(number + num_sweep)
                number = number + num_sweep
                
print("Total sweeps combined:", number)

begin = begin_dt.strftime("%Y-%m-%d_%H-%M-%S")
end = end_dt.strftime("%Y-%m-%d_%H-%M-%S")

np.savetxt(f"combined_{begin}_{end}.txt", averaged, delimiter="\n")

print("Saved to", f"combined_{begin}_{end}.txt")
#print("Combined sweep:", averaged)                
        
