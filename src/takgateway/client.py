"""
TAK Server client for CoT message injection.

Supports multiple connection methods:
- TCP (raw sockets with optional TLS/mTLS)
- UDP (multicast or unicast)
- HTTP/HTTPS REST API (TAK Server 4.x+)
"""

import socket
import ssl
import logging
import time
from typing import Optional, Tuple
from pathlib import Path
import requests
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TAKServerConfig:
    """TAK Server connection configuration."""
    
    host: str
    port: int
    protocol: str = "tcp"  # tcp, udp, http, https
    
    # TLS/mTLS settings (for tcp/https)
    use_tls: bool = False
    cert_path: Optional[str] = None  # Client certificate
    key_path: Optional[str] = None   # Client private key
    ca_path: Optional[str] = None    # CA certificate
    verify_ssl: bool = True
    
    # HTTP API settings
    api_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    
    # Connection settings
    timeout: int = 10
    retry_attempts: int = 3
    retry_delay: int = 2
    
    def __post_init__(self):
        """Validate configuration."""
        if self.protocol not in ["tcp", "udp", "http", "https"]:
            raise ValueError(f"Unsupported protocol: {self.protocol}")
        
        if self.use_tls and self.protocol == "tcp":
            if not self.cert_path or not self.key_path:
                logger.warning("TLS enabled but no client cert/key provided - may use password auth")
        
        if self.protocol in ["http", "https"] and not (self.api_token or (self.username and self.password)):
            logger.warning("HTTP API requires either api_token or username/password")


class TAKServerClient:
    """Client for sending CoT messages to TAK Server."""
    
    def __init__(self, config: TAKServerConfig):
        self.config = config
        self._socket = None
        self._session = None  # For HTTP connections
        
        if config.protocol in ["http", "https"]:
            self._init_http_session()
    
    def _init_http_session(self):
        """Initialize HTTP session with auth."""
        self._session = requests.Session()
        
        if self.config.api_token:
            self._session.headers["Authorization"] = f"Bearer {self.config.api_token}"
        elif self.config.username and self.config.password:
            self._session.auth = (self.config.username, self.config.password)
        
        # TLS/mTLS for HTTPS
        if self.config.protocol == "https":
            if self.config.cert_path and self.config.key_path:
                self._session.cert = (self.config.cert_path, self.config.key_path)
            if self.config.ca_path:
                self._session.verify = self.config.ca_path
            elif not self.config.verify_ssl:
                self._session.verify = False
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def connect(self) -> bool:
        """
        Establish connection to TAK Server.
        
        Returns:
            bool: True if connected successfully
        """
        if self.config.protocol in ["http", "https"]:
            # HTTP is connectionless, just verify endpoint is reachable
            return self._verify_http_endpoint()
        elif self.config.protocol == "tcp":
            return self._connect_tcp()
        elif self.config.protocol == "udp":
            return self._connect_udp()
        
        return False
    
    def _verify_http_endpoint(self) -> bool:
        """Verify HTTP endpoint is reachable."""
        try:
            base_url = f"{self.config.protocol}://{self.config.host}:{self.config.port}"
            response = self._session.get(
                f"{base_url}/Marti/api/version/config",
                timeout=self.config.timeout
            )
            logger.info(f"TAK Server HTTP endpoint reachable: {response.status_code}")
            return response.status_code in [200, 401, 403]  # Even auth failures mean endpoint exists
        except Exception as e:
            logger.error(f"Failed to reach TAK Server HTTP endpoint: {e}")
            return False
    
    def _connect_tcp(self) -> bool:
        """Establish TCP connection with optional TLS."""
        try:
            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.timeout)
            
            # Wrap with TLS if needed
            if self.config.use_tls:
                context = ssl.create_default_context()
                
                if self.config.ca_path:
                    context.load_verify_locations(self.config.ca_path)
                    context.check_hostname = True
                else:
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE if not self.config.verify_ssl else ssl.CERT_REQUIRED
                
                if self.config.cert_path and self.config.key_path:
                    context.load_cert_chain(
                        certfile=self.config.cert_path,
                        keyfile=self.config.key_path
                    )
                
                sock = context.wrap_socket(
                    sock,
                    server_hostname=self.config.host if context.check_hostname else None
                )
            
            # Connect
            sock.connect((self.config.host, self.config.port))
            self._socket = sock
            logger.info(f"Connected to TAK Server via TCP{'S' if self.config.use_tls else ''}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to TAK Server via TCP: {e}")
            if self._socket:
                try:
                    self._socket.close()
                except:
                    pass
                self._socket = None
            return False
    
    def _connect_udp(self) -> bool:
        """Setup UDP socket."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.config.timeout)
            self._socket = sock
            logger.info(f"UDP socket ready for TAK Server")
            return True
        except Exception as e:
            logger.error(f"Failed to create UDP socket: {e}")
            return False
    
    def send_cot(self, cot_xml: str) -> bool:
        """
        Send CoT message to TAK Server.
        
        Args:
            cot_xml: CoT XML string
        
        Returns:
            bool: True if sent successfully
        """
        for attempt in range(self.config.retry_attempts):
            try:
                if self.config.protocol in ["http", "https"]:
                    success = self._send_http(cot_xml)
                elif self.config.protocol == "tcp":
                    success = self._send_tcp(cot_xml)
                elif self.config.protocol == "udp":
                    success = self._send_udp(cot_xml)
                else:
                    logger.error(f"Unsupported protocol: {self.config.protocol}")
                    return False
                
                if success:
                    return True
                
                # Retry logic
                if attempt < self.config.retry_attempts - 1:
                    logger.warning(f"Send failed, retrying in {self.config.retry_delay}s (attempt {attempt + 1}/{self.config.retry_attempts})")
                    time.sleep(self.config.retry_delay)
                    
                    # Reconnect if needed
                    if self.config.protocol in ["tcp", "udp"]:
                        self.disconnect()
                        self.connect()
                
            except Exception as e:
                logger.error(f"Error sending CoT (attempt {attempt + 1}/{self.config.retry_attempts}): {e}")
                if attempt < self.config.retry_attempts - 1:
                    time.sleep(self.config.retry_delay)
        
        return False
    
    def _send_http(self, cot_xml: str) -> bool:
        """Send via HTTP REST API."""
        try:
            base_url = f"{self.config.protocol}://{self.config.host}:{self.config.port}"
            response = self._session.post(
                f"{base_url}/Marti/api/cot",
                data=cot_xml,
                headers={"Content-Type": "application/xml"},
                timeout=self.config.timeout
            )
            
            if response.status_code in [200, 201, 202]:
                logger.debug(f"CoT sent via HTTP: {response.status_code}")
                return True
            else:
                logger.error(f"HTTP API returned {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"HTTP send failed: {e}")
            return False
    
    def _send_tcp(self, cot_xml: str) -> bool:
        """Send via TCP socket."""
        if not self._socket:
            logger.error("TCP socket not connected")
            return False
        
        try:
            # TAK expects CoT messages to be terminated with newline
            message = cot_xml.encode('utf-8')
            if not message.endswith(b'\n'):
                message += b'\n'
            
            self._socket.sendall(message)
            logger.debug(f"CoT sent via TCP ({len(message)} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"TCP send failed: {e}")
            return False
    
    def _send_udp(self, cot_xml: str) -> bool:
        """Send via UDP socket."""
        if not self._socket:
            logger.error("UDP socket not initialized")
            return False
        
        try:
            message = cot_xml.encode('utf-8')
            self._socket.sendto(message, (self.config.host, self.config.port))
            logger.debug(f"CoT sent via UDP ({len(message)} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"UDP send failed: {e}")
            return False
    
    def disconnect(self):
        """Close connection."""
        if self._socket:
            try:
                self._socket.close()
                logger.info("Disconnected from TAK Server")
            except Exception as e:
                logger.error(f"Error closing socket: {e}")
            finally:
                self._socket = None
        
        if self._session:
            try:
                self._session.close()
            except:
                pass
            self._session = None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


def create_client_from_env() -> TAKServerClient:
    """
    Create TAK Server client from environment variables.
    
    Expected environment variables:
    - TAK_HOST: Server hostname/IP (required)
    - TAK_PORT: Server port (required)
    - TAK_PROTOCOL: tcp, udp, http, https (default: tcp)
    - TAK_USE_TLS: true/false (default: false)
    - TAK_CERT_PATH: Path to client certificate
    - TAK_KEY_PATH: Path to client private key
    - TAK_CA_PATH: Path to CA certificate
    - TAK_VERIFY_SSL: true/false (default: true)
    - TAK_API_TOKEN: API token for HTTP auth
    - TAK_USERNAME: Username for HTTP basic auth
    - TAK_PASSWORD: Password for HTTP basic auth
    """
    import os
    
    host = os.getenv("TAK_HOST")
    port = os.getenv("TAK_PORT")
    
    if not host or not port:
        raise ValueError("TAK_HOST and TAK_PORT environment variables are required")
    
    config = TAKServerConfig(
        host=host,
        port=int(port),
        protocol=os.getenv("TAK_PROTOCOL", "tcp"),
        use_tls=os.getenv("TAK_USE_TLS", "false").lower() == "true",
        cert_path=os.getenv("TAK_CERT_PATH"),
        key_path=os.getenv("TAK_KEY_PATH"),
        ca_path=os.getenv("TAK_CA_PATH"),
        verify_ssl=os.getenv("TAK_VERIFY_SSL", "true").lower() == "true",
        api_token=os.getenv("TAK_API_TOKEN"),
        username=os.getenv("TAK_USERNAME"),
        password=os.getenv("TAK_PASSWORD")
    )
    
    return TAKServerClient(config)
