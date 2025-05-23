## REAL-TIME ROCK CLIMBING FORCE SENSOR READING
# COPYRIGHT: Blaise O'Mara
# Updated: 18-02-2025
#---------------------------------------------------------
# PURPOSE
# The purpose of this script is to configure the RPi Pico W with the
# LM384 and the force sensitive resistor for writing voltage data to 
# a csv file
#--------------------------------------------------------
# CONFIGURATION
# Import necessary libraries
from machine import ADC
from machine import Pin
import time
import math

# Declare ADC pins
PIN_ADC2 = ADC(28)  # physical pin 34
PIN_ADC1 = ADC(27)  # physcial pin 32
PIN_ADC0 = ADC(26)  # physical pin 31
PIN_IO20 = Pin(20)  # physical pin 26

scale = 3.3/math.pow(2,12)   # ADC conversion factor
R1 = 10e3           # second stage resistor value
R3 = R1             # second stage resistor value
G2 = R3/R1          # gain at the second stage
Req = 690.9e3       # first stage resistor value

start = 0
Ts = 0.1   # sampling time in sec
Fs = 1/Ts
R_fsr = 0
F_lbs = 0

# Record Vout and the compute the RFS voltage
while start==False:
    time.sleep(Ts)
    Vout = (PIN_ADC2.read_u16() >> 4) * scale
    Vo1 = (PIN_ADC1.read_u16() >> 4) * scale
    Vref = (PIN_ADC0.read_u16() >> 4) * scale
    if Vout != Vo1 and Vo1/Vref != 1:
        R_fsr = Req / (Vo1/(Vref) - 1)
    if R_fsr > 0:
        F_lbs = math.pow(781117/R_fsr,1.055)
    
#     print("Vout:", Vout)
#     print("Vo1", Vo1)
#     print("V_ref:", Vref)
#     print('FSR Resistance:', R_fsr, "Ohms")
#     print('Force Applied:', F_lbs, "lbs")
    print("Force", F_lbs)

    start = PIN_IO20.value()