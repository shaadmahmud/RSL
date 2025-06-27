# Pico W MQTT Client for LED Control

import utime
import network
from machine import Pin
from umqtt.simple import MQTTClient # Ensure umqtt/simple.py is on your Pico
import ujson # For potential JSON messages, good practice
import config_mqtt
import ssl

# --- UNIQUE IDENTIFIER FOR EACH PICO ---
# !!! IMPORTANT: CHANGE THIS FOR EVERY PICO !!!
PICO_ID = 'pico1' # Example: "pico2", "living_room_pico", etc.

# --- MQTT Topics ---
# Topic where this Pico will listen for commands
global_command_topic = b"pico/all/cmd"
# Topic where this Pico will publish its recording status
status_topic = b"pico/" + PICO_ID.encode() + b"/status" # e.g., b"pico/pico1/status"

# --- Hardware Setup ---
led = Pin('LED', Pin.OUT) # Onboard LED
led.off() # Start with LED off
led_state = False # Track LED state locally

# --- Network Setup ---
wlan = network.WLAN(network.STA_IF)

# --- MQTT Client Object (global to be accessible in callback) ---
client = None # Initialize client variable

# --- Function to connect to Wi-Fi ---
def connect_to_network():
    wlan.active(True)
    wlan.config(pm = 0xa11140) # disable power-save mode
    wlan.connect(config_mqtt.wifi_ssid, config_mqtt.wifi_password)

    max_wait = 10
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

# --- MQTT Message Callback Function ---
def mqtt_callback(topic, msg):
    global led_state
    print(f"Received MQTT message on topic '{topic.decode()}': '{msg.decode()}'")

    if topic == command_topic:
        message_str = msg.decode().lower()
        if message_str == "on":
            led.on()
            led_state = True
            print("LED turned ON by MQTT command.")
            publish_status(b"on") # Confirm state change
        elif message_str == "off":
            led.off()
            led_state = False
            print("LED turned OFF by MQTT command.")
            publish_status(b"off") # Confirm state change
        else:
            print("Unknown command:", message_str)

# --- Function to publish LED status ---
def publish_status(status_msg):
    try:
        client.publish(status_topic, status_msg, retain=False, qos=0)
        print(f"Published status '{status_msg.decode()}' to '{status_topic.decode()}'")
    except Exception as e:
        print(f"Failed to publish status: {e}")

# --- Function to connect to MQTT Broker ---
def connect_mqtt():
    global client
    
    client = MQTTClient(
        client_id=PICO_ID.encode(), # Unique client ID for the broker
        server = config_mqtt.mqtt_server,
        port = config_mqtt.mqtt_port,
        user = config_mqtt.mqtt_username, # No username if public broker
        password = config_mqtt.mqtt_password, # No password if public broker
        keepalive = 7200, # Send PINGREQ every 60 seconds to keep connection alive
        ssl = True,
        ssl_params = {'server_hostname': config_mqtt.mqtt_server}
    )
    
    client.set_callback(mqtt_callback) # Set the message callback
    print(f"Connecting to MQTT broker {config_mqtt.mqtt_server}:{config_mqtt.mqtt_port} as client ID '{PICO_ID}'...")
    client.connect()
    print("Connected to MQTT broker.")
    client.subscribe(global_command_topic) # --- ADDED: Subscribe to global command topic ---
    print(f"Subscribed to topics: '{global_command_topic.decode()}'")
    publish_status(b"booted_up")

# --- Main loop ---
def main_loop():
    global client, led_state
    reconnect_attempts = 0
    max_reconnect_attempts = 5

    try:
        connect_to_network() # Connect to Wi-Fi first
        pico_ip = wlan.ifconfig()[0] # Get IP after connection

        connect_mqtt() # Connect to MQTT broker

        last_publish_time = utime.time()
        status_publish_interval = 30 # Publish status every 30 seconds

        while True:
            try:
                # Check for new MQTT messages
                # This must be called periodically to receive messages and keep connection alive
                client.check_msg()

                # Periodically publish LED status to confirm alive and current state
                if utime.time() - last_publish_time > status_publish_interval:
                    publish_status(b"on" if led_state else b"off")
                    last_publish_time = utime.time()

                utime.sleep(1) # Small delay to yield control and avoid busy-waiting
                reconnect_attempts = 0 # Reset attempts on successful operation

            except OSError as e: # Common for network errors (disconnects)
                print(f"Network/MQTT error: {e}")
                if reconnect_attempts < max_reconnect_attempts:
                    print(f"Attempting to reconnect... ({reconnect_attempts+1}/{max_reconnect_attempts})")
                    utime.sleep(5) # Wait before retrying
                    try:
                        client.connect() # Try to reconnect
                        print("Reconnected to MQTT broker.")
                        client.subscribe(command_topic) # Resubscribe
                        publish_status(b"reconnected")
                        reconnect_attempts = 0
                    except Exception as re:
                        print(f"Reconnect failed: {re}")
                        reconnect_attempts += 1
                else:
                    print("Max reconnect attempts reached. Exiting.")
                    break # Exit main loop if persistent issues

            except Exception as e: # Catch other potential errors
                print(f"Unexpected error in main loop: {e}")
                break # Exit main loop on unexpected error

    except RuntimeError as e: # Catch network connection failures at startup
        print(f"Initial setup failed: {e}")
    except KeyboardInterrupt:
        print("\nScript terminated by user (Ctrl+C)")
    finally:
        print("Cleaning up resources...")
        if client:
            try:
                client.disconnect()
                print("Disconnected from MQTT broker.")
            except Exception as e:
                print(f"Error disconnecting MQTT: {e}")
        led.off()
        if wlan.isconnected():
            wlan.disconnect()
            print("Wi-Fi disconnected.")
        wlan.active(False)
        print("Wi-Fi deactivated.")
        print("Cleanup complete.")

# --- Start the main loop ---
if __name__ == "__main__":
    main_loop()