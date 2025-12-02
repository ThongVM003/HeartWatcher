import asyncio
from bleak import BleakClient
import datetime
import pymongo
import os

# Heart Rate Service UUID (Standard Bluetooth SIG)
HEART_RATE_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
# Heart Rate Measurement Characteristic UUID
HEART_RATE_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

# Your Galaxy Watch MAC address
WATCH_ADDRESS = "E4:92:82:D2:70:D7"

class HeartRateMonitor:
    def __init__(self, db_client=None):
        self.db = db_client
        self.client = None
        self.running = False
        self.latest_bpm = 0
        
    def parse_heart_rate(self, sender, data: bytearray):
        """
        Parse heart rate data from BLE characteristic.
        First byte contains flags, second byte (or second+third) contains BPM.
        """
        # First byte is flags
        flags = data[0]
        # Check if heart rate value format is UINT16 (bit 0 of flags)
        hr_format = flags & 0x01
        
        if hr_format == 0:
            # Heart rate is UINT8 (8-bit)
            bpm = data[1]
        else:
            # Heart rate is UINT16 (16-bit)
            bpm = int.from_bytes(data[1:3], byteorder='little')
        
        self.latest_bpm = bpm
        print(f"Heart Rate: {bpm} BPM - {datetime.datetime.now()}")
        
        # Store in database
        if self.db is not None:
            bpm_stored = max(80, bpm)  # Keep the same min threshold as before
            self.db.insert_one({"bpm": bpm_stored, "timestamp": datetime.datetime.now()})
        
    async def connect_and_monitor(self):
        """
        Connect to the Galaxy Watch and start monitoring heart rate.
        Uses the same approach as the working lo.py script.
        """
        print(f"Connecting to {WATCH_ADDRESS}...")
        
        try:
            async with BleakClient(WATCH_ADDRESS) as client:
                print(f"✅ Connected to {client.address}")
                
                # Start notifications for heart rate measurements
                print("Starting heart rate notifications...")
                await client.start_notify(HEART_RATE_MEASUREMENT_UUID, self.parse_heart_rate)
                
                self.running = True
                print("❤️  Monitoring heart rate... (Press Ctrl+C to stop)")
                
                # Keep the connection alive
                while self.running and client.is_connected:
                    await asyncio.sleep(1)
                        
        except Exception as e:
            print(f"Connection failed: {e}")
            print("Tip: Make sure the watch is paired and in range.")
            self.running = False
    
    async def start(self):
        """Start the heart rate monitor."""
        await self.connect_and_monitor()
    
    def stop(self):
        """Stop the heart rate monitor."""
        self.running = False

async def main():
    """Main function for testing the heart rate monitor standalone."""
    monitor = HeartRateMonitor()
    await monitor.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped monitoring.")
