# modified from https://www.youtube.com/watch?v=eym8NpHr9Xw
# use web interface to control an LED asynchronously

import utime
import network
from machine import Pin
import uasyncio as asyncio # Ensure this is uasyncio, not just asyncio

ssid = 'TARDIS'
password = 'omniclimb'

# Global variables for LED and state
led = Pin('LED', Pin.OUT)
led.off()
led_state = False

# Placeholder for HTML content
default_html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Pico LED Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="icon" href="data:,">
    <style>
        body { font-family: sans-serif; text-align: center; margin-top: 50px; }
        .button { display: inline-block; padding: 10px 20px; margin: 10px; font-size: 1.2em;
                  text-decoration: none; color: white; background-color: #4CAF50;
                  border-radius: 5px; cursor: pointer; }
        .button-off { background-color: #f44336; }
    </style>
</head>
<body>
    <h1>Pico W LED Control</h1>
    <p>Current LED State: **ledState**</p>
    <p>
        <a href="/ledon" class="button">Turn On</a>
        <a href="/ledoff" class="button button-off">Turn Off</a>
    </p>
</body>
</html>"""

# WiFi Connection Function (synchronous)
def connect_to_network():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.config(pm = 0xa11140) # disabling power-save mode
    wlan.connect(ssid, password)

    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('waiting for connection... ' + str(max_wait))
        utime.sleep(1)

    if wlan.status() != 3:
        raise RuntimeError('network connection failed')
    else:
        print('wlan connected')
        status = wlan.ifconfig()
        pico_ip = status[0]
        print('ip = ' + pico_ip)
        return pico_ip, wlan

# Asynchronous Client Handler
async def serve_client(reader, writer):
    global led_state

    try:
        addr = writer.get_extra_info('peername')
        print(f"Client connected from {addr}")

        request_line = await reader.readline()
        request_str = request_line.decode('utf-8').strip()
        print(f"Request: {request_str}")

        # Read headers until empty line
        while True:
            header_line = await reader.readline()
            if header_line == b'\r\n':
                break

        request_url = request_str.split(' ')[1]

        response_status = b'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'
        current_html_content = default_html_content

        if request_url.find("/ledon") != -1:
            print("Turning LED ON")
            led_state = True
            led.on()
        elif request_url.find("/ledoff") != -1:
            print("Turning LED OFF")
            led_state = False
            led.off()
        elif request_url.find("/favicon.ico") != -1:
            response_status = b'HTTP/1.0 204 No Content\r\n\r\n'
            # No HTML content for 204 No Content
        else:
            pass

        # Load HTML content from file or use default
        try:
            with open("simpleled.html", "r") as f:
                current_html_content = f.read()
        except OSError:
            pass

        # Replace placeholder in HTML
        led_state_text = "OFF"
        if led_state:
            led_state_text = "ON"
        final_html_response = current_html_content.replace('**ledState**', led_state_text)

        # Write response to client
        writer.write(response_status)
        if response_status == b'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n':
            writer.write(final_html_response.encode('utf-8'))

        await writer.drain()

    except OSError as e:
        print(f"Connection error: {e}")
    except Exception as e:
        print(f"Error serving client: {e}")
    finally:
        writer.close()
        await writer.wait_closed()
        print(f"Client {addr} disconnected")

# Main Asynchronous Function
async def main():
    global wlan_obj
    print("Connecting to Network...")
    pico_ip, wlan_obj = connect_to_network()

    print("Setting up webserver...")
    # asyncio.start_server returns a Server object, use async with for clean shutdown
    server = await asyncio.start_server(serve_client, pico_ip, 80)
    print(f"Server started on http://{pico_ip}:80")

    # This keeps the main task running and allows the server to serve connections
    # When `main()` is cancelled (e.g., by KeyboardInterrupt),
    # `server.wait_closed()` will raise CancelledError, and the `async with server:`
    # block will ensure the server socket is properly closed.
    async with server:
        await server.wait_closed()

# Entry Point for the Script with Error Handling and Cleanup
if __name__ == "__main__":
    wlan_obj = None # Initialize wlan_obj to None
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user (Ctrl+C)")
    except Exception as e:
        print(f"An unexpected error occurred in main: {e}")
    finally:
        print("Attempting to clean up resources...")
        # In MicroPython's uasyncio, directly stopping the loop is often sufficient
        # combined with the `async with server:` block in `main()`.
        # `all_tasks()` is often not available.

        loop = asyncio.get_event_loop()
        try:
            # If the loop is still running (e.g., after an unexpected exception), stop it
            # This might raise RuntimeError if the loop isn't running or is already closed
            if loop.is_running():
                loop.stop()
                print("Event loop stopped.")
            
            # Close the loop
            if not loop.is_closed():
                loop.close()
                print("Event loop closed.")

        except Exception as e:
            print(f"Error during loop cleanup: {e}")

        # Disconnect Wi-Fi and turn off LED
        if wlan_obj and wlan_obj.isconnected():
            wlan_obj.disconnect()
            print("Wi-Fi disconnected.")
        if wlan_obj:
            wlan_obj.active(False)
            print("Wi-Fi deactivated.")
        led.off()
        print("LED turned off.")
        print("Cleanup complete.")