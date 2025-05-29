import _thread
import uos
import sdcard
from utime import ticks_ms, ticks_diff
from machine import I2C, SPI, Pin
from ads1x15 import ADS1115
from array import array
from micropython import const

"""FUNCTIONS"""

# Define the ADC sampling function on Core 0
def core0_sample(data, buffersize, ads):
    global data_load            # access data load
    global flag_dataWritten     # access data written flag
    
    while True:
        # Sample each channel in single-shot mode with a timestamp (takes about 9-10ms to run through loop)
        t_start = ticks_ms()
        for sample in range(buffersize):
            timestamp = ticks_diff(ticks_ms(), t_start)
            time = RTC().datetime()
            for ch in range(4):     # all four channels are read
                data[sample][ch+1] = ads.read(rate=7, channel1=ch)
            data[sample][0] = timestamp
        data_load = data
        flag_dataWritten = True

# Define the SD card writing function on Core 1
def core1_write2sd(file_path):
    global data_load
    global flag_dataWritten

    while True:
        if flag_dataWritten is True:
            t_start = ticks_ms()    # capture start time of writing  
            # Transform data into a string
            lines = []
            for row_array in data_load:
                row_str = ','.join(map(str, row_array))
                lines.append(row_str)
            data_load_str = '\n'.join(lines) + '\n'

            # Append data
            try:
                with open(file_path, "a") as f:
                    f.write(data_load_str)
            except OSError as e:
                print(f"Error writing to file: {e}\n")
            t_2write = ticks_diff(ticks_ms(), t_start)
            print(f"Time to write:{t_2write} ms\n")     # print time to write
            flag_dataWritten = False


"""INITIALIZATION"""

# Initialize I2C & ADC through ADS1115
i2c = I2C(0, sda=Pin(16), scl=Pin(17), freq=400000)
ads = ADS1115(i2c, address=72, gain=1)
raw2volt = ads.raw_to_v

# Define the Chip Select (CS) pin (GP13)
cs_pin = Pin(13, mode=Pin.OUT, value=1)

# Initialize the SPI bus
spi = SPI(1,
          baudrate=40000000,
          sck=Pin(14),
          mosi=Pin(15),
          miso=Pin(12))

sd = sdcard.SDCard(spi=spi, cs=cs_pin, baudrate=20000000)

# Set number of samples to capture in one frame
_BUFFERSIZE = const(10)

# Initialize data arrays and construct a data matrix
timestamp = array("i", (0 for _ in range(_BUFFERSIZE)))
Vref = array("i", (0 for _ in range(_BUFFERSIZE)))
Vout_a301 = array("i", (0 for _ in range(_BUFFERSIZE)))
Vout_a401 = Vout_a301
Vout_empty = Vout_a301

# There are two data arrays. The first one, data_samples is a piece of data that
# is being constantly updated by the sampling thread on core 1. The second one,
# data_load is the completed sampled data of a particular frame. The load is 
# then written to memory by thread 2 on core 2

# array where each row is a variable, each column is a sample
data_samples = [timestamp, Vref, Vout_a301, Vout_a401, Vout_empty]

# reorganize the array so that samples are the rows and variables are columns
data_samples = [[row[i] for row in data_samples] 
                for i in range(len(data_samples[0]))]
data_load = data_samples    # initialize the data load as a copy

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

"""DEFINE THREADS & COMPLETE FLAG"""
flag_dataWritten = False
thread_1 = _thread.start_new_thread(core1_write2sd, [file_path])

"""Execute Threads"""
core0_sample(data=data_samples, buffersize=_BUFFERSIZE, ads=ads)

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

