#!/usr/bin/python

import logging
import sys
import sqlite3
import time
from datetime import datetime
from datetime import timedelta
import RPi.GPIO as GPIO
import thread
import utils

# Setup Stuff
# Setup Stuff

utils.flushThreshold = 0.1
utils.db = '/home/pi/git/pi/precip.db'
utils.valveSoftwareStatus = 'Closed'
utils.lastRunTime = datetime.now()
utils.database_init()
utils.email_restarted()

# Default rain amount per tip
tip = 0.01

# Set the pin numbering mode
GPIO.cleanup()
GPIO.setmode(GPIO.BCM)

# Alias the pin numbers to variables
rainPin = 11
resetPin = 27
statusLED = 5
valvePins = (7, 8, 25, 24)
relay5Pin = 23
relay6Pin = 18
relay7Pin = 15
relay8Pin = 14
auxRelays = (relay5Pin, relay6Pin, relay7Pin, relay8Pin)

# Sleep timing
valveDelay = 1

# Set up the rain pin as a pull up pin for the rain gauge. The gauge should be a switch between the rain_pin and ground
GPIO.setup(rainPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(resetPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(statusLED, GPIO.OUT)

# Set the valve pins up as outputs
for x in valvePins:
    GPIO.setup(x, GPIO.OUT)

for x in auxRelays:
    GPIO.setup(x, GPIO.OUT)

# Set their pins high which corresponds to the off state of the relay
for x in valvePins:
    GPIO.output(x, True)

for x in auxRelays:
    GPIO.output(x, True)

# Set up logging
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

# Flashes the status LED
def flash(pin, num, duration):

    for i in range(0, num):
        GPIO.output(pin, True)
        time.sleep(duration)
        GPIO.output(pin, False)
        time.sleep(duration)

# Get the amount of rain that has fallen in the past period as measured in timeType of minutes or hours
def rain_over_period(period, timeType):

    if timeType == 'minutes':
        offset = datetime.now() - timedelta(minutes=period)
    if timeType == 'days':
        offset = datetime.now() - timedelta(days=period)

    try:
        conn = sqlite3.connect(utils.db)
        c = conn.cursor()
        sql = "SELECT sum(amount) AS 'total rainfall' FROM rain WHERE dt > (?)"
        c.execute(sql, (offset,))

        total = c.fetchall()
        total1 = total[0]
        total = round(total1[0],2)

        logging.info('This is the total: ')
        logging.info(total)


        if period == 30 and timeType == 'minutes':
            utils.thirtyMinuteTotal = total
            sql = 'UPDATE tempstorage SET thirtymin = (?) WHERE id = 0'
            c.execute(sql, (total,))
        elif period == 3 and timeType == 'days':
            utils.threeDayTotal = total
            sql = 'UPDATE tempstorage SET threeday = (?) WHERE id = 0'
            c.execute(sql, (total,))
        else:
            logging.debug("Trouble with the rain period mapping to the database, check variables")

        return total

    except Exception:
        logging.debug('Error getting rain total from database')

    conn.commit()
    conn.close()

# Get the status of the valves TODO
def valve_hardware_status():
    utils.valve1_status = 'TODO'
    utils.valve2_status = 'TODO'
    utils.valve3_status = 'TODO'
    utils.valve4_status = 'TODO'

# Opens the four valves, taking sleeptime to open each one to avoid over-drawing our power supply
def open_valves(sleeptime):

    logging.info('valves opening')

    utils.valveSoftwareStatus = "Opening"

    for x in valvePins:
        GPIO.output(x, False)
        time.sleep(sleeptime)
        logging.info(x)
        logging.info('is open')

    utils.valveSoftwareStatus = "Open"

    utils.update_web_variables()

# Closes the four valves, taking sleeptime to open each one to avoid over-drawing our power supply
def close_valves(sleeptime):

    logging.info('valves closing')

    utils.valveSoftwareStatus = "Closing"

    for x in valvePins:
        GPIO.output(x, True)
        time.sleep(sleeptime)
        logging.info(x)
        logging.info(' closed')

    utils.valveSoftwareStatus = "Closed"

    utils.update_web_variables()

def pump():

    triggerstate = utils.tempstorage_retrieve(11)

    # conn = sqlite3.connect(utils.db)
    # c = conn.cursor()
    # sql = "SELECT * FROM tempstorage"
    # c.execute(sql)
    # dump = c.fetchall()
    # conn.commit()
    # conn.close()
    #
    # data = dump[0]
    # state = data[11]

    if triggerstate == 'on':
        GPIO.output(relay5Pin, False)
        utils.pumpLastOn = datetime.now()
        utils.tempstorage_update(11, 'Running')
        logging.info('Pump turned on.')

    elif triggerstate == 'off':
        GPIO.output(relay5Pin, True)
        utils.tempstorage_update(11, 'Turned Off')
        logging.info('Pump turned off.')

    # elif triggerstate == 'running':
    #     laston = utils.pumpLastOn
    #     ontime = datetime.now() - laston
    #     logging.info('Pump has been on for: ')
    #     logging.info(ontime)
    #     if ontime > timedelta(seconds=6):
    #         GPIO.output(relay5Pin, True)
    #         utils.tempstorage_update(11, 'turned off')
    #         logging.info('Pump auto-shutoff completed')

# Logic behind when to open/close valves
def valve_control():

    def openv():
        thread.start_new_thread(open_valves,(valveDelay,))

    def close():
        thread.start_new_thread(close_valves,(valveDelay,))

    valve_override = utils.tempstorage_retrieve(10)

    # Log data to console
    logging.info('Valve override = ')
    logging.info(utils.tempstorage_retrieve(10))

    utils.thirtyMinuteTotal = rain_over_period(30, 'minutes')
    logging.info('half hour total is:')
    logging.info(utils.thirtyMinuteTotal)

    utils.threeDayTotal = rain_over_period(3, 'days')
    logging.info('Three day total is:')
    logging.info(utils.threeDayTotal)

    # Before anything else, execute any valve overrides from the webpage
    if valve_override == 'Open':
        openv()
        utils.update_valve_override('No')

    elif valve_override == 'Close':
        close()
        utils.update_valve_override('No')

    # Now we check the normal logic to see if the valves should be open or closed

    elif utils.thirtyMinuteTotal > 0:                       # If it's currently raining
        if utils.threeDayTotal < utils.flushThreshold:      # and the roofs are dirty
            if utils.valveSoftwareStatus == 'Closed':       # and the valves are closed
                openv()                                     # Open them to flush, dirty water coming in!

            elif utils.valveSoftwareStatus == 'Open':       # But, if the valves are already open,
                logging.info('Valve already open.')         # Just leave them alone and log that we checked

        elif utils.threeDayTotal > utils.flushThreshold:    # It's raining now and the roofs are clean
            if utils.valveSoftwareStatus == 'Open':         # But the valves are still open
                close()                                     # Close them, let's collect some rainwater!
                utils.email_collecting()                    # E-mail that the system is collecting water!

            elif utils.valveSoftwareStatus == 'Closed':     # It's raining on clean roofs and we're collecting water
                logging.info('Valve already closed.')       # Just leave the valves alone and log that we checked

    elif utils.thirtyMinuteTotal <= 0:                      # If it hasn't rained in the last 30 min, lets close the valves
        if utils.valveSoftwareStatus == 'Open':             # Are the valves are open?
            close()                                         # Close em and save the relays

        elif utils.valveSoftwareStatus == 'Closed':         # Are the valves closed?
            logging.info('Valve already closed.')           # Just log that we checked

    # Old Logic below:
    # elif utils.thirtyMinuteTotal > 0 \
    #     and utils.threeDayTotal < utils.flushThreshold \
    #         and utils.valveSoftwareStatus == 'Closed':
    #             open()
    #
    # elif utils.thirtyMinuteTotal > 0 \
    #     and utils.threeDayTotal < utils.flushThreshold \
    #         and utils.valveSoftwareStatus == 'Open':
    #             logging.info('Valve already open.')
    #
    # elif (utils.thirtyMinuteTotal > 0
    #     and utils.threeDayTotal > utils.flushThreshold
    #         and utils.valveSoftwareStatus == 'Open'):
    #             close()
    #             utils.email_collecting()
    #
    # elif (utils.thirtyMinuteTotal > 0
    #     and utils.threeDayTotal > utils.flushThreshold
    #         and utils.valveSoftwareStatus == 'Closed'):
    #             logging.info('Valve already closed.')
    #
    # elif (utils.thirtyMinuteTotal < 0
    #     and utils.threeDayTotal < utils.flushThreshold
    #         and utils.valveSoftwareStatus == 'Open'):
    #             close()
    #
    # elif utils.thirtyMinuteTotal < 0 \
    #     and utils.threeDayTotal < utils.flushThreshold \
    #         and utils.valveSoftwareStatus == 'Closed':
    #             logging.info('Valve already closed.')

    utils.update_web_variables()

# This is the callback function that gets triggered when it rains
def log_rain(channel):
    logging.info('Rain Tip Detected!')
    conn = sqlite3.connect(utils.db)
    c = conn.cursor()
    sql = 'INSERT INTO rain(amount) VALUES (?)'
    c.execute(sql, (tip,))
    logging.info('data inserted')
    conn.commit()
    conn.close()

    flash(statusLED, 3, .07)

# Watch the rain_pin for a rain event, callback to log_rain to log it.
GPIO.add_event_detect(11, GPIO.RISING, callback=log_rain, bouncetime=150)

# Watch the for database reset button.
GPIO.add_event_detect(27, GPIO.RISING, callback=utils.db_drop, bouncetime=150)

# Actually Run this thing:

while True:

    valve_hardware_status()
    valve_control()
    pump()
    utils.lastRunTime = datetime.now()
    utils.update_web_variables()
    flash(statusLED, 1, .1)
    utils.purge_old()
    time.sleep(2)

GPIO.cleanup()






