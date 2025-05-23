""" WRITE FORCE DATA
The purpose of this script is to test writing recorded force data to the MicroSD Card Adapter
"""

# Import necessary libraries
from machine import SPI, Pin
import uos, sdcard

# Define the SPI pins
sck_pin = Pin(10)       # GP10
mosi_pin = Pin(11)      # GP11
miso_pin = Pin(12)      # GP12

# Define the Chip Select (CS) pin (GP09)
cs_pin = Pin(9, mode=Pin.OUT, value=1)

# Initialize the SPI bus
spi = SPI(1,
          sck=sck_pin,
          mosi=mosi_pin,
          miso=miso_pin)

sd = sdcard.SDCard(spi=spi,cs=cs_pin)

# Can also choose to mount the file system virutally so that the process is consistent across boards
# v = vfs.VfsFat(sd)

# Check to see if the SD card can be mounted
try:
    uos.mount(sd, "/sd")
    print("SD card mounted successfully at /sd\n")
    print(uos.listdir('/sd'))
except OSError as e:
    print(f"Error mounting SD card: {e}")
    # Potentially add code here to halt or retry

# Write data
file_path = "/sd/omniclimb/gemini_test.txt"
data_to_write = "Hello from Pico W! This data was written to the SD card."

try:
    with open(file_path, "w") as f:
        f.write(data_to_write)
    print(f"Data written to {file_path}\n")
except OSError as e:
    print(f"Error writing to file: {e}\n")

# Verify that the data was written
try:
    with open(file_path, "r") as f:
        read_data = f.read()
        print(f"Data read from {file_path}: {read_data}\n")
except OSError as e:
    print(f"Error reading from file: {e}\n")

# It's good practice to unmount the SD card once done
try:
    uos.umount("/sd")
    print("SD card unmounted.")
except OSError as e:
    print(f"Error unmounting SD card: {e}")
