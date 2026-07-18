"""
Cursor on Target (CoT) message generation and formatting.

This module provides utilities for creating TAK-compatible CoT XML messages
following the Event schema defined in MIL-STD-2525 and CoT specifications.
"""

import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class CoTEvent:
    """Represents a Cursor on Target event."""
    
    uid: str
    event_type: str
    how: str
    lat: float
    lon: float
    hae: float = 0.0  # Height above ellipsoid
    ce: float = 9999999.0  # Circular error
    le: float = 9999999.0  # Linear error
    stale_minutes: int = 10
    remarks: Optional[str] = None
    callsign: Optional[str] = None
    detail: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate coordinates and set defaults."""
        if not -90 <= self.lat <= 90:
            raise ValueError(f"Invalid latitude: {self.lat}")
        if not -180 <= self.lon <= 180:
            raise ValueError(f"Invalid longitude: {self.lon}")
        if not self.uid:
            self.uid = str(uuid.uuid4())
    
    def to_xml(self) -> str:
        """
        Generate CoT XML message.
        
        Returns:
            str: XML string representation of the CoT event
        """
        now = datetime.utcnow()
        start_time = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        stale_time = (now + timedelta(minutes=self.stale_minutes)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        # Create root event element
        event = ET.Element("event", {
            "version": "2.0",
            "uid": self.uid,
            "type": self.event_type,
            "how": self.how,
            "time": start_time,
            "start": start_time,
            "stale": stale_time
        })
        
        # Add point element
        point = ET.SubElement(event, "point", {
            "lat": str(self.lat),
            "lon": str(self.lon),
            "hae": str(self.hae),
            "ce": str(self.ce),
            "le": str(self.le)
        })
        
        # Add detail element
        detail = ET.SubElement(event, "detail")
        
        # Add contact if callsign provided
        if self.callsign:
            contact = ET.SubElement(detail, "contact", {
                "callsign": self.callsign
            })
        
        # Add remarks if provided
        if self.remarks:
            remarks = ET.SubElement(detail, "remarks")
            remarks.text = self.remarks
        
        # Add custom detail fields
        if self.detail:
            self._add_detail_fields(detail, self.detail)
        
        # Convert to string
        return ET.tostring(event, encoding="unicode")
    
    def _add_detail_fields(self, parent: ET.Element, fields: Dict[str, Any]):
        """
        Recursively add custom detail fields to XML.
        
        Args:
            parent: Parent XML element
            fields: Dictionary of field names and values
        """
        for key, value in fields.items():
            if isinstance(value, dict):
                child = ET.SubElement(parent, key)
                self._add_detail_fields(child, value)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    child = ET.SubElement(parent, key)
                    if isinstance(item, dict):
                        self._add_detail_fields(child, item)
                    else:
                        child.text = str(item)
            else:
                child = ET.SubElement(parent, key)
                child.text = str(value)


class CoTTypes:
    """Common CoT event type definitions."""
    
    # Atoms (base types)
    FRIENDLY_GROUND = "a-f-G"
    HOSTILE_GROUND = "a-h-G"
    NEUTRAL_GROUND = "a-n-G"
    UNKNOWN_GROUND = "a-u-G"
    
    FRIENDLY_AIR = "a-f-A"
    HOSTILE_AIR = "a-h-A"
    
    FRIENDLY_SURFACE = "a-f-S"  # Maritime
    HOSTILE_SURFACE = "a-h-S"
    
    # Specific types
    FRIENDLY_GROUND_UNIT = "a-f-G-E-V"  # Equipment-Vehicle
    FRIENDLY_AIR_FIXED_WING = "a-f-A-M-F"  # Military-Fixed Wing
    FRIENDLY_SURFACE_SHIP = "a-f-S-N"  # Non-military
    
    # Sensor/SIGINT
    SENSOR_POINT = "b-m-p-s-p-loc"  # Sensor-Position-Location
    RF_EMITTER = "b-m-p-s-p-e"  # Sensor-Position-Emitter
    
    # Points of Interest
    GENERIC_POINT = "b-m-p-s-p"
    ALERT = "b-m-p-w-ALERT"
    
    # Geofences/Shapes
    GEOFENCE = "u-d-f"  # Draw-Feature
    
    @classmethod
    def is_valid(cls, event_type: str) -> bool:
        """Validate CoT event type format."""
        parts = event_type.split("-")
        return len(parts) >= 2 and parts[0] in ["a", "b", "u", "t"]


class CoTBuilder:
    """Fluent builder for CoT events."""
    
    def __init__(self):
        self._uid = None
        self._type = None
        self._how = "m-g"  # machine-generated (default)
        self._lat = None
        self._lon = None
        self._hae = 0.0
        self._ce = 9999999.0
        self._le = 9999999.0
        self._stale_minutes = 10
        self._remarks = None
        self._callsign = None
        self._detail = {}
    
    def uid(self, uid: str):
        """Set UID."""
        self._uid = uid
        return self
    
    def type(self, event_type: str):
        """Set event type."""
        if not CoTTypes.is_valid(event_type):
            raise ValueError(f"Invalid CoT type: {event_type}")
        self._type = event_type
        return self
    
    def how(self, how: str):
        """Set how (provenance)."""
        self._how = how
        return self
    
    def location(self, lat: float, lon: float, hae: float = 0.0):
        """Set location."""
        self._lat = lat
        self._lon = lon
        self._hae = hae
        return self
    
    def accuracy(self, ce: float, le: float):
        """Set accuracy (circular error, linear error)."""
        self._ce = ce
        self._le = le
        return self
    
    def stale(self, minutes: int):
        """Set stale time in minutes."""
        self._stale_minutes = minutes
        return self
    
    def callsign(self, callsign: str):
        """Set callsign."""
        self._callsign = callsign
        return self
    
    def remarks(self, remarks: str):
        """Set remarks."""
        self._remarks = remarks
        return self
    
    def add_detail(self, key: str, value: Any):
        """Add custom detail field."""
        self._detail[key] = value
        return self
    
    def build(self) -> CoTEvent:
        """Build the CoT event."""
        if not self._type:
            raise ValueError("Event type is required")
        if self._lat is None or self._lon is None:
            raise ValueError("Location (lat/lon) is required")
        
        return CoTEvent(
            uid=self._uid or str(uuid.uuid4()),
            event_type=self._type,
            how=self._how,
            lat=self._lat,
            lon=self._lon,
            hae=self._hae,
            ce=self._ce,
            le=self._le,
            stale_minutes=self._stale_minutes,
            remarks=self._remarks,
            callsign=self._callsign,
            detail=self._detail if self._detail else None
        )


def create_alert(
    lat: float,
    lon: float,
    title: str,
    message: str,
    uid: Optional[str] = None,
    stale_minutes: int = 60
) -> str:
    """
    Create a simple alert CoT message.
    
    Args:
        lat: Latitude
        lon: Longitude
        title: Alert title (becomes callsign)
        message: Alert message (becomes remarks)
        uid: Optional unique identifier
        stale_minutes: How long the alert is valid
    
    Returns:
        str: CoT XML string
    """
    event = CoTBuilder() \
        .uid(uid or str(uuid.uuid4())) \
        .type(CoTTypes.ALERT) \
        .how("m-g") \
        .location(lat, lon) \
        .callsign(title) \
        .remarks(message) \
        .stale(stale_minutes) \
        .build()
    
    return event.to_xml()


def create_marker(
    lat: float,
    lon: float,
    callsign: str,
    marker_type: str = CoTTypes.GENERIC_POINT,
    uid: Optional[str] = None,
    remarks: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a generic map marker.
    
    Args:
        lat: Latitude
        lon: Longitude
        callsign: Marker label
        marker_type: CoT type string
        uid: Optional unique identifier
        remarks: Optional remarks text
        metadata: Optional dictionary of custom fields
    
    Returns:
        str: CoT XML string
    """
    builder = CoTBuilder() \
        .uid(uid or str(uuid.uuid4())) \
        .type(marker_type) \
        .how("m-g") \
        .location(lat, lon) \
        .callsign(callsign) \
        .stale(30)
    
    if remarks:
        builder.remarks(remarks)
    
    if metadata:
        for key, value in metadata.items():
            builder.add_detail(key, value)
    
    return builder.build().to_xml()
