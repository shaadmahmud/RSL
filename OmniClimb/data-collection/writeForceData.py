# WRITE DATA
# The purpose of this script is to test writing data to the MicroSD Card Adapter

# Import necessary libraries
from machine import SPI, ADC, Pin, Timer
import uos, sdcard, time, fsr

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

# Declare ADC pins
PIN_ADC2 = ADC(28)  # physical pin 34, a301
PIN_ADC1 = ADC(27)  # physcial pin 32, a401
PIN_ADC0 = ADC(26)  # physical pin 31, Vref
PIN_IO20 = Pin(20)  # physical pin 26, cancel button

Ts = 0.02           # sampling period in sec
Fs = 1/Ts           # sampling frequency
t_dur = 10          # duration of recording in sec
N = int(Fs*t_dur)   # number of samples

def record(time_start):
    # Sample voltages and calculate force output
    Vref = (PIN_ADC0.read_u16() >> 4)
    Vout_a301 = (PIN_ADC2.read_u16() >> 4)
    Vout_a401 = (PIN_ADC1.read_u16() >> 4)
    F_a301 = fsr.a301().force2(vref=Vref, vout=Vout_a301)
    F_a401 = fsr.a401().force2(vref=Vref, vout=Vout_a401)
    time_stamp = time.ticks_diff(time.ticks_ms(),ticks_start)
    data = f"{time_stamp},f'{F_a301},f'{F_a401}\n"

    # Write data to txt file with csv format
    try:
        with open(file_path, "a") as f:
            f.append(data)
    except OSError as e:
        print(f"Error writing to file: {e}\n")


# Mount the SD card
try:
    uos.mount(sd, "/sd")
    print("SD card mounted successfully at /sd\n")
    print(uos.listdir('/sd'))
except OSError as e:
    print(f"Error mounting SD card: {e}")
    # Potentially add code here to halt or retry


""" Write Data """
file_path = "/sd/omniclimb/forcedata.txt"
header = "Time (ms),Force A301 (lbs),Force A401 (lbs)\n"

# Write header
try:
    with open(file_path, "w") as f:
        f.write(header)
    print(f"Data written to {file_path}\n")
except OSError as e:
    print(f"Error writing to file: {e}\n")

ticks_start = time.ticks_ms()
# Write force data
tim = Timer(-1)
tim.init(mode=Timer.PERIODIC,
         period=Ts,
         callback=record(time_start=ticks_start))
time.sleep(t_dur)
tim.deinit()


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
