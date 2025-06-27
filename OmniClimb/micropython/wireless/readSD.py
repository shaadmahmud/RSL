import uos
import sdcard
from machine import Pin, SPI

# Define the Chip Select (CS) pin (GP13)
cs_pin = Pin(13, mode=Pin.OUT, value=1)

# Initialize the SPI bus
spi = SPI(1, baudrate=40000000, sck=Pin(14), mosi=Pin(15), miso=Pin(12))

sd = sdcard.SDCard(spi=spi, cs=cs_pin, baudrate=20000000)

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
