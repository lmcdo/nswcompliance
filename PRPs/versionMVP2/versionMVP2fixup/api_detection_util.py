#!/usr/bin/env python3
"""
API Detection Utility
Automatically detects API server host and port for verification scripts
"""

import os
import json
import requests
from typing import Optional, Tuple
from urllib.parse import urlparse

def detect_api_server(
    default_host: str = "localhost",
    common_ports: list = None,
    timeout: int = 2
) -> Optional[Tuple[str, int]]:
    """
    Detect running API server host and port

    Returns:
        Tuple of (host, port) if found, None otherwise
    """
    if common_ports is None:
        common_ports = [8000, 8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009, 8010]

    # Check environment variables first
    env_host = os.environ.get("API_HOST", default_host)
    env_port = os.environ.get("API_PORT")

    if env_port:
        try:
            port = int(env_port)
            if test_api_connection(env_host, port, timeout):
                return (env_host, port)
        except ValueError:
            pass

    # Check config files
    config_host, config_port = load_api_config()
    if config_host and config_port:
        if test_api_connection(config_host, config_port, timeout):
            return (config_host, config_port)

    # Scan common ports
    for port in common_ports:
        if test_api_connection(env_host, port, timeout):
            return (env_host, port)

    return None

def test_api_connection(host: str, port: int, timeout: int = 2) -> bool:
    """Test if API server is running on given host:port"""
    try:
        response = requests.get(f"http://{host}:{port}/health", timeout=timeout)
        if response.status_code == 200:
            # Verify it's our API by checking response structure
            try:
                data = response.json()
                return "status" in data and "processor_available" in data
            except:
                return False
        return False
    except:
        return False

def load_api_config() -> Tuple[Optional[str], Optional[int]]:
    """Load API configuration from config files"""
    config_files = [
        "config/api_config.json",
        "../config/api_config.json",
        "../../config/api_config.json",
        "api_config.json"
    ]

    for config_path in config_files:
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    api_config = config.get('api', {})
                    host = api_config.get('host') or api_config.get('default_host')
                    port = api_config.get('port') or api_config.get('default_port')
                    if host and port:
                        return (host, int(port))
            except:
                continue

    return (None, None)

def get_api_base_url(default_host: str = "localhost") -> Optional[str]:
    """Get complete API base URL"""
    result = detect_api_server(default_host)
    if result:
        host, port = result
        return f"http://{host}:{port}"
    return None

if __name__ == "__main__":
    result = detect_api_server()
    if result:
        host, port = result
        print(f"API server detected at {host}:{port}")
        print(f"Base URL: http://{host}:{port}")
    else:
        print("No API server detected")
