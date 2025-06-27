"""
Filename: main.py
Author: Blaise O'Mara
Date: 2025-06-04
Version: 1.0
Description:
    This script connects RPi Pico Ws to an external MQTT broker for the
    recording of force data in a rock-climbing environment. In a given rock
    climbing route, each RPi Pico W records force data exterted on a single
    rock hold with the use of force sensitive resistors. Exerted force is
    the force that the climber applies to a rock hold while ascending the
    route.

    The RPi Pico is a client that is remotely controlled by the broker via a
    Node-Red html user interface. This interface acts as the central control
    for multiple RPi Pico Ws that record force data.

    This script makes use of the RPi Pico W's WLAN and multithreading
    capabilities. Core 1 handles initialization, connection to the MQTT
    broker, publish and subscription transactions between it and the broker,
    and ADC recording. Core 2 handles the writing of this force data to an
    external Micro SD card module.

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

# Import standard micropython libraries, 3rd party libraries,
# and local libraries
import sys
import uos
import utime
import ujson
import network
import _thread
import sdcard
import ntptime
import config_mqtt
import config_wifi

# Import explicit library submodules
from machine import Pin, I2C, SPI # Pin is still needed for I2C/SPI
from lib.umqtt.simple import MQTTClient
from utime import ticks_ms, ticks_diff
from ads1x15 import ADS1115
from array import array # Explicitly imported
from micropython import const


"""----INITIALIZATION----"""


# Constants
_PICO_ID = config_mqtt.clientID
_SAMPLES_PER_FRAME = const(100)
_CHANNELS_PER_SAMPLE = const(5)
_SAMPLE_INTERVAL_MS = const(20)

# MQTT Topics
# All picos subscribe to the cental command topic and publish
# to their unique status topic
global_command_topic = b"pico/all/cmd"
status_topic = b"pico/" + _PICO_ID.encode() + b"/status"

# Global Data Recording State & Shared Buffer
recording_active = False
current_filename = ""

# Global MQTT Client Object
client = None

# Shared buffer for ADC data between Core 0 (sampling) and Core 1 (writing)
# This will hold completed 'frames' of data ready to be written.
# Using a list to hold 'array.array' objects (frames). Access to the
# data queue is locked between cores
data_queue = []
lock = _thread.allocate_lock()

# I2C and SPI setup
i2c = I2C(0, sda=Pin(16), scl=Pin(17), freq=400000)
cs_pin = Pin(13, mode=Pin.OUT, value=1)
spi_sd = SPI(1, baudrate=40000000, sck=Pin(14), mosi=Pin(15), miso=Pin(12))

# --- Initialize ADS1115 and SD Card --- #
ads = ADS1115(i2c, address=0x48, gain=1)
sd = sdcard.SDCard(spi=spi_sd, cs=cs_pin)
sd_card_present = False

# A single frame buffer to hold data before pushing to queue.
# Using 'l' data type for a minimum of 4 bytes for each data point.
# This size is necessary for capturing the timestamps. This could be
# made more efficient by allocating only 2 byes ('i')for ADC values
frame_buffer_raw = array('l', (0 for _ in range(
    _SAMPLES_PER_FRAME * _CHANNELS_PER_SAMPLE
    )))

# Network Setup
wlan = network.WLAN(network.STA_IF)


"""----FUNCTIONS----"""


# Synchronize Pico time with NTP
def sync_time():
    print("Attempting NTP time sync...")
    try:
        ntptime.host = "pool.ntp.org"
        ntptime.settime()
        print("Time synced via NTP:", utime.localtime())
    except Exception as e:
        print(f"NTP time sync failed: {e}")


# WiFi connection
def connect_to_network():
    # --- Soft Reset Wi-Fi Interface ---
    print("Performing soft reset of Wi-Fi interface...")
    if wlan.isconnected():
        wlan.disconnect()
        utime.sleep_ms(50)

    wlan.active(False)
    utime.sleep_ms(50)
    wlan.active(True)
    print("Wi-Fi interface reset complete.")
    # --- End Soft Reset ---

    wlan.config(pm=0xa11140)  # disable power-save mode
    wlan.connect(config_wifi.ssid, config_wifi.password)

    max_wait = 20  # wait time in seconds
    print(f"Connecting to Wi-Fi '{config_wifi.ssid}'...")
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('waiting for connection...')
        utime.sleep(1)

    if wlan.status() != 3:
        raise RuntimeError('network connection failed')
    else:
        print('WLAN connected')
        status = wlan.ifconfig()
        pico_ip = status[0]
        print('IP = ' + pico_ip)
        return pico_ip


# Mount SD card
def mount_sd_card():
    global sd_card_present
    try:
        uos.mount(sd, "/sd")
        print("SD card mounted successfully at /sd\n")
        sd_card_present = True
        return True
    except Exception as e:
        print(f"Error mounting SD card: {e}")
        print("Continuing without SD card. Data recording will not work.")
        sd_card_present = False
        return False


# ADC Recording (intended for Core 0 - main loop).
# This function will be called repeatedly in the main loop while
# recording_active is True.
def core0_record_adc_data_frame():
    global recording_active, lock, data_queue, frame_buffer_raw

    # Check if recording is active *before* starting to fill a new frame.
    # If not active, return immediately.
    with lock:  # Acquire lock to check recording_active as it's shared
        if not recording_active:
            # print("Core 0: Detected recording_active is FALSE. Returning.")
            return

    # Loop through to fill the entire frame buffer without checking the flag
    # within the loop
    for sample_idx in range(_SAMPLES_PER_FRAME):
        timestamp = ticks_ms()

        base_idx = sample_idx * _CHANNELS_PER_SAMPLE

        frame_buffer_raw[base_idx + 0] = timestamp
        frame_buffer_raw[base_idx + 1] = ads.read(rate=7, channel1=0)
        frame_buffer_raw[base_idx + 2] = ads.read(rate=7, channel1=1)
        frame_buffer_raw[base_idx + 3] = ads.read(rate=7, channel1=2)
        frame_buffer_raw[base_idx + 4] = ads.read(rate=7, channel1=3)

        # Calculate time elapsed for this sample and determine sleep duration
        elapsed_sample_time = ticks_diff(ticks_ms(), timestamp)
        sleep_duration = _SAMPLE_INTERVAL_MS - elapsed_sample_time

        if sleep_duration > 0:
            utime.sleep_ms(sleep_duration)

    # --- Check recording_active *after* the data frame is filled --- #
    # This check happens *after* the for loop completes all _SAMPLES_PER_FRAME.
    with lock:
        if recording_active:
            data_queue.append(array('i', frame_buffer_raw))
            print(f"Core 0: Completed and queued a \
                  {len(frame_buffer_raw)//_CHANNELS_PER_SAMPLE} \
                    -sample frame.")
        else:
            # If recording_active became False while we were filling the
            # buffer this full frame is discarded. The next call to this
            # function will stop immediately.
            print("Core 0: Recording stopped during frame collection.")


# SD Card Writing (runs on Core 1). Uncomment lines to measure write time
def core1_write2sd(file_path):
    global data_queue, recording_active, lock
    print(f"Core 1 (SD Write Thread) started for {file_path}")

    # Create/open the file once at the beginning of the thread's life
    try:
        with open(file_path, "a") as f:
            while True:
                data_to_write_frame = None
                with lock:
                    if data_queue:
                        data_to_write_frame = data_queue.pop(0)

                if data_to_write_frame:
                    # t_start_write = ticks_ms()

                    # Transform the 1D array.array frame into CSV lines
                    lines = []
                    for sample_idx in range(_SAMPLES_PER_FRAME):
                        base_idx = sample_idx * _CHANNELS_PER_SAMPLE
                        row_elements = [str(data_to_write_frame[base_idx + i])
                                        for i in range(_CHANNELS_PER_SAMPLE)]
                        lines.append(','.join(row_elements))

                    data_block_str = '\n'.join(lines) + '\n'

                    try:
                        f.write(data_block_str)
                        # f.flush() # Optional: force write to disk more often
                        print(f"Core 1: Wrote \
                              {len(data_to_write_frame)//_CHANNELS_PER_SAMPLE} \
                                samples to file.")
                    except OSError as e:
                        print(f"Core 1: Error writing to file {file_path}: {e}")
                        publish_status(f"recording_write_error_{e}".encode())
                        with lock:
                            recording_active = False  # Signal stop main loop
                        break  # Exit Core 1 loop on critical write error

                    # t_write_duration = ticks_diff(ticks_ms(), t_start_write)
                    # print(f"Core 1: Wrote {len(data_to_write_frame)//_CHANNELS_PER_SAMPLE} samples in {t_write_duration} ms\n")
                else:
                    # No data in queue, check recording_active state
                    with lock:
                        if not recording_active and not data_queue:
                            # If recording is off AND queue is empty,
                            #  then we can exit
                            print("Core 1: Recording stopped and queue empty. \
                                  Exiting thread.")
                            break
                    utime.sleep_ms(10)  # avoid busy-waiting

    except OSError as e:
        print(f"Core 1: Initial file open error for {file_path}: {e}")
        publish_status(f"recording_file_open_error_{e}".encode())
        with lock:
            recording_active = False  # Force stop on file open error
    except Exception as e:
        print(f"Core 1: Unexpected error in write thread: {e}")
        sys.print_exception(e)
        publish_status(f"recording_thread_error_{e}".encode())
        with lock:
            recording_active = False  # Force stop on unexpected error
    finally:
        print("Core 1 (SD Write Thread) finished.")
        # Ensure recording_active is false (handled by main loop too)
        with lock:
            recording_active = False
        publish_status(b"recording_stopped_core1_exit")


# Start data recording command
def start_adc_recording(filename_from_cmd):
    global recording_active, current_filename, lock, sd_card_present

    print("start_adc_recording called.")
    with lock:
        if recording_active:
            print("Recording already active. Ignoring start command.")
            publish_status(b"recording_already_active")
            return

        if not sd_card_present:
            print("SD card not mounted. Cannot start recording.")
            publish_status(b"error_sd_not_mounted")
            return

        current_filename = "/sd/" + filename_from_cmd

        # Clear any old data in the queue before starting new recording
        data_queue.clear()

        # Set recording_active to True *before* starting thread
        # This signals core0_record_adc_data_frame to start sampling
        recording_active = True
        print(f"DEBUG: recording_active set to \
              {recording_active} \
                in start_adc_recording.")

        # Start Core 1 thread only once when recording starts
        # This will now pass the filename to core1_write2sd directly
        _thread.start_new_thread(core1_write2sd, (current_filename, ))

        print(f"Starting recording to {current_filename}")
        publish_status(b"recording_started")


# Stop data recording command
def stop_adc_recording():
    global recording_active, lock
    print("stop_adc_recording called.")
    with lock:
        if not recording_active:
            print("No recording active. Ignoring stop command.")
            publish_status(b"no_recording_active")
            return

        recording_active = False  # Signal both Core 0 and 1 threads to stop
        print(f"DEBUG: recording_active set to \
              {recording_active} \
                in stop_adc_recording.")
        print("Stopping recording.")
        publish_status(b"recording_stopping_signal")


# Check Pico connection handler
def check_pico_connection():
    print("Received check connection command.")
    publish_status(b"connected")


# MQTT Message Callback Function
def mqtt_callback(topic, msg):
    print(f"Received MQTT message on topic '{topic.decode()}': '{msg.decode()}'")

    if topic == global_command_topic:
        try:
            command_data = ujson.loads(msg.decode())
            cmd_type = command_data.get("command")

            if cmd_type == "start_recording":
                filename = command_data.get("filename")
                if not filename:
                    print("Error: 'start_recording' command missing \
                          'filename'.")
                    publish_status(b"error_missing_filename")
                    return
                start_adc_recording(filename)
                print("mqtt_callback: start_adc_recording initiated.")

            elif cmd_type == "stop_recording":
                stop_adc_recording()
                print("mqtt_callback: stop_adc_recording called.")

            elif cmd_type == "check_pico_connection":
                check_pico_connection()

            else:
                print("Unknown JSON command type:", cmd_type)
                publish_status(b"error_unknown_json_command")

        except ValueError:
            print(f"Received non-JSON message on global command topic: \
                  {msg.decode()}")
            publish_status(b"error_non_json_command")
        except Exception as e:
            print(f"Error processing command: {e}")
            sys.print_exception(e) # Print traceback for debugging
            publish_status(f"error_processing_command_{e}".encode())


# Publish status to MQTT broker
def publish_status(status_msg):
    try:
        if client:
            client.publish(status_topic, status_msg, retain=False, qos=0)
            print(f"Published status \
                  '{status_msg.decode()}' \
                    to \
                  '{status_topic.decode()}'")
    except Exception as e:
        print(f"Failed to publish status: {e}")
        sys.print_exception(e)


# Connect to MQTT broker
def connect_mqtt():
    global client

    client = MQTTClient(
        client_id=_PICO_ID.encode(),
        server=config_mqtt.server,
        port=config_mqtt.port,
        user=config_mqtt.username,
        password=config_mqtt.password,
        keepalive=7200,
        ssl=True,
        ssl_params={'server_hostname': config_mqtt.server}
    )

    client.set_callback(mqtt_callback)
    print(f"Connecting to MQTT broker \
          {config_mqtt.server}:{config_mqtt.port} \
            as client ID '{_PICO_ID}'...")

    try:
        client.connect()
        print("Connected to MQTT broker.")
        client.subscribe(global_command_topic)
        print(f"Subscribed to topic: '{global_command_topic.decode()}'")
        publish_status(b"booted_up")
    except OSError as e:
        print(f"MQTT connection failed: {e}")
        raise


# Main loop (runs on Core 0)
def main_loop():
    global client, recording_active, data_queue, sd_card_present
    reconnect_attempts = 0
    max_reconnect_attempts = 5
    wlan_local_ref = network.WLAN(network.STA_IF)

    try:
        connect_to_network()

        sync_time()

        # Mount SD card on startup, it will remain mounted unless error 
        # or script exit
        if not mount_sd_card():
            pass  # Continue even if SD card fails, but recording won't work

        connect_mqtt()

        last_status_publish_time = utime.time()
        status_publish_interval = 1

        # This loop keeps the Pico running and ready for commands
        while True:
            try:
                # Handle MQTT messages and maintain connection
                client.check_msg()

                core0_record_adc_data_frame()

                utime.sleep_us(500)  # Yield control frequently

                # Periodically publish status
                if utime.time() - last_status_publish_time > status_publish_interval:
                    with lock:
                        if recording_active:
                            publish_status(b"recording_active")
                        elif sd_card_present:
                            publish_status(b"idle_sd_ready")
                        else:
                            publish_status(b"idle_no_sd")
                    last_status_publish_time = utime.time()

                reconnect_attempts = 0

            except OSError as e:
                print(f"Network/MQTT error in main loop: {e}")
                # Reconnection logic handles most network errors,
                # allows loop to continue
                if reconnect_attempts < max_reconnect_attempts:
                    print(f"Attempting to reconnect... ({reconnect_attempts+1}/{max_reconnect_attempts})")
                    utime.sleep(5)
                    try:
                        if not wlan_local_ref.isconnected():
                            print("Wi-Fi disconnected. Reconnecting...")
                            wlan_local_ref.active(False)
                            utime.sleep(1)
                            wlan_local_ref.active(True)
                            wlan_local_ref.connect(config_wifi.ssid, config_wifi.password)
                            wifi_reconnect_wait = 10
                            while wifi_reconnect_wait > 0 and not wlan_local_ref.isconnected():
                                utime.sleep(1)
                                wifi_reconnect_wait -= 1
                            if not wlan_local_ref.isconnected():
                                print("Wi-Fi reconnect failed.")
                                # If Wi-Fi consistently fails,
                                # it's a critical error for connectivity
                                raise RuntimeError("WiFi reconnect failed")

                        client.connect()
                        print("Reconnected to MQTT broker.")
                        client.subscribe(global_command_topic)
                        publish_status(b"reconnected_idle")
                        reconnect_attempts = 0
                    except Exception as re:
                        print(f"Reconnect failed: {re}")
                        sys.print_exception(re)
                        reconnect_attempts += 1
                else:
                    print("Max reconnect attempts reached. Exiting main loop.")
                    break

            except Exception as e:
                print(f"Unexpected error in main loop: {e}")
                sys.print_exception(e)
                print("Exiting main loop due to unexpected error.")
                break

    # Catches initial setup failures like WiFi connect fail
    except RuntimeError as e:
        print(f"Initial setup failed: {e}")
        sys.print_exception(e)
    except KeyboardInterrupt:
        print("\nScript terminated by user (Ctrl+C)")
    finally:
        # This block now ONLY executes when the entire script is exiting 
        # (e.g., due to errors that break the loop, or KeyboardInterrupt)
        print("Cleaning up resources (on full script exit)...")
        # Signal recording thread to stop and wait briefly
        with lock:
            if recording_active:
                recording_active = False
                print("Signaling recording thread to stop...")
        # Give Core 1 a moment to finish writing any remaining data and exit
        utime.sleep(3)

        if sd_card_present:
            try:
                uos.umount("/sd")
                print("SD card unmounted.")
            except Exception as e:
                print(f"Error unmounting SD card: {e}")

        if client:
            try:
                client.disconnect()
                print("Disconnected from MQTT broker.")
            except Exception as e:
                print(f"Error disconnecting MQTT: {e}")

        # Deactivate WLAN on full script exit
        if 'wlan_local_ref' in locals() and wlan_local_ref.isconnected():
            wlan_local_ref.disconnect()
            print("Wi-Fi disconnected.")
        if 'wlan_local_ref' in locals():
            wlan_local_ref.active(False)
            print("Wi-Fi deactivated.")
        print("Cleanup complete.")


"""---EXECUTE MAIN LOOP---"""


if __name__ == "__main__":
    main_loop()
