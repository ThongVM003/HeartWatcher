import asyncio
from bleak import BleakClient, BleakError

# This is the NEW address you confirmed works in bluetoothctl
ADDRESS = "E4:92:82:D2:70:D7"

# The UUID for Heart Rate Measurement (same as the one you selected manually)
HR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

def notification_handler(sender, data):
    """
    This function runs every time the watch sends a new value.
    It replicates the 'Value: 00 5c' output you saw.
    """
    # data[0] is the Flags byte (usually 00)
    # data[1] is the Heart Rate value (e.g., 5c = 92)
    
    if len(data) >= 2:
        bpm = data[1]
        print(f"❤️  Heart Rate: {bpm} BPM")
    else:
        print("Received empty data.")

async def main():
    print(f"Connecting to {ADDRESS}...")
    
    try:
        async with BleakClient(ADDRESS) as client:
            print(f"✅ Connected to {ADDRESS}")
            
            # This is the Python equivalent of 'notify on'
            await client.start_notify(HR_UUID, notification_handler)
            print("Listening for data... (Press Ctrl+C to stop)")
            
            # Keep the script running so we can keep receiving data
            while client.is_connected:
                await asyncio.sleep(1)

    except BleakError as e:
        print(f"Connection failed: {e}")
        print("Tip: Make sure the 'Heart for Bluetooth' app is still running on the watch.")
    except KeyboardInterrupt:
        print("Stopping script...")

if __name__ == "__main__":
    asyncio.run(main())