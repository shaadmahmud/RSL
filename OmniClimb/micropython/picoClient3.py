# Pico W MQTT Client for Global Data Recording Control

import utime
import network
import uos
import sdcard
import ujson
import _thread
import config_mqtt
import sys # For sys.print_exception
import ntptime

from machine import Pin, I2C, SPI # Pin is still needed for I2C/SPI
from umqtt.simple import MQTTClient
from utime import ticks_ms, ticks_diff
from ads1x15 import ADS1115
from array import array # Explicitly imported
from micropython import const

# --- UNIQUE IDENTIFIER FOR EACH PICO --- #
# !!! IMPORTANT: CHANGE THIS FOR EVERY PICO !!!
PICO_ID = 'pico1' # Example: "pico2", "living_room_pico", etc.

# --- MQTT Topics --- #
global_command_topic = b"pico/all/cmd" # All Picos listen to this for commands
status_topic = b"pico/" + PICO_ID.encode() + b"/status" # Each Pico publishes its status here

# --- Global Data Recording State & Shared Buffer --- #
recording_active = False
current_filename = ""

# Shared buffer for ADC data between Core 0 (sampling) and Core 1 (writing)
# This will hold completed 'frames' of data ready to be written.
# Using a list to hold 'array.array' objects (frames)
data_queue = []
lock = _thread.allocate_lock() # Protects access to data_queue and recording_active

# --- I2C & SPI Setup --- #
i2c = I2C(0, sda=Pin(16), scl=Pin(17), freq=400000) # I2C for ADS1115

# SPI for SD card (adjust baudrate as needed)
cs_pin = Pin(13, mode=Pin.OUT, value=1)
spi_sd = SPI(1, baudrate=40000000, sck=Pin(14), mosi=Pin(15), miso=Pin(12))

# --- Initialize ADS1115 and SD Card --- #
ads = ADS1115(i2c, address=0x48, gain=1) # Default ADS1115 address is 0x48 (72 decimal)
sd = sdcard.SDCard(spi=spi_sd, cs=cs_pin)
sd_card_present = False # Will be set to True if SD card mounts successfully

# --- Initialize Data Structures for ADC Sampling --- #
_SAMPLES_PER_FRAME = const(50) # Number of samples (rows) to capture in one frame buffer
_CHANNELS_PER_SAMPLE = const(5) # Number of columns: timestamp + 4 ADC channels
_SAMPLE_INTERVAL_MS = const(20) # Sampling period in ms
running_time_ms = 0 # running time initialized as 0 ms

# A single frame buffer to hold data before pushing to queue.
# 'h' type code for signed short (2 bytes), sufficient for 16-bit ADC data + timestamps
# Ensure it can hold all values from (timestamp, Vref, Vout_a301, Vout_a401, Vout_empty)
# We'll re-create this for each frame to manage memory if needed, or re-use.
# For simplicity, let's make it an array.array that holds all raw ints for one frame.
# This means it will be a 1D array, and we'll access elements by index within that.
# Total size: _SAMPLES_PER_FRAME * _CHANNELS_PER_SAMPLE elements.
# Example: frame_buffer[sample_idx * _CHANNELS_PER_SAMPLE + channel_offset]
frame_buffer_raw = array('h', (0 for _ in range(_SAMPLES_PER_FRAME * _CHANNELS_PER_SAMPLE)))


# --- Network Setup --- #
wlan = network.WLAN(network.STA_IF)

# --- MQTT Client Object (global) --- #
client = None

# --- Function to Synchronize the Pico Time --- #
def sync_time():
    print("Attempting NTP time sync...")
    try:
        ntptime.host = "pool.ntp.org" # Or a regional NTP server
        ntptime.settime()
        print("Time synced via NTP:", utime.localtime())
    except Exception as e:
        print(f"NTP time sync failed: {e}")

# --- Function to connect to Wi-Fi --- #
def connect_to_network():
    print("Performing soft reset of Wi-Fi interface...")
    if wlan.isconnected(): # Check if already connected
        wlan.disconnect() # Explicitly disconnect
        utime.sleep_ms(50) # Small delay to allow disconnect to process

    wlan.active(False) # Deactivate to clear state
    utime.sleep_ms(50) # Small delay
    wlan.active(True) # Reactivate for a fresh start
    print("Wi-Fi interface reset complete.\n")
    
    wlan.active(True)
    wlan.config(pm = 0xa11140) # disable power-save mode
    wlan.connect(config_mqtt.wifi_ssid, config_mqtt.wifi_password)

    max_wait = 20 # Increased wait time for robust connection
    print(f"Connecting to Wi-Fi '{config_mqtt.wifi_ssid}'...")
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

# --- Mount SD Card --- #
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

# --- ADC Recording Function (intended for Core 0 - main loop) --- #
# This function will be called repeatedly in the main loop while recording_active is True.
def core0_record_adc_data_frame():
    global recording_active, lock, sd_card_present, data_queue, frame_buffer_raw, running_time_ms

    # Check if recording is active *before* starting to fill a new frame.
    # If not active, return immediately.
    with lock: # Acquire lock to check recording_active as it's shared
        if not recording_active:
            #print("Core 0: Detected recording_active is FALSE. Returning.")
            return

    # Sample each channel for a full frame
    t_frame_start = ticks_ms() + running_time_ms
    
    # Loop through to fill the entire frame buffer without checking the flag within the loop
    for sample_idx in range(_SAMPLES_PER_FRAME):
        # timestamp = ticks_diff(ticks_ms(), t_frame_start) # Timestamp relative to frame start
        timestamp = ticks_ms()
        # running_time_ms = timestamp
        
        base_idx = sample_idx * _CHANNELS_PER_SAMPLE
        
        frame_buffer_raw[base_idx + 0] = timestamp
        frame_buffer_raw[base_idx + 1] = ads.read(rate=7, channel1=0) # Vref_val
        frame_buffer_raw[base_idx + 2] = ads.read(rate=7, channel1=1) # Vout_a301_val
        frame_buffer_raw[base_idx + 3] = ads.read(rate=7, channel1=2) # Vout_a401_val
        frame_buffer_raw[base_idx + 4] = ads.read(rate=7, channel1=3) # Vout_empty_val
        
        # Calculate time elapsed for this sample and determine sleep duration
        elapsed_sample_time = ticks_diff(ticks_ms(), timestamp)
        sleep_duration = _SAMPLE_INTERVAL_MS - elapsed_sample_time

        if sleep_duration > 0:
            utime.sleep_ms(sleep_duration)
        
    # --- IMPORTANT: Check recording_active *after* the entire frame has been filled ---
    # Only append the frame to the queue if recording is *still* active.
    # This means a stop command arriving during the frame collection will cause this
    # specific frame to be discarded, and the next call to this function will stop immediately.
    with lock: # Acquire lock to check recording_active before appending
        if recording_active: # Only append if the recording is still desired
            data_queue.append(array('h', frame_buffer_raw)) # Append a *copy* of the completed frame
            print(f"Core 0: Completed and queued a {len(frame_buffer_raw)//_CHANNELS_PER_SAMPLE}-sample frame.")
        else:
            # If recording_active became False while we were filling the buffer,
            # this frame is discarded, and the function will return on its next call.
            print("Core 0: Recording stopped during frame collection. Discarding this frame.")

# --- SD Card Writing Function (runs on Core 1) --- #
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
                        data_to_write_frame = data_queue.pop(0) # Get the oldest frame (array.array)
                
                if data_to_write_frame:
                    t_start_write = ticks_ms()
                    
                    # Transform the 1D array.array frame into CSV lines
                    lines = []
                    # core1_write2sd now assumes full frames due to core0_record_adc_data_frame change
                    for sample_idx in range(_SAMPLES_PER_FRAME):
                        base_idx = sample_idx * _CHANNELS_PER_SAMPLE
                        row_elements = [str(data_to_write_frame[base_idx + i]) for i in range(_CHANNELS_PER_SAMPLE)]
                        lines.append(','.join(row_elements))
                    
                    data_block_str = '\n'.join(lines) + '\n' # Add newline after each block

                    try:
                        f.write(data_block_str)
                        # f.flush() # Optional: force write to disk more often (might slow down)
                        print(f"Core 1: Wrote {len(data_to_write_frame)//_CHANNELS_PER_SAMPLE} samples to file.")
                    except OSError as e:
                        print(f"Core 1: Error writing to file {file_path}: {e}")
                        publish_status(f"recording_write_error_{e}".encode())
                        with lock: recording_active = False # Signal main loop to stop
                        break # Exit Core 1 loop on critical write error

                    t_write_duration = ticks_diff(ticks_ms(), t_start_write)
                    # print(f"Core 1: Wrote {len(data_to_write_frame)//_CHANNELS_PER_SAMPLE} samples in {t_write_duration} ms\n")
                else:
                    # No data in queue, check recording_active state
                    with lock:
                        if not recording_active and not data_queue:
                            # If recording is off AND queue is empty, then we can exit
                            print("Core 1: Recording stopped and queue empty. Exiting thread.")
                            break # Exit the thread loop
                    utime.sleep_ms(10) # Small delay if queue is empty to avoid busy-waiting

    except OSError as e:
        print(f"Core 1: Initial file open error for {file_path}: {e}")
        publish_status(f"recording_file_open_error_{e}".encode())
        with lock: recording_active = False # Force stop on file open error
    except Exception as e:
        print(f"Core 1: Unexpected error in write thread: {e}")
        sys.print_exception(e) # Print full traceback for debugging
        publish_status(f"recording_thread_error_{e}".encode())
        with lock: recording_active = False # Force stop on unexpected error
    finally:
        print("Core 1 (SD Write Thread) finished.")
        # Ensure recording_active is false and LED is off (handled by main loop too)
        with lock: recording_active = False
        publish_status(b"recording_stopped_core1_exit")


# --- Start Recording Command Handler --- #
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
        data_queue.clear() # CRITICAL: Ensure buffer is empty for new recording

        # Set recording_active to True *before* starting thread
        # This signals core0_record_adc_data_frame to start sampling immediately
        recording_active = True
        print(f"DEBUG: recording_active set to {recording_active} in start_adc_recording.")
        
        # Start Core 1 thread only once when recording starts
        # This will now pass the filename to core1_write2sd directly
        _thread.start_new_thread(core1_write2sd, (current_filename, ))
        
        print(f"Starting recording to {current_filename}")
        publish_status(b"recording_started")

# --- Stop Recording Command Handler --- #
def stop_adc_recording():
    global recording_active, lock
    print("stop_adc_recording called.")
    with lock:
        if not recording_active:
            print("No recording active. Ignoring stop command.")
            publish_status(b"no_recording_active")
            return
        
        recording_active = False # Signal both Core 0 sampling and Core 1 thread to stop
        print(f"DEBUG: recording_active set to {recording_active} in stop_adc_recording.")
        print("Stopping recording.")
        publish_status(b"recording_stopping_signal") # Signaled, Core 1 will send final "stopped"

# --- Check Pico Connection Handler --- #
def check_pico_connection():
    print("Received check connection command.")
    publish_status(b"connected")

# --- MQTT Message Callback Function --- #
def mqtt_callback(topic, msg):
    print(f"Received MQTT message on topic '{topic.decode()}': '{msg.decode()}'")

    if topic == global_command_topic:
        try:
            command_data = ujson.loads(msg.decode())
            cmd_type = command_data.get("command")

            if cmd_type == "start_recording":
                filename = command_data.get("filename")
                if not filename:
                    print("Error: 'start_recording' command missing 'filename'.")
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
            print(f"Received non-JSON message on global command topic: {msg.decode()}")
            publish_status(b"error_non_json_command")
        except Exception as e:
            print(f"Error processing command: {e}")
            sys.print_exception(e) # Print traceback for debugging
            publish_status(f"error_processing_command_{e}".encode())

# --- Function to publish status to the broker ---
def publish_status(status_msg):
    try:
        if client:
            client.publish(status_topic, status_msg, retain=False, qos=0)
            print(f"Published status '{status_msg.decode()}' to '{status_topic.decode()}'")
    except Exception as e:
        print(f"Failed to publish status: {e}")
        sys.print_exception(e) # Print traceback for debugging

# --- Function to connect to MQTT Broker ---
def connect_mqtt():
    global client

    client = MQTTClient(
        client_id=PICO_ID.encode(),
        server=config_mqtt.mqtt_server,
        port=config_mqtt.mqtt_port,
        user=config_mqtt.mqtt_username,
        password=config_mqtt.mqtt_password,
        keepalive=7200, # Long keepalive is good for cloud brokers
        ssl=True,
        ssl_params = {'server_hostname': config_mqtt.mqtt_server}
    )

    client.set_callback(mqtt_callback)
    print(f"Connecting to MQTT broker {config_mqtt.mqtt_server}:{config_mqtt.mqtt_port} as client ID '{PICO_ID}'...")

    try:
        client.connect()
        print("Connected to MQTT broker.")
        client.subscribe(global_command_topic)
        print(f"Subscribed to topic: '{global_command_topic.decode()}'")
        publish_status(b"booted_up")
    except OSError as e:
        print(f"MQTT connection failed: {e}")
        raise

# --- Main loop (runs on Core 0) --- #
def main_loop():
    global client, recording_active, data_queue
    reconnect_attempts = 0
    max_reconnect_attempts = 5
    wlan_local_ref = network.WLAN(network.STA_IF)

    try:
        connect_to_network()
        
        sync_time()
        
        if not mount_sd_card(): # Attempt to mount SD card on startup
            pass # Continue even if SD card fails, but recording won't work

        connect_mqtt()

        last_status_publish_time = utime.time()
        status_publish_interval = 30

        while True:
            try:
                # Handle MQTT messages and maintain connection
                # This needs to be called frequently to process incoming commands
                client.check_msg()

                # --- Core 0 Task: Sample ADC data if recording is active ---
                # This function will check recording_active itself
                core0_record_adc_data_frame()
                
                # A small sleep to yield control to other tasks on Core 0 (e.g., MQTT check)
                # and also give Core 1 a chance to run. Adjust as needed for sample rate.
                utime.sleep_us(250) # Yield control frequently

                # Periodically publish status
                if utime.time() - last_status_publish_time > status_publish_interval:
                    with lock: # Protect access to recording_active
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
                if reconnect_attempts < max_reconnect_attempts:
                    print(f"Attempting to reconnect... ({reconnect_attempts+1}/{max_reconnect_attempts})")
                    utime.sleep(5)
                    try:
                        if not wlan_local_ref.isconnected():
                            print("Wi-Fi disconnected. Reconnecting...")
                            wlan_local_ref.active(False)
                            utime.sleep(1)
                            wlan_local_ref.active(True)
                            wlan_local_ref.connect(config_mqtt.wifi_ssid, config_mqtt.wifi_password)
                            wifi_reconnect_wait = 10
                            while wifi_reconnect_wait > 0 and not wlan_local_ref.isconnected():
                                utime.sleep(1)
                                wifi_reconnect_wait -= 1
                            if not wlan_local_ref.isconnected():
                                print("Wi-Fi reconnect failed.")
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
                    print("Max reconnect attempts reached. Exiting.")
                    break

            except Exception as e:
                print(f"Unexpected error in main loop: {e}")
                sys.print_exception(e)
                break

    except RuntimeError as e:
        print(f"Initial setup failed: {e}")
        sys.print_exception(e)
    except KeyboardInterrupt:
        print("\nScript terminated by user (Ctrl+C)")
    finally:
        print("Cleaning up resources...")
        # Signal recording thread to stop and wait briefly
        with lock:
            if recording_active:
                recording_active = False # Signal the thread to stop
                print("Signaling recording thread to stop...")
        # Give Core 1 a moment to finish writing any remaining data and exit
        # This sleep is crucial to allow core1_write2sd to drain data_queue and exit
        utime.sleep(3) # Increased sleep time for Core 1 to clear its queue

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
        
        # Removed: led.off()
        
        if 'wlan_local_ref' in locals() and wlan_local_ref.isconnected():
            wlan_local_ref.disconnect()
            print("Wi-Fi disconnected.")
        if 'wlan_local_ref' in locals():
            wlan_local_ref.active(False)
            print("Wi-Fi deactivated.")
        print("Cleanup complete.")

# --- Start the main loop ---
if __name__ == "__main__":
    main_loop()
