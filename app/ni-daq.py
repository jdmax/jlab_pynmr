'''PyNMR, J.Maxwell 2020
NI-DAQmx interface by C. Carlin
'''
import unyt
import nidaqmx
from nidaqmx.constants import (DigitalWidthUnits, AcquisitionType,
                               ReadRelativeTo, OverwriteMode, DigitalWidthUnits,
                               TriggerType, TaskMode, READ_ALL_AVAILABLE)
from numpy import linspace
from statistics import mean
from time import sleep


def setup_chans(config,ai,ao):
    '''Set up in and out channels
    
    Arguments:
        config: Current Config object 
        ai: In channel
        ao: out channel
    '''
    
    ramp_min_V,ramp_max_V = -1 * unyt.V, 1 * unyt.V
    pts_per_ramp = config.settings['steps']
    pretris = config.settings['nidaq_settings']['pretris']
    tris_per_scan = config.controls['sweeps'].value
    time_per_pt_us = config.settings['nidaq_settings']['time_per_pt'] * unyt.us
    settling_delay_ratio = config.settings['nidaq_settings']['settling_ratio']
    ai_min_V,ai_max_V = -1 * unyt.V, 1 * unyt.V

    ai_chan = config.settings['nidaq_settings']['ai_chan']
    ao_chan = config.settings['nidaq_settings']['ao_chan']

    pts_per_tri = pts_per_ramp * 2
    total_pts = pts_per_tri * (tris_per_scan + pretris)
    sample_rate_Hz = 1 / time_per_pt_us.to(unyt.s)
    settling_delay_us = time_per_pt_us * settling_delay_ratio
    pretri_delay_s = (pretris * time_per_pt_us * pts_per_tri).to(unyt.s)
    ramp = linspace(ramp_min_V, ramp_max_V, pts_per_ramp) #Generate the ramp points
    
    ao.control(TaskMode.TASK_UNRESERVE)
    ao.ao_channels.add_ao_voltage_chan(ao_chan,
                                       min_val=ramp_min_V,
                                       max_val=ramp_max_V)

    ao.timing.cfg_samp_clk_timing(sample_rate_Hz,
                                  sample_mode=AcquisitionType.CONTINUOUS,
                                  samps_per_chan=pts_per_tri)

    ao.triggers.start_trigger.trig_type = TriggerType.NONE
    ao_start_terminal = ao.triggers.start_trigger.term

    #Setup AI channel
    print(" Set up AI")
    ai.ai_channels.add_ai_voltage_chan(ai_chan,
                                       min_val=ai_min_V,
                                       max_val=ai_max_V)

    ai.timing.delay_from_samp_clk_delay = settling_delay_us.to(unyt.s)
    ai.timing.delay_from_samp_clk_delay_units = DigitalWidthUnits.SECONDS

    ai.timing.cfg_samp_clk_timing(sample_rate_Hz,
                                  sample_mode=AcquisitionType.CONTINUOUS,
                                  samps_per_chan=total_pts*2)

    ai.timing.read_all_avail_samp = True
    ai.timing.relative_to = ReadRelativeTo.FIRST_SAMPLE
    ai.timing.over_write  = OverwriteMode.OVERWRITE_UNREAD_SAMPLES

    ai.triggers.start_trigger.cfg_dig_edge_start_trig(ao_start_terminal)
    ai.triggers.start_trigger.trig_type = TriggerType.DIGITAL_EDGE
    ai.triggers.start_trigger.delay = pretri_delay_s
    ai.triggers.start_trigger.delay_units = DigitalWidthUnits.SECONDS

def start(ai,ao):
    print("Starting...",end='')
    ao.stop()
    ai.stop()
    ao.write(ramp)
    ai.in_stream.offset = 0
    ai.start()
    ao.start()
    print(" Started.")

def cutandavg(samps, ppt):
    """Process samples and return a list of average values per frequency.

    Arguments:
    samps -- the stream of samples
    ppt -- points per triange
    
    Input is measurements as output frequencies go up and down in a sawtooth
    pattern, aka, "triangles".
    
    Frequency levels look like 0,1,2,3,4,5,5,4,3,2,1,0,...
    
    We need to average across all of the 0s, 1s, etc, in the list of samples
    which is programmatically harder because the sequence goes backwards half
    the time.

    To explain the magic and complicated list comprehension,
    [                           Build a list 
    mean(                       Of averages
    [samps[i]                   Of points in the sample list, index i
    for t in range(0, numtris * ppt, ppt)
                                From triangles that start at index t
    for i in (t+p, t+ppt-(p+1))]
                                Two points in each triangle at offsets
                                p and -(p+1) from the beginning and end
                                of the triangle, respectively
    ) for p in range(ppt//2)]   Get average for each level in the triangle
    
    """
    
    #How many triangles? e.g. 35 samps w/10 ppt = 3 tris, drop extra 5
    numtris = len(samps) // ppt
    
    #Using a magic list comprehension
    return [mean(
                [samps[i] for t in range(0, numtris * ppt, ppt)
                          for i in (t+p, t+ppt-(p+1))]
                ) for p in range(ppt//2)
           ]

# with nidaqmx.Task() as ai, nidaqmx.Task() as ao:
    # setup_chans(ai,ao)
    # start(ai,ao)

    # while True:
        # samples = ai.read(READ_ALL_AVAILABLE, timeout=pretri_delay_s)
        # print(cutandavg(samples, pts_per_tri))
        # sleep(1)
    


