
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Configuration
DATA_DIR = Path("d:/QuMail/key_manager/data/pki")
PKI_PASSWORD = b"insecure-pki-password" # For demo purposes

def generate_key():
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

def save_key(key, filename, password=None):
    if password:
        encryption = serialization.BestAvailableEncryption(password)
    else:
        encryption = serialization.NoEncryption()
        
    with open(DATA_DIR / filename, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption
        ))

def save_cert(cert, filename):
    with open(DATA_DIR / filename, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

def create_root_ca():
    print("Generating Root CA...")
    key = generate_key()
    
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"QuantumState"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"QubitCity"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"QuMail Quantum Root CA"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"QuMail Root CA"),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.now(timezone.utc)
    ).not_valid_after(
        # 10 years
        datetime.now(timezone.utc) + timedelta(days=3650)
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=None), critical=True,
    ).sign(key, hashes.SHA256(), default_backend())
    
    save_key(key, "ca_key.pem", PKI_PASSWORD)
    save_cert(cert, "ca_cert.pem")
    return key, cert

def create_node_cert(name, ca_key, ca_cert):
    print(f"Generating certificate for {name}...")
    key = generate_key()
    
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"QuantumState"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"QubitCity"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"QuMail Network"),
        x509.NameAttribute(NameOID.COMMON_NAME, name),
    ])
    
    # SubjectAltName is required for modern TLS
    alt_names = [x509.DNSName(u"localhost"), x509.DNSName(u"127.0.0.1"), x509.DNSName(name)]
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        ca_cert.subject
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.now(timezone.utc)
    ).not_valid_after(
        datetime.now(timezone.utc) + timedelta(days=365)
    ).add_extension(
        x509.BasicConstraints(ca=False, path_length=None), critical=True,
    ).add_extension(
        x509.SubjectAlternativeName(alt_names), critical=False,
    ).sign(ca_key, hashes.SHA256(), default_backend())
    
    # We save node keys without password for automation ease (in this demo)
    # In production, these should be in HSM or encrypted
    save_key(key, f"{name}_key.pem", None) 
    save_cert(cert, f"{name}_cert.pem")

def main():
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True)
        
    ca_key, ca_cert = create_root_ca()
    
    # Create certs for our typical nodes
    create_node_cert("km-local", ca_key, ca_cert)
    create_node_cert("km-bob", ca_key, ca_cert)
    create_node_cert("km-alice", ca_key, ca_cert)
    
    print(f"\nPKI generated in {DATA_DIR}")
    print("Files:")
    for f in DATA_DIR.iterdir():
        print(f" - {f.name}")

if __name__ == "__main__":
    main()
