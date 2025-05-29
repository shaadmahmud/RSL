# FSR CHARACTERIZATION
# COPYRIGHT: Blaise O'Mara
# Updated: 05-09-2025
# ---------------------------------------------------------
# PURPOSE
# The purpose of this script is to use the Raspberry Pi Pico W
# for characterizing the force-resistance relationship of FSRs.
# These FSRs are: (1) Tekscan A401-100, and (2) Tekscan A301-100.
# Their force output will be measured via a simple voltage divider.
# The goal is to get a general idea of the FSRs' resistance given a 
# specific force input.
# --------------------------------------------------------
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

bits = pow(2,16)
scale = 3.3/bits
R1 = 493000
R2 = 13020000
Vs = 3.299
start = 0

print("| Resistance A301-100  |   Resistance A401-100 |")
print("--------------------------------------------------")

# Record Vout and the compute the FSR resistances
while start==False:
    time.sleep(0.5)
    Vo_a301 = PIN_ADC2.read_u16()*scale
    Vo_a401 = PIN_ADC1.read_u16()*scale
    Rfs_a301 = (R2*Vo_a301) / (Vs-Vo_a301)   # votalge divider
    Rfs_a401 = (R1*Vo_a401) / (Vs-Vo_a401)   # votalge divider

    print("|    ", f'{Rfs_a301:7.2f}', "    |   ", f'{Rfs_a401:7.2f}', "   |")
    start = PIN_IO20.value()

