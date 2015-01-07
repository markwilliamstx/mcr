
import time
import RPi.GPIO as GPIO

# Set the pin numbering mode
#GPIO.cleanup() when is this needed?
GPIO.setmode(GPIO.BCM)

#name the pin
led = 12

#set up the pin
GPIO.setup(led, GPIO.OUT)

def hello():

    print 'Hello Mark!'
    GPIO.output(led, 1)
    time.sleep (5)
    print 'Goodbye Mark!'
    GPIO.output(led, 0)
    time.sleep (5)

#loop
count = 0
countmax = 10
while count < countmax:
    hello()
    count +=1

GPIO.cleanup()