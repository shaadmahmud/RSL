## LM384 FORCE SENSITIVE RESISTOR AMPLIFIER CONFIGURATION
# COPYRIGHT: Blaise O'Mara
# Updated: 10-29-2024
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

# Declare ADC pins
PIN_ADC2 = ADC(28)
PIN_ADC1 = ADC(27)
PIN_ADC0 = ADC(26)
PIN_IO20 = Pin(20)

scale = 3.3/65536
R1 = 1.49e6
R2 = 9.05e3
R3 = 9.07e3
Vs = 3.299
start = 0

# Record Vout and the compute the RFS voltage
while start==False:
    time.sleep(0.5)
    Vo_neg = PIN_ADC1.read_u16()*scale
    Vo_pos = PIN_ADC2.read_u16()*scale
    Vout = Vo_pos - Vo_neg
    Rfs = (R3*(Vs - Vo_pos)) / Vo_pos   # votalge divider
    Rfs2 = (R3 / (Vout/Vs + R3/(R3+R1))) - R3   # Wheatstone Bridge
    #print('Reference Voltage:',ref_check)
    print('Vout(+):', Vo_pos)
    print('Vout(-):', Vo_neg)
    print('Vout:', Vout)
    print('FSR Resistance 1:', Rfs)
    print('FSR Resistance 2:', Rfs2)
    print()
    start = PIN_IO20.value()