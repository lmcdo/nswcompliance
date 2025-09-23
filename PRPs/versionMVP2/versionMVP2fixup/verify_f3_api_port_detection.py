#!/usr/bin/env python3
"""
PRP-F3 Verification: API Port Detection Fix
Fixes and verifies API port detection for verification scripts
"""

import os
import sys
import json
import requests
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

class APIPortDetectionFix:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "prp": "F3",
            "objective": "API Port Detection Fix",
            "success": False,
            "actions_taken": [],
            "errors": [],
            "warnings": [],
            "statistics": {}
        }

        self.default_host = "localhost"
        self.common_ports = [8000, 8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009, 8010]

    def detect_api_port(self, host: str = None, port_range: tuple = None, timeout: int = 2) -> Optional[int]:
        """Detect which port the API server is running on"""
        host = host or self.default_host
        ports_to_check = list(range(port_range[0], port_range[1] + 1)) if port_range else self.common_ports

        print(f"Scanning for API server on {host}...")

        for port in ports_to_check:
            try:
                url = f"http://{host}:{port}/health"
                print(f"  Checking port {port}...", end="")

                response = requests.get(url, timeout=timeout)
                if response.status_code == 200:
                    # Verify it's actually our API by checking response content
                    try:
                        data = response.json()
                        if "status" in data and "processor_available" in data:
                            print(f" FOUND API SERVER")
                            return port
                    except:
                        pass
                print(f" No API")

            except requests.exceptions.RequestException:
                print(f" No response")
                continue
            except Exception as e:
                print(f" Error: {str(e)}")
                continue

        return None

    def check_environment_variables(self) -> Dict[str, Any]:
        """Check for API configuration in environment variables"""
        print("Checking environment variables...")

        env_config = {
            "API_HOST": os.environ.get("API_HOST"),
            "API_PORT": os.environ.get("API_PORT"),
            "API_URL": os.environ.get("API_URL"),
            "API_BASE_URL": os.environ.get("API_BASE_URL")
        }

        parsed_config = {}

        # Parse API_PORT
        if env_config["API_PORT"]:
            try:
                parsed_config["port"] = int(env_config["API_PORT"])
                print(f"  Found API_PORT: {parsed_config['port']}")
            except ValueError:
                self.results["warnings"].append(f"Invalid API_PORT value: {env_config['API_PORT']}")

        # Parse API_HOST
        if env_config["API_HOST"]:
            parsed_config["host"] = env_config["API_HOST"]
            print(f"  Found API_HOST: {parsed_config['host']}")

        # Parse full URLs
        for url_var in ["API_URL", "API_BASE_URL"]:
            if env_config[url_var]:
                try:
                    # Extract host and port from URL
                    from urllib.parse import urlparse
                    parsed = urlparse(env_config[url_var])
                    if parsed.hostname:
                        parsed_config["host"] = parsed.hostname
                    if parsed.port:
                        parsed_config["port"] = parsed.port
                    print(f"  Found {url_var}: {env_config[url_var]}")
                except Exception as e:
                    self.results["warnings"].append(f"Failed to parse {url_var}: {str(e)}")

        self.results["actions_taken"].append("Checked environment variables")
        return parsed_config

    def check_config_files(self) -> Dict[str, Any]:
        """Check for API configuration in config files"""
        print("Checking configuration files...")

        config_locations = [
            "config/api_config.json",
            "../config/api_config.json",
            "../../config/api_config.json",
            "api_config.json",
            ".env"
        ]

        for config_path in config_locations:
            if os.path.exists(config_path):
                print(f"  Found config file: {config_path}")
                try:
                    if config_path.endswith('.json'):
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                            api_config = config.get('api', {})
                            if api_config:
                                print(f"    API config: {api_config}")
                                self.results["actions_taken"].append(f"Loaded config from {config_path}")
                                return api_config
                    elif config_path.endswith('.env'):
                        # Simple .env parser
                        env_vars = {}
                        with open(config_path, 'r') as f:
                            for line in f:
                                if '=' in line and not line.strip().startswith('#'):
                                    key, value = line.strip().split('=', 1)
                                    env_vars[key] = value.strip('"\'')

                        api_config = {}
                        if 'API_PORT' in env_vars:
                            api_config['port'] = int(env_vars['API_PORT'])
                        if 'API_HOST' in env_vars:
                            api_config['host'] = env_vars['API_HOST']

                        if api_config:
                            print(f"    API config from .env: {api_config}")
                            self.results["actions_taken"].append(f"Loaded config from {config_path}")
                            return api_config

                except Exception as e:
                    self.results["warnings"].append(f"Failed to read config {config_path}: {str(e)}")

        return {}

    def test_api_endpoints(self, host: str, port: int) -> Dict[str, Any]:
        """Test various API endpoints to verify functionality"""
        print(f"Testing API endpoints on {host}:{port}...")

        base_url = f"http://{host}:{port}"
        endpoints_to_test = [
            ("/health", "Health check"),
            ("/docs", "API documentation"),
            ("/openapi.json", "OpenAPI schema"),
            ("/", "Root endpoint")
        ]

        test_results = {
            "base_url": base_url,
            "endpoints_tested": 0,
            "endpoints_working": 0,
            "endpoint_details": []
        }

        for endpoint, description in endpoints_to_test:
            try:
                url = base_url + endpoint
                response = requests.get(url, timeout=5)

                endpoint_result = {
                    "endpoint": endpoint,
                    "description": description,
                    "status_code": response.status_code,
                    "working": response.status_code < 400,
                    "response_size": len(response.content),
                    "content_type": response.headers.get("content-type", "")
                }

                print(f"  {endpoint} ({description}): {response.status_code} - {'OK' if response.status_code < 400 else 'FAILED'}")

                test_results["endpoints_tested"] += 1
                if endpoint_result["working"]:
                    test_results["endpoints_working"] += 1

                test_results["endpoint_details"].append(endpoint_result)

            except Exception as e:
                endpoint_result = {
                    "endpoint": endpoint,
                    "description": description,
                    "error": str(e),
                    "working": False
                }

                print(f"  {endpoint} ({description}): ERROR - {str(e)}")
                test_results["endpoints_tested"] += 1
                test_results["endpoint_details"].append(endpoint_result)

        success_rate = test_results["endpoints_working"] / test_results["endpoints_tested"] if test_results["endpoints_tested"] > 0 else 0
        test_results["success_rate"] = success_rate

        print(f"  Endpoint tests: {test_results['endpoints_working']}/{test_results['endpoints_tested']} working ({success_rate:.1%})")

        self.results["actions_taken"].append(f"Tested {test_results['endpoints_tested']} API endpoints")
        return test_results

    def create_api_detection_utility(self) -> bool:
        """Create reusable API detection utility function"""
        print("Creating API detection utility...")

        utility_code = '''#!/usr/bin/env python3
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
'''

        try:
            utility_path = "api_detection_util.py"
            with open(utility_path, 'w') as f:
                f.write(utility_code)

            print(f"  Created utility: {utility_path}")
            self.results["actions_taken"].append(f"Created API detection utility: {utility_path}")
            return True

        except Exception as e:
            self.results["errors"].append(f"Failed to create utility: {str(e)}")
            return False

    def test_utility_function(self) -> bool:
        """Test the created utility function"""
        print("Testing API detection utility...")

        try:
            # Import the utility we just created
            sys.path.insert(0, ".")
            import api_detection_util

            # Test detection
            result = api_detection_util.detect_api_server()
            if result:
                host, port = result
                print(f"  Utility detected API at {host}:{port}")

                # Test base URL function
                base_url = api_detection_util.get_api_base_url()
                print(f"  Base URL: {base_url}")

                self.results["actions_taken"].append("Successfully tested API detection utility")
                return True
            else:
                print("  Utility could not detect API server")
                self.results["warnings"].append("Utility could not detect API server")
                return False

        except Exception as e:
            self.results["errors"].append(f"Utility test failed: {str(e)}")
            return False

    def verify_statistics(self) -> Dict[str, Any]:
        """Get verification statistics"""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "detection_methods_tested": 0,
            "successful_detections": 0,
            "api_servers_found": [],
            "config_sources_found": []
        }

        # Test various detection methods
        methods = [
            ("Environment variables", self.check_environment_variables),
            ("Config files", self.check_config_files),
            ("Port scanning", lambda: {"detected_port": self.detect_api_port()})
        ]

        for method_name, method_func in methods:
            try:
                result = method_func()
                stats["detection_methods_tested"] += 1

                if result and any(result.values()):
                    stats["successful_detections"] += 1
                    stats["config_sources_found"].append(method_name)

            except Exception as e:
                self.results["warnings"].append(f"Detection method {method_name} failed: {str(e)}")

        # Try to detect actual API server
        detected_port = self.detect_api_port()
        if detected_port:
            stats["api_servers_found"].append({
                "host": self.default_host,
                "port": detected_port,
                "detected_at": datetime.now().isoformat()
            })

        return stats

    def execute_fix(self) -> bool:
        """Execute the complete API port detection fix"""
        print("Starting PRP-F3 API Port Detection Fix...")
        print("=" * 60)

        # Step 1: Check environment variables
        env_config = self.check_environment_variables()
        self.results["statistics"]["environment"] = env_config

        # Step 2: Check config files
        file_config = self.check_config_files()
        self.results["statistics"]["config_files"] = file_config

        # Step 3: Detect actual API server
        detected_port = self.detect_api_port()
        if detected_port:
            print(f"\nAPI server detected on port {detected_port}")

            # Test endpoints
            endpoint_tests = self.test_api_endpoints(self.default_host, detected_port)
            self.results["statistics"]["endpoint_tests"] = endpoint_tests
        else:
            print("\nNo API server detected")
            self.results["warnings"].append("No API server currently running")

        # Step 4: Create detection utility
        if not self.create_api_detection_utility():
            return False

        # Step 5: Test utility function
        if not self.test_utility_function():
            self.results["warnings"].append("Utility function test failed")

        # Step 6: Final verification
        final_stats = self.verify_statistics()
        self.results["statistics"]["final"] = final_stats

        # Determine success
        success = (
            len(self.results["errors"]) == 0 and
            (detected_port is not None or len(final_stats["config_sources_found"]) > 0)
        )

        self.results["success"] = success

        # Save results
        with open("verify_f3_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

        # Print summary
        print("\n" + "=" * 60)
        print("PRP-F3 API PORT DETECTION FIX RESULTS")
        print("=" * 60)

        if detected_port:
            print(f"API server detected: {self.default_host}:{detected_port}")
        else:
            print("API server: Not currently running")

        print(f"Detection methods tested: {final_stats.get('detection_methods_tested', 0)}")
        print(f"Successful detections: {final_stats.get('successful_detections', 0)}")
        print(f"Config sources found: {len(final_stats.get('config_sources_found', []))}")
        print(f"Actions taken: {len(self.results['actions_taken'])}")

        if self.results["errors"]:
            print("\nErrors:")
            for error in self.results["errors"]:
                print(f"  - {error}")

        if self.results["warnings"]:
            print("\nWarnings:")
            for warning in self.results["warnings"]:
                print(f"  - {warning}")

        print(f"\nPRP-F3 API PORT DETECTION FIX {'PASSED' if success else 'FAILED'}")

        return success

def main():
    """Main entry point"""
    fixer = APIPortDetectionFix()
    success = fixer.execute_fix()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()