"""
Vulnerable code patterns for CVE testing with Trivy
This module intentionally contains security vulnerabilities for testing purposes
"""

import subprocess
import pickle
import os
import tempfile
import hashlib
import random
import sqlite3

# Import YAML safely to avoid import errors if not installed
try:
    import yaml
except ImportError:
    yaml = None

# Import cryptography safely
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
except ImportError:
    Cipher = algorithms = modes = default_backend = None

class VulnerableClass:
    """Class with multiple security vulnerabilities"""
    
    def __init__(self):
        self.secret_key = "hardcoded_secret_123"  # Hardcoded secret
        self.api_key = "sk-1234567890abcdef"      # Hardcoded API key
        
    def command_injection_vuln(self, user_input):
        """Vulnerable to command injection"""
        # CWE-78: OS Command Injection
        command = f"echo {user_input}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout
    
    def sql_injection_vuln(self, user_id):
        """Vulnerable to SQL injection"""
        # CWE-89: SQL Injection
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        
        # Vulnerable query construction
        query = f"SELECT * FROM users WHERE id = {user_id}"
        cursor.execute(query)
        return cursor.fetchall()
    
    def pickle_deserialization_vuln(self, data):
        """Vulnerable to insecure deserialization"""
        # CWE-502: Deserialization of Untrusted Data
        return pickle.loads(data)
    
    def yaml_load_vuln(self, yaml_data):
        """Vulnerable YAML loading"""
        # CWE-502: Using unsafe yaml.load
        if yaml:
            return yaml.load(yaml_data, Loader=yaml.Loader)  # Unsafe loader
        else:
            return "YAML not available"
    
    def weak_crypto(self, data):
        """Using weak cryptographic algorithms"""
        # CWE-327: Use of a Broken or Risky Cryptographic Algorithm
        
        # Weak hash algorithm
        weak_hash = hashlib.md5(data.encode()).hexdigest()
        
        # Weak encryption (if cryptography is available)
        if Cipher and algorithms and modes and default_backend:
            key = b'0123456789abcdef'  # Weak key
            iv = b'1234567890123456'   # Static IV
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            encrypted = encryptor.update(data.encode()) + encryptor.finalize()
            return weak_hash, encrypted
        else:
            return weak_hash, b"Cryptography not available"
    
    def path_traversal_vuln(self, filename):
        """Vulnerable to path traversal"""
        # CWE-22: Path Traversal
        file_path = f"/var/app/files/{filename}"
        with open(file_path, 'r') as f:
            return f.read()
    
    def insecure_temp_file(self):
        """Creates insecure temporary files"""
        # CWE-377: Insecure Temporary File
        temp_file = f"/tmp/temp_{random.randint(1000, 9999)}.txt"
        with open(temp_file, 'w') as f:
            f.write("sensitive data")
        return temp_file
    
    def weak_random(self):
        """Using weak random number generation"""
        # CWE-338: Use of Cryptographically Weak Pseudo-Random Number Generator
        return random.random()
    
    def hardcoded_credentials(self):
        """Returns hardcoded credentials"""
        # CWE-798: Use of Hard-coded Credentials
        database_config = {
            'host': 'localhost',
            'username': 'admin',
            'password': 'password123',  # Hardcoded password
            'api_secret': 'abc123def456'  # Hardcoded API secret
        }
        return database_config
    
    def debug_info_exposure(self, error):
        """Exposes sensitive debug information"""
        # CWE-209: Information Exposure Through Error Messages
        import traceback
        debug_info = {
            'error': str(error),
            'traceback': traceback.format_exc(),
            'locals': locals(),
            'globals': dict(globals())
        }
        return debug_info

# Global variables with sensitive data
DATABASE_PASSWORD = "admin123"
API_SECRET_KEY = "sk-proj-abc123def456"
JWT_SECRET = "super_secret_jwt_key"

def unsafe_eval(user_code):
    """Dangerous use of eval"""
    # CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code
    return eval(user_code)

def unsafe_exec(user_code):
    """Dangerous use of exec"""
    # CWE-95: Code Injection
    exec(user_code)

def insecure_http_request():
    """Makes insecure HTTP requests"""
    import requests
    # CWE-295: Improper Certificate Validation
    response = requests.get('https://api.example.com/data', verify=False)
    return response.text

# Example of using vulnerable dependencies
try:
    import django
    from django.conf import settings
    
    # Vulnerable Django configuration
    settings.configure(
        SECRET_KEY='django-insecure-hardcoded-key-123456789',  # Hardcoded secret
        DEBUG=True,  # Debug mode in production
        ALLOWED_HOSTS=['*'],  # Allow all hosts
    )
except ImportError:
    pass

# Weak SSL/TLS configuration
import ssl
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE