"""
The purpose of this script is to test reading and writing ADC values from the
ADS1115, a 4-channel I2C-enabled 16-bit ADC
"""

# Import necessary libraries
import uos
import sdcard
from utime import ticks_ms, ticks_diff, sleep_ms
from machine import I2C, SPI, Pin
from ads1x15 import ADS1115
from micropython import const
import struct  # Import the struct module

"""FUNCTIONS"""
def write2sd(file_path, data_buffer):
    """
    Writes the data buffer to the SD card.  Handles errors and timing.

    Args:
        file_path (str): The path to the file on the SD card.
        data_buffer (bytes): The data to write (as a bytes object).
    """
    start_time = ticks_ms()
    try:
        with open(file_path, "ab") as f:  # Use "ab" to append binary data
            f.write(data_buffer)
    except OSError as e:
        print(f"Error writing to file: {e}\n")
        return  # Important: Exit if there's an error
    end_time = ticks_ms()
    write_time_ms = ticks_diff(end_time, start_time)
    print(f"Wrote {len(data_buffer)} bytes in {write_time_ms} ms")
    return write_time_ms # Return write time

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

sd = sdcard.SDCard(spi=spi, cs=cs_pin)

# Define file path
file_base = "/sd/omniclimb/"
fname = "forcedata.dat"  # Use .dat for binary data
file_path = file_base + fname

# Set number of samples to capture
_BUFFERSIZE = const(1)

# Initialize ADC channels
channels = [0, 1, 2, 3]

# Mount the SD card
try:
    uos.mount(sd, "/sd")
    print("SD card mounted successfully at /sd\n")
except OSError as e:
    print(f"Error mounting SD card: {e}")
    # Potentially add code here to halt or retry
    raise  # Re-raise the exception to stop execution if mounting fails

"""WRITE HEADER"""
header_format = "<IIII"  # Define the struct format string ONCE
header_names = ["Time (ms)", "Vref", "Vout_a301", "Vout_a401", "Vs"]
header_size = struct.calcsize(header_format)
header_buffer = bytearray()
for i in range(len(header_names)):
    header_buffer.extend(header_names[i].encode('utf-8'))
    if i < len(header_names)-1:
        header_buffer.extend(b',')
header_buffer.extend(b'\n')

# Write header
try:
    with open(file_path, "wb") as f:  # Use "wb" for binary header
        f.write(header_buffer)
    print(f"Header written to {file_path}\n")
except OSError as e:
    print(f"Error writing to file: {e}\n")
    raise  # Re-raise to stop if header write fails

# Sample each channel in single-shot mode with a timestamp
t_start = ticks_ms()
data_buffer = bytearray()
for sample in range(_BUFFERSIZE):
    timestamp = ticks_diff(ticks_ms(), t_start)
    sample_data = [timestamp]  # Start with the timestamp
    for ch in channels:
        sample_data.append(ads.read(rate=7, channel1=ch))
    # Pack the data using the pre-defined format string
    packed_data = struct.pack(header_format, *sample_data) #pack according to the number of channels
    data_buffer.extend(packed_data)

write_time = write2sd(file_path, data_buffer) #time the write
if write_time > 8:
    print(f"WARNING: Write time exceeded 8ms: {write_time} ms")

# Unmount the SD card
try:
    uos.umount("/sd")
    print("SD card unmounted.")
except OSError as e:
    print(f"Error unmounting SD card: {e}")
