# 🔒 SETTLE Service - Encryption Implementation Guide

**Date:** December 7, 2025  
**Standards:** TLS 1.3 (in transit) + AES-256-GCM (at rest)  
**Compliance:** HIPAA, CCPA, SOC 2 Type II

---

## 🎯 **ENCRYPTION REQUIREMENTS**

SETTLE implements **defense-in-depth** encryption:

1. **TLS 1.3 Encryption in Transit** - All data moving between client and server
2. **AES-256-GCM Encryption at Rest** - All data stored in database and files

---

## 🔐 **PART 1: TLS 1.3 ENCRYPTION IN TRANSIT**

### **What is Protected**
- ✅ API requests/responses (all endpoints)
- ✅ Database connections (PostgreSQL/Supabase)
- ✅ External API calls (Stripe, AWS S3, etc.)
- ✅ WebSocket connections (if applicable)

### **Implementation Options**

---

### **Option A: Production Deployment (RECOMMENDED)**

#### **1. Using Reverse Proxy (Nginx/Caddy)**

**Nginx Configuration:**

```nginx
# /etc/nginx/sites-available/settle.truevow.law

server {
    listen 443 ssl http2;
    server_name settle.truevow.law;

    # TLS 1.3 Configuration
    ssl_protocols TLSv1.3;
    ssl_ciphers 'TLS_AES_256_GCM_SHA384:TLS_AES_128_GCM_SHA256:TLS_CHACHA20_POLY1305_SHA256';
    ssl_prefer_server_ciphers off;

    # SSL Certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/settle.truevow.law/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/settle.truevow.law/privkey.pem;

    # HSTS (HTTP Strict Transport Security)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Proxy to FastAPI application
    location / {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name settle.truevow.law;
    return 301 https://$server_name$request_uri;
}
```

**Setup Commands:**

```bash
# Install Nginx
sudo apt-get install nginx

# Install Certbot (Let's Encrypt)
sudo apt-get install certbot python3-certbot-nginx

# Obtain SSL Certificate
sudo certbot --nginx -d settle.truevow.law

# Test Nginx Configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Verify TLS 1.3
curl -vI https://settle.truevow.law 2>&1 | grep -i "tls"
```

**Caddy Configuration (Simpler Alternative):**

```caddy
# /etc/caddy/Caddyfile

settle.truevow.law {
    # Caddy automatically provisions TLS 1.3 certificates
    reverse_proxy localhost:8002
    
    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Frame-Options "DENY"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
    }
}
```

---

#### **2. Using Cloud Load Balancer**

**AWS Application Load Balancer (ALB):**

```yaml
# AWS CloudFormation template
Resources:
  SettleLoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Name: settle-alb
      Scheme: internet-facing
      SecurityGroups:
        - !Ref SettleSecurityGroup
      Subnets:
        - !Ref PublicSubnet1
        - !Ref PublicSubnet2

  SettleListener:
    Type: AWS::ElasticLoadBalancingV2::Listener
    Properties:
      LoadBalancerArn: !Ref SettleLoadBalancer
      Port: 443
      Protocol: HTTPS
      # TLS 1.3 Policy
      SslPolicy: ELBSecurityPolicy-TLS13-1-2-2021-06
      Certificates:
        - CertificateArn: !Ref SSLCertificate
      DefaultActions:
        - Type: forward
          TargetGroupArn: !Ref SettleTargetGroup
```

**GCP Cloud Load Balancer:**

```bash
# Create SSL certificate
gcloud compute ssl-certificates create settle-cert \
    --certificate=settle.truevow.law.crt \
    --private-key=settle.truevow.law.key

# Create HTTPS load balancer with TLS 1.3
gcloud compute target-https-proxies create settle-https-proxy \
    --ssl-certificates=settle-cert \
    --ssl-policy=settle-ssl-policy \
    --url-map=settle-url-map

# Create SSL policy with TLS 1.3
gcloud compute ssl-policies create settle-ssl-policy \
    --profile=MODERN \
    --min-tls-version=1.3
```

---

#### **3. Using Managed Platform (Easiest)**

**Fly.io (Recommended for SETTLE):**

```toml
# fly.toml

app = "settle-truevow"

[http_service]
  internal_port = 8002
  force_https = true
  auto_stop_machines = false
  auto_start_machines = true
  min_machines_running = 1

  # TLS 1.3 automatically configured by Fly.io
  # Certificate auto-provisioned and renewed
```

```bash
# Deploy with automatic TLS 1.3
fly deploy
```

**Heroku:**

```bash
# TLS 1.3 automatically configured
# Automatic SSL certificates via Let's Encrypt
heroku certs:auto:enable
```

**Railway:**

```yaml
# railway.toml
[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"

# TLS 1.3 automatically configured
# Custom domain with auto SSL
```

---

### **Option B: Development with Self-Signed Certificate**

**Generate Self-Signed Certificate:**

```bash
# Generate certificate and key
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout key.pem -out cert.pem -days 365 \
  -subj "/CN=localhost"
```

**Run FastAPI with TLS:**

```python
# app/main.py

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8002,
        ssl_keyfile="./key.pem",
        ssl_certfile="./cert.pem",
        ssl_version=3,  # TLS 1.3
        ssl_ciphers="TLS_AES_256_GCM_SHA384:TLS_AES_128_GCM_SHA256"
    )
```

**Or via command line:**

```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8002 \
  --ssl-keyfile ./key.pem \
  --ssl-certfile ./cert.pem
```

---

### **TLS 1.3 Verification**

**Test TLS 1.3 Support:**

```bash
# Using curl
curl -vI https://settle.truevow.law 2>&1 | grep "TLSv1.3"

# Using openssl
openssl s_client -connect settle.truevow.law:443 -tls1_3

# Using nmap
nmap --script ssl-enum-ciphers -p 443 settle.truevow.law

# Using SSL Labs (online test)
# https://www.ssllabs.com/ssltest/analyze.html?d=settle.truevow.law
```

**Expected Output:**

```
* TLSv1.3 (OUT), TLS handshake, Client hello (1):
* TLSv1.3 (IN), TLS handshake, Server hello (2):
* TLSv1.3 (IN), TLS handshake, Encrypted Extensions (8):
* TLSv1.3 (IN), TLS handshake, Certificate (11):
* TLSv1.3 (IN), TLS handshake, CERT verify (15):
* TLSv1.3 (IN), TLS handshake, Finished (20):
* SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384
```

---

## 🔐 **PART 2: AES-256-GCM ENCRYPTION AT REST**

### **What is Protected**
- ✅ Database records (PostgreSQL tables)
- ✅ Report files (PDF/JSON/HTML)
- ✅ Backup files
- ✅ Log files (if containing sensitive data)

---

### **Implementation Options**

---

### **Option A: Database-Level Encryption (PostgreSQL)**

#### **1. PostgreSQL Transparent Data Encryption (TDE)**

**Using pgcrypto extension:**

```sql
-- Enable pgcrypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create encrypted column
CREATE TABLE settle.settle_contributions_encrypted (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Encrypted fields (if needed for extra sensitive data)
    encrypted_data BYTEA,  -- Encrypted JSON blob
    
    -- Regular fields (already encrypted at disk level)
    jurisdiction TEXT NOT NULL,
    case_type TEXT NOT NULL,
    -- ... other fields
    
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Encrypt data (using AES-256-GCM via application)
-- Decrypt in application layer, not in database
```

**Note:** For most use cases, **disk-level encryption** (below) is sufficient and more performant.

---

#### **2. Disk-Level Encryption (RECOMMENDED)**

**PostgreSQL with LUKS (Linux Unified Key Setup):**

```bash
# Create encrypted partition
sudo cryptsetup luksFormat /dev/sdb1
sudo cryptsetup luksOpen /dev/sdb1 postgres_encrypted

# Format and mount
sudo mkfs.ext4 /dev/mapper/postgres_encrypted
sudo mkdir -p /var/lib/postgresql_encrypted
sudo mount /dev/mapper/postgres_encrypted /var/lib/postgresql_encrypted

# Configure PostgreSQL data directory
sudo -u postgres initdb -D /var/lib/postgresql_encrypted/data

# Configure encryption algorithm
# Edit /etc/crypttab
postgres_encrypted /dev/sdb1 none luks,cipher=aes-xts-plain64,size=256
```

**Verify encryption:**

```bash
# Check encryption status
sudo cryptsetup status postgres_encrypted

# Output should show:
# cipher:  aes-xts-plain64
# keysize: 256 bits
```

---

### **Option B: Cloud Database Encryption (RECOMMENDED)**

#### **1. Supabase (Built-in AES-256 Encryption)**

**Automatic encryption at rest:**

```python
# app/core/config.py

class Settings(BaseSettings):
    # Supabase automatically provides AES-256 encryption at rest
    SUPABASE_URL: str = "https://your-project.supabase.co"
    SUPABASE_KEY: str = "your-supabase-key"
    
    # Data is automatically encrypted at rest
    # No additional configuration needed
```

**Verification:**

Supabase uses AWS RDS with encryption enabled by default:
- **Algorithm:** AES-256-GCM
- **Key Management:** AWS KMS (Key Management Service)
- **Backup Encryption:** Automatic

**Supabase Security Settings:**

```bash
# Verify encryption in Supabase Dashboard
# Settings → Database → Encryption
# Should show: "Encryption at rest: Enabled (AES-256)"
```

---

#### **2. AWS RDS PostgreSQL**

```python
# Using boto3 to create encrypted RDS instance

import boto3

rds = boto3.client('rds')

response = rds.create_db_instance(
    DBInstanceIdentifier='settle-postgres',
    DBInstanceClass='db.t3.medium',
    Engine='postgres',
    MasterUsername='settle_admin',
    MasterUserPassword='secure_password',
    AllocatedStorage=100,
    
    # Enable encryption at rest (AES-256-GCM)
    StorageEncrypted=True,
    KmsKeyId='arn:aws:kms:us-west-2:123456789:key/your-kms-key',
    
    # Enable encryption in transit
    EnableIAMDatabaseAuthentication=True
)
```

**Verify RDS encryption:**

```bash
aws rds describe-db-instances \
  --db-instance-identifier settle-postgres \
  --query 'DBInstances[0].StorageEncrypted'

# Output: true
```

---

#### **3. GCP Cloud SQL PostgreSQL**

```bash
# Create encrypted Cloud SQL instance
gcloud sql instances create settle-postgres \
    --database-version=POSTGRES_15 \
    --tier=db-custom-2-8192 \
    --region=us-west2 \
    --storage-size=100GB \
    --storage-type=SSD \
    --storage-auto-increase \
    --database-flags=cloudsql.enable_pgaudit=on \
    --backup \
    --disk-encryption-key=projects/PROJECT_ID/locations/LOCATION/keyRings/KEY_RING/cryptoKeys/KEY

# Encryption is automatic with Cloud SQL
# Uses AES-256-GCM by default
```

---

### **Option C: File-Level Encryption (Reports, Backups)**

#### **1. Encrypt Report Files (PDF/JSON)**

**Using Python cryptography library:**

```python
# app/services/encryption.py

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
import os
import base64

class FileEncryption:
    """File encryption using AES-256-GCM"""
    
    def __init__(self, key: bytes = None):
        """
        Initialize encryption with AES-256-GCM key.
        
        Args:
            key: 32-byte encryption key (256 bits)
        """
        if key is None:
            # Load from environment or generate
            key = os.environ.get("ENCRYPTION_KEY")
            if key:
                key = base64.b64decode(key)
            else:
                # Generate new key (store securely!)
                key = AESGCM.generate_key(bit_length=256)
        
        self.aesgcm = AESGCM(key)
    
    def encrypt_file(self, plaintext: bytes, associated_data: bytes = None) -> tuple:
        """
        Encrypt file content using AES-256-GCM.
        
        Args:
            plaintext: File content to encrypt
            associated_data: Additional authenticated data (optional)
            
        Returns:
            Tuple of (ciphertext, nonce)
        """
        # Generate random nonce (12 bytes for GCM)
        nonce = os.urandom(12)
        
        # Encrypt
        ciphertext = self.aesgcm.encrypt(nonce, plaintext, associated_data)
        
        return ciphertext, nonce
    
    def decrypt_file(
        self, 
        ciphertext: bytes, 
        nonce: bytes, 
        associated_data: bytes = None
    ) -> bytes:
        """
        Decrypt file content using AES-256-GCM.
        
        Args:
            ciphertext: Encrypted content
            nonce: Nonce used during encryption
            associated_data: Additional authenticated data (must match encryption)
            
        Returns:
            Decrypted plaintext
        """
        plaintext = self.aesgcm.decrypt(nonce, ciphertext, associated_data)
        return plaintext


# Usage in report generation
from app.services.encryption import FileEncryption

async def save_encrypted_report(report_id: str, report_content: bytes):
    """Save report with AES-256-GCM encryption"""
    
    encryptor = FileEncryption()
    
    # Encrypt report
    associated_data = f"report_id:{report_id}".encode()
    ciphertext, nonce = encryptor.encrypt_file(report_content, associated_data)
    
    # Store encrypted report + nonce
    with open(f"reports/{report_id}.enc", "wb") as f:
        f.write(nonce + ciphertext)  # Prepend nonce for retrieval
    
    return True


async def load_encrypted_report(report_id: str) -> bytes:
    """Load and decrypt report"""
    
    encryptor = FileEncryption()
    
    # Read encrypted report
    with open(f"reports/{report_id}.enc", "rb") as f:
        data = f.read()
    
    # Extract nonce and ciphertext
    nonce = data[:12]  # First 12 bytes
    ciphertext = data[12:]  # Rest is ciphertext
    
    # Decrypt
    associated_data = f"report_id:{report_id}".encode()
    plaintext = encryptor.decrypt_file(ciphertext, nonce, associated_data)
    
    return plaintext
```

**Add to requirements.txt:**

```txt
cryptography==41.0.7
```

---

#### **2. Encrypt Files in AWS S3**

```python
# app/services/storage.py

import boto3
from botocore.config import Config

class SecureS3Storage:
    """S3 storage with AES-256-GCM encryption"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            config=Config(signature_version='s3v4')
        )
        self.bucket_name = os.environ.get("S3_BUCKET_NAME")
    
    def upload_encrypted_report(self, report_id: str, content: bytes):
        """
        Upload report with server-side encryption (AES-256-GCM).
        """
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=f"reports/{report_id}.pdf",
            Body=content,
            
            # Server-side encryption with AES-256-GCM
            ServerSideEncryption='AES256',
            
            # Or use AWS KMS for key management
            # ServerSideEncryption='aws:kms',
            # SSEKMSKeyId='arn:aws:kms:us-west-2:123456789:key/your-key',
            
            # Metadata
            Metadata={
                'report-id': report_id,
                'encryption': 'AES-256-GCM'
            }
        )
```

**Configure S3 bucket for encryption:**

```bash
# Enable default encryption on S3 bucket
aws s3api put-bucket-encryption \
    --bucket settle-reports \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            },
            "BucketKeyEnabled": true
        }]
    }'
```

---

## 🔑 **KEY MANAGEMENT**

### **Encryption Key Storage**

**Option A: Environment Variables (Development)**

```bash
# .env
ENCRYPTION_KEY="base64_encoded_256_bit_key_here"

# Generate key
python -c "from cryptography.hazmat.primitives.ciphers.aead import AESGCM; import base64; print(base64.b64encode(AESGCM.generate_key(bit_length=256)).decode())"
```

**Option B: AWS Secrets Manager (Production)**

```python
import boto3
import base64

def get_encryption_key():
    """Retrieve encryption key from AWS Secrets Manager"""
    
    client = boto3.client('secretsmanager', region_name='us-west-2')
    
    response = client.get_secret_value(SecretId='settle/encryption-key')
    
    secret = response['SecretString']
    key = base64.b64decode(secret)
    
    return key
```

**Option C: HashiCorp Vault (Production)**

```python
import hvac

def get_encryption_key():
    """Retrieve encryption key from Vault"""
    
    client = hvac.Client(url='https://vault.truevow.law')
    client.token = os.environ.get('VAULT_TOKEN')
    
    secret = client.secrets.kv.v2.read_secret_version(
        path='settle/encryption-key'
    )
    
    key = base64.b64decode(secret['data']['data']['key'])
    
    return key
```

---

## 📋 **CONFIGURATION SUMMARY**

### **Update Configuration**

```python
# app/core/config.py

class Settings(BaseSettings):
    # ... existing settings
    
    # Encryption Settings
    ENCRYPTION_ENABLED: bool = True
    ENCRYPTION_KEY: Optional[str] = None  # Base64-encoded 256-bit key
    ENCRYPTION_ALGORITHM: str = "AES-256-GCM"
    
    # TLS Settings
    TLS_ENABLED: bool = True
    TLS_MIN_VERSION: str = "1.3"
    SSL_CERT_PATH: Optional[str] = None
    SSL_KEY_PATH: Optional[str] = None
    
    # Key Management
    USE_KMS: bool = False  # Use AWS KMS
    KMS_KEY_ID: Optional[str] = None
    USE_SECRETS_MANAGER: bool = False
```

---

## ✅ **VERIFICATION CHECKLIST**

### **TLS 1.3 In Transit**
- [ ] SSL certificate installed (Let's Encrypt or commercial)
- [ ] TLS 1.3 protocol enabled (verified with curl/openssl)
- [ ] Weak ciphers disabled (only GCM ciphers)
- [ ] HSTS header configured
- [ ] HTTP redirects to HTTPS
- [ ] A+ rating on SSL Labs test

### **AES-256-GCM At Rest**
- [ ] Database encryption enabled (disk or column level)
- [ ] File storage encryption enabled (S3/local)
- [ ] Backup encryption enabled
- [ ] Encryption keys stored securely (Secrets Manager/Vault)
- [ ] Key rotation policy defined
- [ ] Encryption verified in production

---

## 🎯 **RECOMMENDED PRODUCTION SETUP**

### **For SETTLE Service:**

1. **TLS 1.3 In Transit:**
   - Use **Fly.io** or **AWS ALB** (automatic TLS 1.3)
   - Or Nginx reverse proxy with Let's Encrypt

2. **AES-256-GCM At Rest:**
   - Use **Supabase** (automatic AES-256 encryption)
   - Or AWS RDS with KMS encryption

3. **File Encryption:**
   - Use **AWS S3** with server-side encryption
   - Or client-side AES-256-GCM before upload

4. **Key Management:**
   - Use **AWS Secrets Manager** or **HashiCorp Vault**
   - Rotate keys every 90 days

---

## 📊 **COMPLIANCE VERIFICATION**

### **HIPAA Compliance**
- ✅ TLS 1.3 for data in transit
- ✅ AES-256-GCM for data at rest
- ✅ Encryption key management
- ✅ Audit logging enabled
- ✅ Access controls

### **SOC 2 Type II**
- ✅ Encryption end-to-end
- ✅ Key rotation policy
- ✅ Security monitoring
- ✅ Incident response plan

---

## 📞 **NEXT STEPS**

1. Choose deployment platform (Fly.io/AWS/GCP)
2. Configure TLS 1.3 (automatic or manual)
3. Enable database encryption (Supabase/RDS)
4. Implement file encryption (if needed)
5. Set up key management (Secrets Manager)
6. Verify encryption (SSL Labs + manual tests)
7. Document in compliance audit

---

**Last Updated:** December 7, 2025  
**Status:** Production-Ready Configuration  
**Standards:** TLS 1.3 + AES-256-GCM

