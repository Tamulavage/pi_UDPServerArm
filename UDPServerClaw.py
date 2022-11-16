#!/usr/bin/env python3
import socket
import RPi.GPIO as GPIO
import Adafruit_PCA9685
import time
import queue
import threading
import concurrent.futures

UDP_IP = "192.168.1.200"
PORT=2390
bufferSize=1024

serverSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

pwm = Adafruit_PCA9685.PCA9685()
pwm.set_pwm_freq(50)

# pwm_init = 300        90°
# pwm_max  = 500        180° 
# pwm_min  = 100        0°
 
angle = [300, 500, 300, 200]   

angles = None

def setup():
    
    serverSocket.bind((UDP_IP,PORT))
    
    GPIO.setmode(GPIO.BOARD)	# Numbers GPIOs by physical location
    
    pwm.set_pwm(0, 0, 300) # start :90
    pwm.set_pwm(1, 0, 500) # start  flat : 180
    pwm.set_pwm(2, 0, 300) # start :90
    pwm.set_pwm(3, 0, 200) # start claw slighly open

    print("starting server")

def convert(value):
    scale = float(value+90)/float(180)
    return 100+(scale*400)

def convertNegate(value):
    scale = float(value)/float(180)
    return ((scale*400)-500)*-1

def convertshort(value):
    scale = float(value+90)/float(90)
    return 100+(scale*200)

def convertClaw(value):
    scale = float(value)/float(1024)
    return 100+(scale*200)

def rotation(ID, speed):
    global angle
    if ID == None:
        pass
    elif ID == 0:
        angle[0] = convert(speed)
        pwm.set_pwm(ID, 0, int(angle[0]))
    elif ID == 1:
        if speed > 0:
            angle[1] = convertNegate(speed)            
            angle[2] = 300
        else :
            angle[1] = 500
            angle[2] = convertshort(speed)
        pwm.set_pwm(1, 0, int(angle[1]))
        pwm.set_pwm(2, 0, int(angle[2]))
    elif ID == 2:
        angle[3] = convertClaw(speed)
        print(angle[3])
        pwm.set_pwm(3, 0, int(angle[3]))


def move_servo(value):
    global angles
    if value == 1:          # servo 1
        rotation(0,  angles) 
    elif value == 2:        # servo 2
        rotation(1,  angles)
    elif value == 3:        # servo 4
        rotation(2,  angles)    

def decodeSignal(message):
    value = None
    global angles
    
    if "ANGLE"==message[0:5]:
        print(message)
        if "ROLL" == message[6:10]:
            angles = int(message[10:])/10
            value = 1
        if "PITCH" == message[6:11]:
            angles = int(message[11:])/10
            value = 2

    elif "POT"==message[0:3]:
        angles = int(message[3:])
        value = 3
    return value

def receiveMsg(queue, event):
    lastMsg=""
    while not event.is_set():
        fullSignal= serverSocket.recvfrom(bufferSize)
        signal = fullSignal[0]
        message = str(signal, 'utf-8')[2:]
        if lastMsg!=message:
            lastMsg=message
            queue.put(message)
            
def processMsg(queue, event):
    while not event.is_set() or not queue.Empty():
        message = queue.get()
        
        value = decodeSignal(message)
        move_servo(value)

def loop(event):
    pipeline = queue.Queue(maxsize=100)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(receiveMsg, pipeline, event)
        executor.submit(processMsg, pipeline, event)


if __name__ == '__main__':
    setup()
    event = threading.Event()
    try:
        loop(event)
    except :
        print("exiting")

