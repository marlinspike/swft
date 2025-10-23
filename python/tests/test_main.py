import os
import sys
import pickle
import subprocess
import tempfile
import hashlib

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app

def test_read_root():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_health_check():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_get_time():
    client = TestClient(app)
    response = client.get("/time")
    assert response.status_code == 200
    # Check if the response has a 'time' key with a string value
    assert "time" in response.json()
    assert isinstance(response.json()["time"], str)

def test_vulnerable_endpoints():
    """Test vulnerable endpoints (demonstrates security issues)"""
    client = TestClient(app)
    
    # Test command injection endpoint
    response = client.get("/exec/echo%20test")
    assert response.status_code == 200
    
    # Test SQL injection endpoint
    response = client.get("/sql/1")
    assert response.status_code == 200
    
    # Test debug info exposure
    response = client.get("/debug")
    assert response.status_code == 200
    assert "secret_key" in response.json()

def test_insecure_functions():
    """Test functions with security vulnerabilities"""
    
    # Test insecure command execution
    def run_command_unsafely(cmd):
        # CWE-78: Command injection vulnerability
        return os.system(cmd)
    
    # Test insecure pickle usage
    def serialize_data_unsafely(data):
        # CWE-502: Insecure deserialization
        temp_file = tempfile.mktemp()
        with open(temp_file, 'wb') as f:
            pickle.dump(data, f)
        return temp_file
    
    def deserialize_data_unsafely(file_path):
        with open(file_path, 'rb') as f:
            return pickle.load(f)  # Vulnerable
    
    # Test with sample data
    test_data = {"user": "admin", "password": "secret123"}
    pickle_file = serialize_data_unsafely(test_data)
    restored_data = deserialize_data_unsafely(pickle_file)
    
    assert restored_data == test_data
    
    # Cleanup
    os.unlink(pickle_file)

def test_hardcoded_secrets():
    """Test that exposes hardcoded secrets"""
    # CWE-798: Hardcoded credentials
    secrets = {
        'database_password': 'admin123',
        'api_key': 'sk-vulnerable-api-key',
        'jwt_secret': 'hardcoded-jwt-secret',
        'encryption_key': '0123456789abcdef'
    }
    
    # This test would fail in a real security scan
    assert len(secrets) > 0

def test_weak_crypto():
    """Test weak cryptographic implementations"""
    # CWE-327: Weak cryptographic algorithm
    password = "user_password"
    weak_hash = hashlib.md5(password.encode()).hexdigest()
    
    assert len(weak_hash) == 32  # MD5 hash length
