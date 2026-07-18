# TAK Plugin Gateway

**Shared Python library for TAK-Server plugin integration.**

Provides:
- **CoT message generation** (XML formatting per MIL-STD-2525)
- **TAK-Server client** (mTLS, TCP, UDP, HTTP/HTTPS)
- **Health monitoring** utilities

Used by all TAK plugins in this ecosystem. Plugins vendor this library or install from PyPI.

---

## Installation

### From Source (Development)
```bash
git clone https://github.com/yourorg/tak-plugin-gateway
cd tak-plugin-gateway
pip install -e .
```

### From PyPI (Stable)
```bash
pip install takgateway
```

### Vendored in Plugin Repos
Many plugins vendor this library directly (copy `src/takgateway/` into their repo) to avoid external dependencies.

---

## Quick Start

### Generate a CoT Alert

```python
from takgateway import CoTBuilder, CoTTypes

# Build an alert message
cot_xml = (
    CoTBuilder()
    .type(CoTTypes.ALERT)
    .location(lat=37.7749, lon=-122.4194)
    .callsign("AMBER ALERT")
    .remarks("Silver Honda Civic, plate ABC123")
    .stale(60)  # Valid for 60 minutes
    .build()
    .to_xml()
)

print(cot_xml)
```

### Send to TAK-Server (mTLS)

```python
from takgateway import TAKServerConfig, TAKServerClient

config = TAKServerConfig(
    host="10.0.0.50",
    port=8089,
    protocol="tcp",
    use_tls=True,
    cert_path="/certs/client.pem",
    key_path="/certs/client-key.pem",
    ca_path="/certs/ca.pem"
)

with TAKServerClient(config) as client:
    success = client.send_cot(cot_xml)
    print(f"Sent: {success}")
```

### Environment Variable Configuration

```python
import os
from takgateway import create_client_from_env

# Set environment variables
os.environ["TAK_HOST"] = "10.0.0.50"
os.environ["TAK_PORT"] = "8089"
os.environ["TAK_PROTOCOL"] = "tcp"
os.environ["TAK_USE_TLS"] = "true"
os.environ["TAK_CERT_PATH"] = "/certs/client.pem"
os.environ["TAK_KEY_PATH"] = "/certs/client-key.pem"
os.environ["TAK_CA_PATH"] = "/certs/ca.pem"

# Create client from environment
client = create_client_from_env()
client.connect()
client.send_cot(cot_xml)
```

---

## CoT Types Reference

```python
from takgateway import CoTTypes

# Friendly/Hostile/Neutral
CoTTypes.FRIENDLY_GROUND      # "a-f-G"
CoTTypes.HOSTILE_AIR          # "a-h-A"
CoTTypes.NEUTRAL_GROUND       # "a-n-G"

# SIGINT
CoTTypes.SENSOR_POINT         # "b-m-p-s-p-loc"
CoTTypes.RF_EMITTER           # "b-m-p-s-p-e"

# Alerts
CoTTypes.ALERT                # "b-m-p-w-ALERT"

# Points of Interest
CoTTypes.GENERIC_POINT        # "b-m-p-s-p"
```

---

## Health Monitoring

```python
from takgateway import HealthMonitor

monitor = HealthMonitor()

# Register components
monitor.register("tak_server", "unknown")
monitor.register("external_api", "unknown")

# Update status
monitor.mark_healthy("tak_server", "Connected via mTLS")
monitor.mark_degraded("external_api", "High latency (500ms)")

# Get health report (for HTTP endpoint)
report = monitor.get_health_report()
# {
#   "status": "degraded",
#   "timestamp": "2026-07-18T23:15:00Z",
#   "uptime_seconds": 3600,
#   "components": { ... }
# }
```

---

## Certificate Setup (mTLS)

TAK-Server administrators generate client certificates:

```bash
# On TAK-Server
cd /opt/tak/certs
./makeCert.sh client my-plugin-name

# Copy to plugin host
scp my-plugin-name.pem user@plugin-host:/certs/client.pem
scp my-plugin-name-key.pem user@plugin-host:/certs/client-key.pem
scp ca.pem user@plugin-host:/certs/ca.pem
```

Plugin configuration references these paths:
```bash
TAK_CERT_PATH=/certs/client.pem
TAK_KEY_PATH=/certs/client-key.pem
TAK_CA_PATH=/certs/ca.pem
```

---

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Coverage
pytest tests/ --cov=takgateway --cov-report=html

# Linting
ruff check src/
black --check src/
mypy src/
```

---

## Architecture for Plugin Developers

### Standalone Plugin Pattern

Each plugin is a separate repository that imports `takgateway`:

```
your-plugin/
├── requirements.txt        # includes: takgateway>=1.0.0
├── docker-compose.yml      # standalone deployment
├── .env.template           # TAK-Server creds + plugin config
├── setup.sh                # guided setup script
├── src/
│   └── main.py             # from takgateway import CoTBuilder, TAKServerClient
└── README.md
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
CMD ["python", "src/main.py"]
```

### Environment Variables (Plugin .env)

```bash
# TAK-Server Connection (mTLS)
TAK_HOST=10.0.0.50
TAK_PORT=8089
TAK_PROTOCOL=tcp
TAK_USE_TLS=true
TAK_CERT_PATH=/certs/client.pem
TAK_KEY_PATH=/certs/client-key.pem
TAK_CA_PATH=/certs/ca.pem

# Plugin-Specific Config
PLUGIN_UPDATE_INTERVAL=300
PLUGIN_API_KEY=your-api-key-here
```

---

## Security Best Practices

1. **Never commit certificates** to Git (`.gitignore` all `.pem`, `.key`, `.crt` files)
2. **Use .env.template** (checked in) vs `.env` (gitignored, contains secrets)
3. **Validate cert paths** in setup scripts before starting services
4. **Set restrictive file permissions** on certs (`chmod 600 *.pem`)
5. **Rotate certificates** per your organization's policy
6. **Use Docker secrets** in production (not environment variables)

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make changes and add tests
4. Run linters: `ruff check . && black . && mypy src/`
5. Run tests: `pytest tests/ --cov`
6. Commit with clear messages
7. Push and open a pull request

---

## License

Apache License 2.0 - see [LICENSE](LICENSE) file.

---

## Support

- **Issues**: https://github.com/yourorg/tak-plugin-gateway/issues
- **Discussions**: https://github.com/yourorg/tak-plugin-gateway/discussions
- **Security**: See [SECURITY.md](SECURITY.md) for vulnerability reporting

---

## Related Projects

- [tak-plugin-sat-alerts](https://github.com/yourorg/tak-plugin-sat-alerts) - Satellite pass alerts
- [tak-plugin-amber-alert](https://github.com/yourorg/tak-plugin-amber-alert) - AMBER Alert integration
- [tak-plugin-crime-heatmap](https://github.com/yourorg/tak-plugin-crime-heatmap) - Crime heatmap overlays
- [Intercept SIGINT Platform](https://github.com/smittix/intercept) - Distributed SIGINT for TAK

---

**Built for operational security professionals.**  
Executive protection · Private security · SAR · Red team training
