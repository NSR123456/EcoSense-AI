"""
Data Ingestion Pipeline for Energy Management AI Platform

Handles real-time sensor data streams, historical warehousing, and multimodal inputs
with validation and anomaly detection at ingestion.
"""

import asyncio
import io
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field, validator
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
import uvicorn
import numpy as np

from src.core.analytics import detect_anomalies_with_ml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Configuration
# DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/energy_db"  # Update with actual credentials

# For development, use SQLite
DATABASE_URL = "sqlite+aiosqlite:///energy.db"

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Database Models
class Base(DeclarativeBase):
    pass

class SensorData(Base):
    __tablename__ = "sensor_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[str] = mapped_column(sa.String(50), index=True)
    sensor_type: Mapped[str] = mapped_column(sa.String(50))  # e.g., 'energy_meter', 'hvac_temp'
    value: Mapped[float]
    unit: Mapped[str] = mapped_column(sa.String(20))
    timestamp: Mapped[datetime] = mapped_column(sa.DateTime, index=True)
    source_type: Mapped[str] = mapped_column(sa.String(30), default="Manual_Upload")
    source_id: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    sensor_metadata: Mapped[Optional[str]] = mapped_column(sa.Text)  # JSON string for additional data

class BuildingMetadata(Base):
    __tablename__ = "building_metadata"

    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[str] = mapped_column(sa.String(50), unique=True, index=True)
    building_name: Mapped[Optional[str]] = mapped_column(sa.String(100))
    building_type: Mapped[Optional[str]] = mapped_column(sa.String(50))
    square_footage: Mapped[Optional[float]] = mapped_column(sa.Float)
    hvac_spec: Mapped[Optional[str]] = mapped_column(sa.Text)
    equipment_profile: Mapped[Optional[str]] = mapped_column(sa.Text)
    metadata: Mapped[Optional[str]] = mapped_column(sa.Text)

class TextLog(Base):
    __tablename__ = "text_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[str] = mapped_column(sa.String(50), index=True)
    log_type: Mapped[str] = mapped_column(sa.String(50))  # e.g., 'maintenance', 'error'
    content: Mapped[str] = mapped_column(sa.Text)
    timestamp: Mapped[datetime] = mapped_column(sa.DateTime, index=True)

class ImageData(Base):
    __tablename__ = "image_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[str] = mapped_column(sa.String(50), index=True)
    equipment_type: Mapped[str] = mapped_column(sa.String(50))
    image_path: Mapped[str] = mapped_column(sa.String(255))
    timestamp: Mapped[datetime] = mapped_column(sa.DateTime, index=True)
    analysis_result: Mapped[Optional[str]] = mapped_column(sa.Text)  # JSON string for AI analysis

# Pydantic Models for API
class SensorReading(BaseModel):
    building_id: str = Field(..., description="Building identifier")
    sensor_type: str = Field(..., description="Type of sensor (e.g., energy_meter)")
    value: float = Field(..., description="Sensor reading value")
    unit: str = Field(..., description="Unit of measurement")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    source_type: str = Field("Manual_Upload", description="Source of the data: Simulated, Edge, or Manual_Upload")
    source_id: Optional[str] = Field(None, description="Optional source identifier such as device id or upload batch id")
    metadata: Optional[Dict[str, Any]] = Field(default=None)

    @validator('value')
    def validate_value(cls, v):
        if not (-1000000 <= v <= 1000000):
            raise ValueError('Value out of reasonable range')
        return v

class TextLogEntry(BaseModel):
    building_id: str
    log_type: str
    content: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)

class BuildingMetadataInput(BaseModel):
    building_id: str
    building_name: Optional[str] = None
    building_type: Optional[str] = None
    square_footage: Optional[float] = None
    hvac_spec: Optional[str] = None
    equipment_profile: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

# Anomaly Detection
class AnomalyDetector:
    def __init__(self, contamination: float = 0.05, min_history: int = 12):
        self.history: Dict[str, List[float]] = {}
        self.contamination = contamination
        self.min_history = min_history

    def update_history(self, sensor_key: str, value: float, max_history: int = 100):
        if sensor_key not in self.history:
            self.history[sensor_key] = []
        self.history[sensor_key].append(value)
        if len(self.history[sensor_key]) > max_history:
            self.history[sensor_key].pop(0)

    def detect_anomaly(self, sensor_key: str, value: float, threshold: float = 3.0) -> bool:
        self.update_history(sensor_key, value)

        history = self.history[sensor_key]
        if len(history) < self.min_history + 1:
            return False

        labels = detect_anomalies_with_ml(
            history,
            contamination=self.contamination,
            window_size=self.min_history,
        )
        return bool(labels[-1])

anomaly_detector = AnomalyDetector()

# Data Pipeline Functions
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def ingest_sensor_data(reading: SensorReading) -> Dict[str, Any]:
    """Ingest sensor data with validation and anomaly detection."""
    sensor_key = f"{reading.building_id}_{reading.sensor_type}"

    # Detect anomaly
    is_anomaly = anomaly_detector.detect_anomaly(sensor_key, reading.value)

    # Store in database
    async with async_session() as session:
        db_reading = SensorData(
            building_id=reading.building_id,
            sensor_type=reading.sensor_type,
            value=reading.value,
            unit=reading.unit,
            timestamp=reading.timestamp,
            source_type=reading.source_type,
            source_id=reading.source_id,
            sensor_metadata=json.dumps(reading.metadata) if reading.metadata else None
        )
        session.add(db_reading)
        await session.commit()
        await session.refresh(db_reading)

    logger.info(f"Ingested sensor data: {reading.building_id} - {reading.sensor_type}: {reading.value}")

    return {
        "id": db_reading.id,
        "anomaly_detected": is_anomaly,
        "sensor_key": sensor_key
    }

async def ingest_text_log(log_entry: TextLogEntry):
    """Ingest text log data."""
    async with async_session() as session:
        db_log = TextLog(
            building_id=log_entry.building_id,
            log_type=log_entry.log_type,
            content=log_entry.content,
            timestamp=log_entry.timestamp
        )
        session.add(db_log)
        await session.commit()
        await session.refresh(db_log)

    logger.info(f"Ingested text log: {log_entry.building_id} - {log_entry.log_type}")

    return {"id": db_log.id}

async def ingest_image(file: UploadFile, building_id: str, equipment_type: str) -> Dict[str, Any]:
    """Ingest image data with basic validation."""
    # Save image to disk (in production, use cloud storage)
    upload_dir = Path("data/uploads/images")
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"{building_id}_{equipment_type}_{datetime.utcnow().isoformat()}.{file.filename.split('.')[-1]}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Store metadata in database
    async with async_session() as session:
        db_image = ImageData(
            building_id=building_id,
            equipment_type=equipment_type,
            image_path=str(file_path),
            timestamp=datetime.utcnow()
        )
        session.add(db_image)
        await session.commit()
        await session.refresh(db_image)

    logger.info(f"Ingested image: {building_id} - {equipment_type}")

    return {"id": db_image.id, "path": str(file_path)}

async def get_recent_sensor_data(building_id: str, hours: int = 24) -> List[Dict]:
    """Retrieve recent sensor data for analysis."""
    since = datetime.utcnow() - timedelta(hours=hours)

    async with async_session() as session:
        result = await session.execute(
            sa.select(SensorData).where(
                SensorData.building_id == building_id,
                SensorData.timestamp >= since
            ).order_by(SensorData.timestamp.desc())
        )
        readings = result.scalars().all()

    return [
        {
            "id": r.id,
            "sensor_type": r.sensor_type,
            "value": r.value,
            "unit": r.unit,
            "timestamp": r.timestamp.isoformat(),
            "source_type": r.source_type,
            "source_id": r.source_id,
            "metadata": json.loads(r.sensor_metadata) if r.sensor_metadata else None
        }
        for r in readings
    ]

async def ingest_building_metadata(metadata: BuildingMetadataInput) -> Dict[str, Any]:
    """Store or update building context metadata."""
    async with async_session() as session:
        existing = await session.execute(
            sa.select(BuildingMetadata).where(BuildingMetadata.building_id == metadata.building_id)
        )
        existing_obj = existing.scalars().first()

        if existing_obj:
            existing_obj.building_name = metadata.building_name
            existing_obj.building_type = metadata.building_type
            existing_obj.square_footage = metadata.square_footage
            existing_obj.hvac_spec = metadata.hvac_spec
            existing_obj.equipment_profile = json.dumps(metadata.equipment_profile) if metadata.equipment_profile else None
            existing_obj.metadata = json.dumps(metadata.metadata) if metadata.metadata else None
            session.add(existing_obj)
            await session.commit()
            await session.refresh(existing_obj)
            return {"id": existing_obj.id, "updated": True}

        db_building = BuildingMetadata(
            building_id=metadata.building_id,
            building_name=metadata.building_name,
            building_type=metadata.building_type,
            square_footage=metadata.square_footage,
            hvac_spec=metadata.hvac_spec,
            equipment_profile=json.dumps(metadata.equipment_profile) if metadata.equipment_profile else None,
            metadata=json.dumps(metadata.metadata) if metadata.metadata else None
        )
        session.add(db_building)
        await session.commit()
        await session.refresh(db_building)
        return {"id": db_building.id, "updated": False}

async def get_building_metadata(building_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve building metadata for a building."""
    async with async_session() as session:
        result = await session.execute(
            sa.select(BuildingMetadata).where(BuildingMetadata.building_id == building_id)
        )
        building = result.scalars().first()

    if not building:
        return None

    return {
        "building_id": building.building_id,
        "building_name": building.building_name,
        "building_type": building.building_type,
        "square_footage": building.square_footage,
        "hvac_spec": building.hvac_spec,
        "equipment_profile": json.loads(building.equipment_profile) if building.equipment_profile else None,
        "metadata": json.loads(building.metadata) if building.metadata else None
    }

async def ingest_batch_csv(file: UploadFile, source_type: str = "Manual_Upload") -> Dict[str, Any]:
    """Ingest a batch of sensor readings from a CSV upload."""
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        required_columns = {"building_id", "sensor_type", "value", "unit", "timestamp"}
        if not required_columns.issubset(set(df.columns)):
            raise ValueError(f"CSV must contain columns: {sorted(required_columns)}")

        ingestion_results = []
        for _, row in df.iterrows():
            reading = SensorReading(
                building_id=str(row["building_id"]),
                sensor_type=str(row["sensor_type"]),
                value=float(row["value"]),
                unit=str(row["unit"]),
                timestamp=pd.to_datetime(row["timestamp"]).to_pydatetime(),
                source_type=source_type,
                source_id=file.filename,
                metadata=row.get("metadata") and json.loads(row.get("metadata")) if pd.notna(row.get("metadata")) else None
            )
            result = await ingest_sensor_data(reading)
            ingestion_results.append(result)

        return {"ingested": len(ingestion_results), "details": ingestion_results}

    except Exception as e:
        logger.error(f"Batch CSV ingestion failed: {e}")
        raise

# FastAPI App
app = FastAPI(title="Energy Management Data Pipeline", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.post("/ingest/sensor")
async def api_ingest_sensor(reading: SensorReading):
    """API endpoint for sensor data ingestion."""
    try:
        result = await ingest_sensor_data(reading)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error ingesting sensor data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/text-log")
async def api_ingest_text_log(log_entry: TextLogEntry):
    """API endpoint for text log ingestion."""
    try:
        result = await ingest_text_log(log_entry)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error ingesting text log: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/building-metadata")
async def api_ingest_building_metadata(metadata: BuildingMetadataInput):
    """API endpoint for building metadata ingestion."""
    try:
        result = await ingest_building_metadata(metadata)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error ingesting building metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data/building-meta/{building_id}")
async def api_get_building_metadata(building_id: str):
    """API endpoint to retrieve building metadata."""
    try:
        metadata = await get_building_metadata(building_id)
        if metadata is None:
            raise HTTPException(status_code=404, detail="Building metadata not found")
        return {"status": "success", "data": metadata}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving building metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/image")
async def api_ingest_image(
    file: UploadFile = File(...),
    building_id: str = None,
    equipment_type: str = None
):
    """API endpoint for image ingestion."""
    if not building_id or not equipment_type:
        raise HTTPException(status_code=400, detail="building_id and equipment_type required")

    try:
        result = await ingest_image(file, building_id, equipment_type)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error ingesting image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/batch-csv")
async def api_ingest_batch_csv(
    file: UploadFile = File(...),
    source_type: str = "Manual_Upload"
):
    """API endpoint for CSV batch ingestion."""
    try:
        result = await ingest_batch_csv(file, source_type=source_type)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error ingesting batch CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data/sensor/{building_id}")
async def api_get_sensor_data(building_id: str, hours: int = 24):
    """API endpoint to retrieve recent sensor data."""
    try:
        data = await get_recent_sensor_data(building_id, hours)
        return {"status": "success", "data": data}
    except Exception as e:
        logger.error(f"Error retrieving sensor data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)