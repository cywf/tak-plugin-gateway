"""
Test CoT message generation.
"""

import pytest
from takgateway.cot import CoTBuilder, CoTTypes, create_alert, create_marker


def test_cot_builder_basic():
    """Test basic CoT message generation."""
    cot = (
        CoTBuilder()
        .uid("test-123")
        .type(CoTTypes.FRIENDLY_GROUND)
        .location(37.7749, -122.4194, 10.0)
        .callsign("TEST-1")
        .remarks("Test unit")
        .build()
    )
    
    assert cot.uid == "test-123"
    assert cot.event_type == CoTTypes.FRIENDLY_GROUND
    assert cot.lat == 37.7749
    assert cot.lon == -122.4194
    assert cot.hae == 10.0
    assert cot.callsign == "TEST-1"


def test_cot_xml_generation():
    """Test XML generation."""
    cot = (
        CoTBuilder()
        .type(CoTTypes.ALERT)
        .location(0.0, 0.0)
        .callsign("ALERT-1")
        .build()
    )
    
    xml = cot.to_xml()
    
    assert '<?xml' not in xml  # Should not have XML declaration
    assert 'version="2.0"' in xml
    assert 'type="b-m-p-w-ALERT"' in xml
    assert 'lat="0.0"' in xml
    assert 'lon="0.0"' in xml
    assert '<contact callsign="ALERT-1"' in xml


def test_create_alert_helper():
    """Test alert creation helper."""
    xml = create_alert(
        lat=37.7749,
        lon=-122.4194,
        title="Test Alert",
        message="This is a test"
    )
    
    assert 'type="b-m-p-w-ALERT"' in xml
    assert 'lat="37.7749"' in xml
    assert 'callsign="Test Alert"' in xml
    assert 'This is a test' in xml


def test_create_marker_helper():
    """Test marker creation helper."""
    xml = create_marker(
        lat=37.7749,
        lon=-122.4194,
        callsign="POI-1",
        marker_type=CoTTypes.GENERIC_POINT,
        remarks="Point of interest"
    )
    
    assert 'type="b-m-p-s-p"' in xml
    assert 'callsign="POI-1"' in xml
    assert 'Point of interest' in xml


def test_invalid_coordinates():
    """Test coordinate validation."""
    with pytest.raises(ValueError, match="Invalid latitude"):
        CoTBuilder().type(CoTTypes.FRIENDLY_GROUND).location(91.0, 0.0).build()
    
    with pytest.raises(ValueError, match="Invalid longitude"):
        CoTBuilder().type(CoTTypes.FRIENDLY_GROUND).location(0.0, 181.0).build()


def test_missing_required_fields():
    """Test missing required fields."""
    with pytest.raises(ValueError, match="Event type is required"):
        CoTBuilder().location(0.0, 0.0).build()
    
    with pytest.raises(ValueError, match="Location .* is required"):
        CoTBuilder().type(CoTTypes.FRIENDLY_GROUND).build()


def test_cot_type_validation():
    """Test CoT type validation."""
    assert CoTTypes.is_valid("a-f-G")
    assert CoTTypes.is_valid("b-m-p-s-p")
    assert not CoTTypes.is_valid("invalid")
    assert not CoTTypes.is_valid("x-y-z")


def test_custom_detail_fields():
    """Test adding custom detail fields."""
    cot = (
        CoTBuilder()
        .type(CoTTypes.SENSOR_POINT)
        .location(0.0, 0.0)
        .add_detail("frequency", "462.5625")
        .add_detail("power", "-45 dBm")
        .build()
    )
    
    xml = cot.to_xml()
    assert '<frequency>462.5625</frequency>' in xml
    assert '<power>-45 dBm</power>' in xml
