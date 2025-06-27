"""
Filename: sensorCharacterization.py
Author: Blaise O'Mara
Last update: 2025-06-27
Version: 1.1 (Modified for 20ms periodic sampling)
Description:
    This script records voltage data for characterizing the Tekscan A401-100 and
    A4301-100 force sensitive resistors. The data recorded is a 16-bit value
    on the voltage scale from 0-3.3V. It utilizes a dual-core approach on
    MicroPython (e.g., Raspberry Pi Pico) to sample ADC data periodically
    and write it to an SD card asynchronously.

ACKNOWLEDGEMENTS:
    The multithreading implemented in this script was inspired by Bob
    Grant's video
    <https://www.youtube.com/watch?v=1q0EaTkztIs&t=424s>
    detailing how to utilize both cores of the R2040 processor.

    Force data is recorded using the ADS1115 module. The ads1x15.py library
    is used to control the ADS1115. This library was authored by Robert
    Hammelrath, and it may be found here
    <https://github.com/robert-hh/ads1x15/tree/master> on GitHub.

    Force data is written to an external Micro SD card module. The file
    sdcard.py, from the MicroPython library was modified by Brenton Schulz,
    is used. This script may be found here
    <https://github.com/RuiSantosdotme/Random-Nerd-Tutorials/tree/master/Projects/Raspberry-Pi-Pico/MicroPython/sd_card>
    on Rui Santos' GitHub.
"""

import _thread
import uos
import sdcard
from time import sleep_us
from utime import ticks_ms, ticks_us, ticks_diff
from machine import I2C, SPI, Pin, ADC, Timer
from ads1x15 import ADS1115

"""GLOBAL VARIABLES - Declared for clarity and access in both cores/ISR"""
# These variables need to be accessed and modified by both the main thread (Core 0)
# and the sub-thread (Core 1 for writing), and the Timer Interrupt Service Routine (ISR).
global t0               # Global start time reference for timestamps (in microseconds)
global data_load        # Buffer holding data ready to be written to SD card
global flag_dataWritten # Flag to signal that data_load is ready
global irq_busy         # Flag to prevent re-entrant calls to the ISR
global index_put        # Current index for filling the data_samples buffer
global data_samples     # The main buffer for collecting samples (list of lists)
global BUFFERSIZE       # Constant for the size of the data buffer
global ads              # ADS1115 ADC instance
global PIN_ADC0         # Pico's internal ADC pin instance


"""FUNCTIONS"""

# ADC sampling function running on Core 0.
# This function is called periodically by the timer. It hands off a
# data buffer for Core 1 to write data to an Micro SD card
def core0_sample(timer_obj):
    global data_load
    global flag_dataWritten
    global t0
    global irq_busy
    global index_put
    global data_samples
    global ads
    global PIN_ADC0
    global BUFFERSIZE

    # Check if the ISR is already busy processing a previous call.
    # If not, declare that it's busy
    if irq_busy:
        return
    irq_busy = True

    if index_put < BUFFERSIZE:
        current_time_us = ticks_ms()
        
        # Store timestamp (difference from global t0, in microseconds)
        data_samples[index_put][0] = ticks_diff(current_time_us, t0)
        
        # Read all four ADS1115 channels and store them
        for ch in range(4):
            data_samples[index_put][ch+1] = ads.read(rate=7, channel1=ch)
        
        # Read Vref from the Pico's internal ADC
        data_samples[index_put][5] = PIN_ADC0.read_u16()
        
        index_put += 1
    
    # Check if the buffer is full after storing the current sample
    if index_put >= BUFFERSIZE:
        # Save the data samples in a payload for Core 1 to access
        data_load = [list(row) for row in data_samples]
        flag_dataWritten = True
        index_put = 0

    irq_busy = False


# Data writing function running on Core 1
def core1_write2sd(file_path):
    global data_load
    global flag_dataWritten

    while True:
        # This thread continuously checks if new data is ready to be written
        if flag_dataWritten is True:
            t_start = ticks_ms()
            lines = []
            for row_array in data_load:
                row_str = ','.join(map(str, row_array))
                lines.append(row_str)
            data_load_str = '\n'.join(lines) + '\n'

            # Append data to the specified file on the SD card
            try:
                with open(file_path, "a") as f:
                    f.write(data_load_str)
            except OSError as e:
                print(f"Error writing to file: {e}\n")
            
            t_2write = ticks_diff(ticks_ms(), t_start)
            print(f"Time to write:{t_2write} ms\n")
            
            flag_dataWritten = False
        
        # Add a small delay to yield CPU when data isn't ready
        sleep_us(100)


"""INITIALIZATION"""
# Declare constants
BUFFERSIZE = 100
ADC_SAMPLE_PERIOD_MS = 20

# Initialize ADC pin for Vref (Pico's internal ADC on GP26)
PIN_ADC0 = ADC(26)

# Initialize I2C bus and ADS1115 ADC
i2c = I2C(0, sda=Pin(16), scl=Pin(17), freq=400000)
ads = ADS1115(i2c, address=72, gain=1)

# SD card setup
# Define the Chip Select (CS) pin (GP13) for the SD card module
cs_pin = Pin(13, mode=Pin.OUT, value=1)

# Initialize the SPI bus for SD card communication
spi = SPI(1,
          baudrate=20000000,
          sck=Pin(14),
          mosi=Pin(15),
          miso=Pin(12))

# Initialize SD card object with the configured SPI and CS pin
sd = sdcard.SDCard(spi=spi, cs=cs_pin, baudrate=20000000)

# Initialize data structure for collecting samples.
# There is a timestamp, the four ADC channels, and Vref
data_samples = [[0 for _ in range(6)] for _ in range(BUFFERSIZE)]

# Initialize data_load
data_load = [list(row) for row in data_samples]

# Define file path for saving data on the SD card
file_base = "/sd/omniclimb/"
fname = "sensorChar_test.txt"
file_path = file_base + fname

# Mount the SD card. If the directory does not exist, create it.
try:
    uos.mount(sd, "/sd")
    print("SD card mounted successfully at /sd\n")
    # Ensure the directory exists
    try:
        uos.mkdir(file_base)
        print(f"Created directory: {file_base}\n")
    except OSError:
        pass
except OSError as e:
    print(f"Error mounting SD card: {e}. Ensure SD card is inserted and formatted correctly.\n")

"""WRITE HEADER TO FILE"""
# The header defines the columns in the output CSV file.
header = "Time (us),ch0,ch1,ch2,ch3,Vref (V)\n"
try:
    with open(file_path, "w") as f:
        f.write(header)
    print(f"Header written to {file_path}\n")
except OSError as e:
    print(f"Error writing header to file: {e}\n")

"""DEFINE THREADS AND CONTROL FLAGS INITIAL STATE"""
flag_dataWritten = False
irq_busy = False
index_put = 0
t0 = ticks_ms()     # initial start time

# Start the SD card writing thread on the second core (Core 1).
thread_1 = _thread.start_new_thread(core1_write2sd, [file_path])
print("SD card writing thread started on Core 1.\n")

# Prompt user to start data recording
input("Press Enter to start data recording: ")

"""EXECUTE SAMPLING ON CORE 0 VIA TIMER INTERRUPT"""
# Initialize a periodic timer.
tim = Timer(-1)
tim.init(mode=Timer.PERIODIC, period=ADC_SAMPLE_PERIOD_MS, callback=core0_sample)
print(f"ADC sampling timer initialized on Core 0 with a period of {ADC_SAMPLE_PERIOD_MS} ms.\n")

# Main loop for Core 0. This loop keeps Core 0 active while the timer ISR
# handles sampling and the other core handles writing.
print("Sampling and writing process running. Press Ctrl+C to stop.\n")
try:
    while True:
        sleep_us(100)
except KeyboardInterrupt:
    print("\nProgram interrupted by user (Ctrl+C detected).")
finally:
    # Clean up resources when the program stops
    print("De-initializing timer...")
    tim.deinit()
    
    print("Unmounting SD card...")
    try:
        uos.umount("/sd")
        print("SD card unmounted successfully.")
    except OSError as e:
        print(f"Error unmounting SD card: {e}")

    # Verify that the data was written by attempting to read it.
    print("\n--- Attempting to verify written data (for debugging) ---")
    try:
        with open(file_path, "r") as f:
            read_data = f.read()
            print(f"Content of {file_path}:\n{read_data}\n")
    except OSError as e:
        print(f"Could not read from file {file_path} after unmount: {e}. Data should be on card.\n")

print("Script execution finished.")
