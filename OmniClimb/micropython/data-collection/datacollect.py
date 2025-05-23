## LM384 FORCE SENSITIVE RESISTOR AMPLIFIER CONFIGURATION
# COPYRIGHT: Blaise O'Mara
# Updated: 17-04-2024
#---------------------------------------------------------
# PURPOSE
# The purpose of this script is to configure the RPi Pico W with the
# LM384 and the force sensitive resistor for proper amplification.
# This script will define the used GPIO, ADC, and power pins used and
# their specified values
#--------------------------------------------------------
# CONFIGURATION
# Import necessary libraries
from machine import ADC
from machine import Pin
import time
import os

# Declare Constants
PIN_ADC0 = ADC(26)
PIN_ADC2 = ADC(28)
PIN_IO20 = Pin(20)
scale = 3.3/65536

# This code is based on the work by M. Thothadri https://www.instructables.com/Data-Logging-With-Raspberry-Pi-Pico/
# Two files are written:
# (1) participants.csv  | holds participant demographics per row
# (2) forceData.csv     | holds force time-series data per participant per row
cwd = os.getcwd()
fname_par = "participants.csv"
fname_data = "forceData.csv"

# Check if data file exists; if not, create file
if fname_data in os.listdir():
    file_data=open(fname_data,"a")
    file_data.write("\n")
else:
    file_data=open(fname_data,"w")

# Prompt user to start recording force data
Ts = 0.01  # sampling period: 10ms
start = 1
while start!=0:
    start = input("Press '0' to start recording\n")
    start = int(start)

print("")
if start==False:
    print("Recording...\n")
    while start==False:
        force = PIN_ADC2.read_u16()*scale   # units are in volts
        file_data.write(str(force)+",")
        time.sleep(Ts)    # sample every 5ms
        start = PIN_IO20.value()

outcome = input("Sent or Failed? (1/0):\n")
file_data.write(outcome+",")
file_data.close()   # file is closed
print("Force data added.\n\n")

# Check if participant file exists; if not, create file
if fname_par in os.listdir():
    file_par=open(fname_par,"a")
    file_par.write("\n")
else:
    file_par=open(fname_par,"w")

# Collect participant demographics
print("_____________________________\n")
print("Enter Participant Information\n")
w = input("Weight (lbs):\n")
grade_par = input("Skill level (V-Grade):\n")
grade_route = input("Route V-Grade:\n")
sequence = input("Limb(s) Sensed (RH,LH,RF,LF)?\n")
attempt = input("Attempt Number:\n")
outcome = input("Sent or Fell?:\n")

# Write the demographic info
file_par.write(w+","+grade_par+","+grade_route+","+sequence+","+attempt+","+outcome+",")
file_par.close()			# The file is closed
print("Participant information added.")