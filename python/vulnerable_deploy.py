#!/usr/bin/env python3
"""
Vulnerable deployment script for CVE testing
This script contains multiple security vulnerabilities intentionally
"""

import os
import subprocess
import pickle
import tempfile
import hashlib

# Import optional dependencies safely
try:
    import yaml
except ImportError:
    yaml = None

try:
    import requests
    import urllib3
    # Disable SSL warnings (vulnerability)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    requests = urllib3 = None

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
except ImportError:
    Cipher = algorithms = modes = default_backend = None

class VulnerableDeployment:
    def __init__(self):
        # Hardcoded credentials
        self.db_password = "admin123"
        self.api_key = "sk-vulnerable-key-123"
        self.jwt_secret = "hardcoded-jwt-secret"
        
    def deploy_with_command_injection(self, app_name):
        """Vulnerable deployment function with command injection"""
        # CWE-78: Command Injection
        command = f"docker deploy --name {app_name}"
        os.system(command)  # Vulnerable to command injection
        
    def load_config_with_yaml_vuln(self, config_file):
        """Loads configuration using vulnerable YAML loader"""
        with open(config_file, 'r') as f:
            # CWE-502: Unsafe deserialization
            config = yaml.load(f)  # Should use yaml.safe_load
        return config
        
    def backup_with_pickle(self, data, backup_file):
        """Creates backup using insecure pickle"""
        with open(backup_file, 'wb') as f:
            # CWE-502: Insecure deserialization
            pickle.dump(data, f)
            
    def restore_from_pickle(self, backup_file):
        """Restores from pickle backup (vulnerable)"""
        with open(backup_file, 'rb') as f:
            return pickle.load(f)  # Dangerous deserialization
            
    def make_insecure_request(self, url):
        """Makes HTTP request without SSL verification"""
        # CWE-295: Improper certificate validation
        response = requests.get(url, verify=False)
        return response.text
        
    def weak_password_hash(self, password):
        """Uses weak hashing for passwords"""
        # CWE-327: Weak cryptographic algorithm
        return hashlib.md5(password.encode()).hexdigest()
        
    def encrypt_with_static_key(self, data):
        """Encrypts data with hardcoded key and IV"""
        # CWE-798: Hardcoded credentials
        key = b'0123456789abcdef'  # Static key
        iv = b'1234567890123456'   # Static IV
        
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        return encryptor.update(data.encode()) + encryptor.finalize()
        
    def create_temp_file_insecurely(self, content):
        """Creates temporary file with predictable name"""
        # CWE-377: Insecure temporary file
        temp_path = f"/tmp/deploy_{os.getpid()}.tmp"
        with open(temp_path, 'w') as f:
            f.write(content)
        os.chmod(temp_path, 0o777)  # World writable
        return temp_path
        
    def log_sensitive_info(self, user_data):
        """Logs sensitive information"""
        # CWE-532: Information exposure through log files
        print(f"User credentials: {user_data}")
        print(f"Database password: {self.db_password}")
        print(f"API key: {self.api_key}")
        
    def eval_user_input(self, user_code):
        """Dangerous evaluation of user input"""
        # CWE-95: Code injection
        return eval(user_code)
        
    def execute_user_code(self, user_script):
        """Executes user-provided code"""
        # CWE-95: Code injection
        exec(user_script)

def main():
    """Main deployment function with vulnerabilities"""
    
    # Initialize vulnerable deployment
    deployer = VulnerableDeployment()
    
    # Hardcoded configuration
    config = {
        'database_url': 'postgresql://admin:password123@db:5432/app',
        'redis_url': 'redis://admin:secret@redis:6379',
        'secret_key': 'hardcoded-secret-key',
        'debug': True,
        'allowed_hosts': ['*'],
    }
    
    # Create vulnerable configuration file
    temp_config = deployer.create_temp_file_insecurely(str(config))
    
    # Log sensitive information
    deployer.log_sensitive_info(config)
    
    # Make insecure HTTP requests
    try:
        deployer.make_insecure_request('https://api.example.com/deploy')
    except:
        pass
        
    # Use weak crypto
    encrypted_config = deployer.encrypt_with_static_key(str(config))
    
    # Vulnerable command execution
    app_name = input("Enter app name: ") if __name__ == "__main__" else "test-app"
    deployer.deploy_with_command_injection(app_name)
    
    print("Deployment completed (with vulnerabilities)")

if __name__ == "__main__":
    main()