""" ADS1115 ADC
The purpose of this script is to test reading and writing ADC values from the
ADS1115, a 4-channel I2C-enabled 16-bit ADC
"""

# Import necessary libraries
import uos
import sdcard
from utime import ticks_ms, ticks_diff, sleep_ms
from machine import I2C, SPI, Pin
from ads1x15 import ADS1115
from array import array
from micropython import const

"""FUNCTIONS"""
def write2sd(data, file_path):
    # Append data
    try:
        with open(file_path, "a") as f:
            f.write(data)
    except OSError as e:
        print(f"Error writing to file: {e}\n")


# Initialize I2C & ADC through ADS1115
i2c = I2C(0, sda=Pin(8), scl=Pin(9), freq=400000)
ads = ADS1115(i2c, address=72, gain=1)
raw2volt = ads.raw_to_v

# Define the Chip Select (CS) pin (GP09)
cs_pin = Pin(13, mode=Pin.OUT, value=1)

# Initialize the SPI bus
spi = SPI(1,
          baudrate=40000000,
          sck=Pin(10),
          mosi=Pin(11),
          miso=Pin(12))

sd = sdcard.SDCard(spi=spi, cs=cs_pin, baudrate=20000000)

# Initialize ADC channels and data arrays
# ch_vref = 0
# ch_a301 = 1
# ch_a401 = 2
# ch_empty = 3
channels = [0, 1, 2, 3]

# Set number of samples to capture
_BUFFERSIZE = const(10)

# Initialize data arrays and construct a data matrix
timestamp = array("I", (0 for _ in range(_BUFFERSIZE)))
Vref = array("I", (0 for _ in range(_BUFFERSIZE)))
Vout_a301 = array("I", (0 for _ in range(_BUFFERSIZE)))
Vout_a401 = Vout_a301
Vout_empty = Vout_a301

data = [timestamp,
        Vref,
        Vout_a301,
        Vout_a401,
        Vout_empty]

data = [[row[i] for row in data] for i in range(len(data[0]))]

# Define file path
file_base = "/sd/omniclimb/"
fname = "forcedata.txt"
file_path = file_base + fname

# Mount the SD card
try:
    uos.mount(sd, "/sd")
    print("SD card mounted successfully at /sd\n")
except OSError as e:
    print(f"Error mounting SD card: {e}")
    # Potentially add code here to halt or retry

"""WRITE HEADER"""
header = "Time (ms),Vref,Vout_a301,Vout_a401,Vs\n"
# Write header
try:
    with open(file_path, "w") as f:
        f.write(header)
    print(f"Header written to {file_path}\n")
except OSError as e:
    print(f"Error writing to file: {e}\n")

# Sample each channel in single-shot mode with a timestamp (takes about 9-10ms to run through loop)
t_start = ticks_ms()
for sample in range(_BUFFERSIZE):
    timestamp = ticks_diff(ticks_ms(), t_start)
    for ch, val in enumerate(channels):
        data[sample][ch+1] = ads.read(rate=7, channel1=channels[ch])
    data[sample][0] = timestamp
    #data_str = ','.join(map(str, data[sample])) + "\n"
    #write2sd(data=data_str, file_path=file_path)

# THIS IS GREAT CODE FOR WRITING A BULK PIECE OF DATA
lines = []
for row_array in data:
    row_str = ','.join(map(str, row_array))
    lines.append(row_str)

final_string = '\n'.join(lines)

w_start = ticks_ms()
write2sd(data=final_string, file_path=file_path)
w_end = ticks_ms()

# # Print out the Resulting data
# print("Timestamp (ms), Vref, Va301, Va401, Vs:\n")
# for sample_row in range(len(data)):
#     print(data[sample_row])

"""VERIFY THAT DATA WAS WRITTEN"""
# Verify that the data was written
try:
    with open(file_path, "r") as f:
        read_data = f.read()
        print(f"Data read from {file_path}: \n{read_data}\n")
except OSError as e:
    print(f"Error reading from file: {e}\n")

# Unmount the SD card
try:
    uos.umount("/sd")
    print("SD card unmounted.")
except OSError as e:
    print(f"Error unmounting SD card: {e}")

print(f"Time to write: {w_end-w_start}")
