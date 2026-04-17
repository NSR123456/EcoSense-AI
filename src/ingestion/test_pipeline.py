"""
Test script for Data Pipeline
"""

import asyncio
import random
from datetime import datetime, timedelta
from data_pipeline import ingest_sensor_data, SensorReading, get_recent_sensor_data, init_db

async def test_sensor_ingestion():
    """Test ingesting sample sensor data."""
    print("Initializing database...")
    await init_db()
    
    print("Testing sensor data ingestion...")

    # Sample buildings and sensors
    buildings = ["Academic Building", "Admin Block", "Library", "Auditorium"]
    sensors = ["energy_meter", "hvac_temp", "occupancy_sensor"]

    # Generate sample data for the last 24 hours
    base_time = datetime.utcnow() - timedelta(hours=24)

    for i in range(100):  # 100 readings
        building = random.choice(buildings)
        sensor = random.choice(sensors)

        # Generate realistic values
        if sensor == "energy_meter":
            value = random.uniform(100, 1000)  # kWh
            unit = "kWh"
        elif sensor == "hvac_temp":
            value = random.uniform(18, 30)  # Celsius
            unit = "C"
        else:  # occupancy
            value = random.randint(0, 500)  # people
            unit = "count"

        timestamp = base_time + timedelta(minutes=i*15)  # Every 15 minutes

        reading = SensorReading(
            building_id=building,
            sensor_type=sensor,
            value=value,
            unit=unit,
            timestamp=timestamp
        )

        result = await ingest_sensor_data(reading)
        print(f"Ingested: {result}")

    print("Sample data ingestion complete.")

async def test_data_retrieval():
    """Test retrieving recent data."""
    print("\nTesting data retrieval...")

    for building in ["Academic Building", "Admin Block"]:
        data = await get_recent_sensor_data(building, hours=24)
        print(f"{building}: {len(data)} readings")
        if data:
            print(f"Sample: {data[0]}")

if __name__ == "__main__":
    asyncio.run(test_sensor_ingestion())
    asyncio.run(test_data_retrieval())