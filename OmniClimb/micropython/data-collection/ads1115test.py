""" ADS1115 ADC
The purpose of this script is to test reading and writing ADC values from the
ADS1115, a 4-channel I2C-enabled 16-bit ADC
"""

# Import necessary libraries
import time, uos, os
from machine import I2C, Timer, Pin
from ads1x15 import ADS1115
from array import array
from micropython import const

# Initialize I2C & ADC through ADS1115
addr = 72
gain = 1
i2c = I2C(0, sda=Pin(8), scl=Pin(9), freq=400000)
ads = ADS1115(i2c, address=addr, gain=gain)

# Initialize ADC channels and data arrays
ch_vref = 0
ch_a301 = 1
ch_a401 = 2
ch_empty = 3
_BUFFERSIZE = const(100)

timestamp = array("L", (0 for _ in range(_BUFFERSIZE)))
Vref = array("L", (0 for _ in range(_BUFFERSIZE)))
Vout_a301 = array("L", (0 for _ in range(_BUFFERSIZE)))
Vout_a401 = Vout_a301
Vout_empty = Vout_a301

# Interrupt service routine for data acquisition
# this is called by a timer interrupt
t_start = time.ticks_ms()
def sample(x, adc=ads.read_rev, data=Vout_a401, timestamp=timestamp, timestart=t_start):
    global index_put, irq_busy
    if irq_busy:
        return
    irq_busy = True
    if index_put < _BUFFERSIZE:
        timestamp[index_put] = time.ticks_diff(time.ticks_ms(), timestart)
        data[index_put] = adc()
        index_put += 1
    irq_busy = False

irq_busy = False

index_put = 0
ADC_RATE = 20       # sample every 20ms

# Set the conversion rate to 860 SPS (sampling period of 1.16 ms),
# This leaves plenty of processing time--about 18 ms-- for processing 
# data between conversions.

ads.set_conv(rate=7, channel1=ch_a401)
ads.read_rev()
time.sleep_ms(ADC_RATE)

tim = Timer(-1)
tim.init(period=ADC_RATE, mode=Timer.PERIODIC, callback=sample)

while index_put < _BUFFERSIZE:
    pass

tim.deinit()

print(timestamp)
print(Vout_a401)
