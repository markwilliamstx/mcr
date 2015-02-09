__author__ = 'Mark'
# TODO Add Imports

import time
import pifacedigitalio as pfio


# TODO Set Up

pfio.init()


# Function to test pin 0 to see whether dome is open: pin low is open, high is closed
def dome_status():
    if pfio.digital_read(0) == 0:
        return "closed"
    if pfio.digital_read(0) == 1:
        return "open"


# Function to test pin 1 to see whether it is raining: pin low is raining, high is not raining  d,
def rain_status():
    if pfio.digital_read(1) == 0:
        return "not raining"
    if pfio.digital_read(1) == 1:
        return "raining"


# Function to turn rain detector on or off
def rain_detector(detector_state):
    if detector_state:
        pfio.digital_write(0, 1)  # detector_state = True to turn rain detector on
    if not detector_state:
        pfio.digital_write(0, 0)  # detector_state = False to turn rain detector off


# Function to force dome closed
def dome_closed(dome_state):
    if dome_state:
        pfio.digital_write(1, 1)  # dome_state  = True to close relay and force dome closed
    if not dome_state:
        pfio.digital_write(1, 0)  # dome_ state = False to open relay and allow dome control via controller


# TODO: Add function to measure rain intensity from ADC
# TODO: Add function to ping ACP to ensure observatory computer is running and ACP is on


# Initiate Rain Detector
rain_detector(False)              # turn off rain detector
dome_closed(False)                # be sure dome is not forced closed initially
time.sleep(10)


# Enter test loop to monitor dome status
while dome_status() == "closed":
    # TODO ping ACP
    print "Dome is closed"
    time.sleep(5)

# When dome opens, turn on rain detector and delay long enough for detector to stabalize outputs
print "Dome is open....turn on rain detector"
rain_detector(True)
time.sleep(10)

# Check if rain has been detected
while rain_status() == "not raining":
    print "Not raining"
    # TODO: Add check rain intensity is above threshold logic
    # TODO ping ACP
    time.sleep(5)

# TODO: Send weather alert to ACP, wait to see if ACP can close dome

# Force dome closed
print "Rain detected!!!.....closing dome"
dome_closed(True)

# Wait for dome to close
while dome_status("open"):
    print "Dome is open"
    time.sleep(5)
    #  TODO: timeout if dome never closes????
    
print "Dome is closed!!!!"

# At this point dome should have been forced closed
# Turn off rain detector but leave dome in forced closed state
# TODO: How to end gracefully?