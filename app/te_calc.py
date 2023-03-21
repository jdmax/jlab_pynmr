'''J.Maxwell 2020
'''
import sys
import numpy as np
import datetime
import pytz
import json
                
                
class TE():    
    '''Class to perform TE measurements, output results. Ignores error in CC due to error in temp, as the contribution to delta CC from delta t is suppressed by 1/pol^2, and pol is small.
    
    Args:
        species: Nuclear species string, proton or deuteron. Looks for p or d to select which, so flexible on the string provided
        field: field value float in Tesla
        areas: 1-D numpy array with areas
        temps: 1-D numpy array with temps
        
    Attributes:
        field: magnetic field used for calculation
        num: number of points in the measurements
        cc: averaged calibration constant from points
        cc_std: standard deviation of calibation constant from points
        te_pol: averaged polarization during TE
        te_pol_std: standard deviation of polarizations
        temp: averaged temperature during TE
        temp_std: standard deviation of temperatures
        area: averaged area during TE
        area_std: standard deviation of areas
    '''    
    def __init__(self, species, field, areas, temps):
    
        nuc_magtn = 5.05078658e-27   #J/T
        boltz_const = 1.380658e-23   #J/K
        self.areas = areas
        self.temps = temps

        if 'P' in species or 'p' in species:
            self.species = 'Proton'
            magneton =  2.79268    # mu_0
        elif 'D' in species or 'd' in species:
            self.species = 'Deuteron'
            magneton =  0.857387  # mu_0
        else:
            print('Incorrect species')
            sys.exit()
        temps[temps<1E-5] = 1E-9     # replace zero values to avoid divide by zero
        
        self.field = field    
        te_pols = np.tanh(magneton*nuc_magtn*field/boltz_const/temps)
        ccs = te_pols/areas
             
        self.num = len(ccs)
        self.te_pol = np.mean(te_pols)
        self.te_pol_std = np.std(te_pols)
        self.cc = np.mean(ccs)
        self.cc_std = np.std(ccs)
        self.temp = np.mean(temps)
        self.temp_std = np.std(temps)
        self.area = np.mean(areas)  
        self.area_std = np.std(areas) 
        
    def pretty_te(self):
        '''Return formated string short version of TE report'''
        return f"""Material type:  {self.species}                                  Number of Points:  {self.num}
Average Area:  {self.area:.7f} ± {self.area_std:.7f}                 Average Temperature:  {self.temp:.4f} ± {self.temp_std:.4f}
Average Polarization:  {self.te_pol:.5f} ± {self.te_pol_std:.5f}        Average Calibration Constant:  {self.cc:.7f} ± {self.cc_std:.7f}"""

    def print_te(self):
        '''Print long version of TE report to JSON file'''
        now = datetime.datetime.now(tz=pytz.timezone('US/Eastern')).strftime("%Y-%m-%d_%H-%M-%S")
        json_dict = {}
        for key, entry in self.__dict__.items():  
            if isinstance(entry, np.ndarray):       
                json_dict[key] = entry.tolist() 
            else:
                json_dict.update({key:entry})
        with open(f"te/{self.species}-{now}.json", "w") as outfile:
            json.dump(json_dict, outfile, indent = 4) 
        return   
        