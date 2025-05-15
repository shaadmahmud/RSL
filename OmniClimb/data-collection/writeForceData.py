# WRITE DATA
# The purpose of this script is to test writing recorded force data to the MicroSD Card Adapter

# Import necessary libraries
import machine
import os
import time

# Define the SPI pins - adjust if your wiring is different
sck_pin = machine.Pin(10)
mosi_pin = machine.Pin(11)
miso_pin = machine.Pin(12)

# Define the Chip Select (CS) pin - adjust if your wiring is different
cs_pin = machine.Pin(9, machine.Pin.OUT)

# Initialize the SPI bus
spi = machine.SPI(0,
                  baudrate=1000000,  # Adjust as needed (1MHz is a good starting point)
                  polarity=0,
                  phase=0,
                  sck=sck_pin,
                  mosi=mosi_pin,
                  miso=miso_pin)

# Function to select the SD card
def sd_select():
    cs_pin.value(0)

# Function to deselect the SD card
def sd_deselect():
    cs_pin.value(1)

# Check to see if the SD card can be mounted
try:
    os.mount(machine.SDCard(spi, cs=cs_pin), "/sd")
    print("SD card mounted successfully at /sd")
except OSError as e:
    print(f"Error mounting SD card: {e}")
    print("Make sure the SD card is properly inserted and the wiring is correct.")
    # Potentially add code here to halt or retry

# Write data
file_path = "/sd/gemini_test.txt"
data_to_write = "Hello from Pico W! This data was written to the SD card."

try:
    with open(file_path, "w") as f:
        f.write(data_to_write)
    print(f"Data written to {file_path}")
except OSError as e:

# Verify that the data was written
try:
    with open(file_path, "r") as f:
        read_data = f.read()
        print(f"Data read from {file_path}: {read_data}")
except OSError as e:
    print(f"Error reading from file: {e}")
    print(f"Error writing to file: {e}")

# It's good practice to unmount the SD card once done
try:
    os.umount("/sd")
    print("SD card unmounted.")
except OSError as e:
    print(f"Error unmounting SD card: {e}")