## LM384 FORCE SENSITIVE RESISTOR AMPLIFIER CONFIGURATION
# COPYRIGHT: Blaise O'Mara
# Updated: 05-15-2025 (MM/DD/YYYY)
#---------------------------------------------------------
# PURPOSE
# The purpose of this script is to configure the RPi Pico W with the
# MCP6004 instrumentaiton amplifier and the A301-25 force sensitive 
# resistor (FSR) for proper amplification.
# This script will define the used GPIO, ADC, and power pins used and
# their specified values
#--------------------------------------------------------
# CONFIGURATION
# Import necessary libraries
from machine import ADC
from machine import Pin
import time

# Declare ADC pins
PIN_ADC2 = ADC(28)  # physical pin 34
PIN_ADC1 = ADC(27)  # physcial pin 32
PIN_ADC0 = ADC(26)  # physical pin 31
PIN_IO20 = Pin(20)  # physical pin 26

scale = 3.3/pow(2,16)   # ADC conversion factor
R1 = 10e3           # second stage resistor value
R3 = R1             # second stage resistor value
G2 = R3/R1          # gain at the second stage
Rf_a401 = 493e3     # first stage resistor value of A401 amp
Rf_a301 = 1.302e6	# first stage resistor value of A301 amp

start = 0
Ts = 0.5   # sampling time in sec
Fs = 1/Ts
Rfs_a401 = 0
Rfs_a301 = 0
F_a401 = 0
F_a301 = 0
Vref = 0.01

print("| Ohms A301	| Ohms A401	| lbs A301	| lbs A401 |")
print("-----------------------------------------------------")

# Record Vout and the compute the RFS voltage
while start==False:
    time.sleep(Ts)
    # ADC measures (volts)
    Vref = PIN_ADC0.read_u16() * scale
    Vout_a301 = PIN_ADC2.read_u16() * scale
    Vout_a401 = PIN_ADC1.read_u16() * scale
    # Resistance calculations (omhs)
    Rfs_a301 = G2*Rf_a301*(Vref/Vout_a301)
    Rfs_a401 = G2*Rf_a401*(Vref/Vout_a401)
    # Force calculations (pounds)
    F_a301 = 2520438*pow(Rfs_a301,-1.128)
    F_a401 = 154875*pow(Rfs_a401,-0.8125)
    
    print("|", f'{Rfs_a301:7.2f}', "	|", f'{Rfs_a401:7.2f}', "	|", f'{F_a301:3.2f}', "		|", f'{F_a401:3.2f}', "	|")
    # print("|    ", f'{Rfs_a301:7.2f}', "    |   ", f'{Rfs_a401:7.2f}', "   |")

    start = PIN_IO20.value()
    
    
    
    
    