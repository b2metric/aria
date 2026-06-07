# Oracle Instant Client Setup (Thick Mode)

ARIA uses Oracle thick mode for advanced features. This requires Oracle Instant Client.

## macOS ARM64 (Apple Silicon)

```bash
# 1. Download from Oracle (requires free account)
# https://www.oracle.com/database/technologies/instant-client/macos-arm64-downloads.html
# Get: instantclient-basic-macos.arm64-23.3.0.0.0.zip

# 2. Extract to /opt/oracle
sudo mkdir -p /opt/oracle
cd /opt/oracle
sudo unzip ~/Downloads/instantclient-basic-macos.arm64-23.3.0.0.0.zip

# 3. Create symlinks (macOS specific)
cd /opt/oracle/instantclient_23_3
ln -sf libclntsh.dylib.23.1 libclntsh.dylib

# 4. Add to .env
echo "ORACLE_CLIENT_LIB_DIR=/opt/oracle/instantclient_23_3" >> backend/.env
```

## macOS Intel (x86_64)

```bash
# Same as above but download x64 version:
# https://www.oracle.com/database/technologies/instant-client/macos-intel-x86-downloads.html
```

## Linux (x86_64)

```bash
# 1. Download
# https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html

# 2. Extract
sudo mkdir -p /opt/oracle
cd /opt/oracle  
sudo unzip instantclient-basic-linux.x64-23.3.0.0.0.zip

# 3. Set library path
echo "/opt/oracle/instantclient_23_3" | sudo tee /etc/ld.so.conf.d/oracle.conf
sudo ldconfig

# 4. Add to .env
echo "ORACLE_CLIENT_LIB_DIR=/opt/oracle/instantclient_23_3" >> backend/.env
```

## Docker (production)

The Dockerfile should include:

```dockerfile
# Oracle Instant Client
RUN apt-get update && apt-get install -y libaio1 && \
    mkdir -p /opt/oracle && \
    curl -o /tmp/instantclient.zip https://download.oracle.com/... && \
    unzip /tmp/instantclient.zip -d /opt/oracle && \
    rm /tmp/instantclient.zip && \
    echo "/opt/oracle/instantclient_23_3" > /etc/ld.so.conf.d/oracle.conf && \
    ldconfig

ENV ORACLE_CLIENT_LIB_DIR=/opt/oracle/instantclient_23_3
```

## Verification

```python
import oracledb
oracledb.init_oracle_client(lib_dir="/opt/oracle/instantclient_23_3")
print("Thick mode:", oracledb.is_thin_mode() == False)  # Should print True
```

## Fallback (Thin Mode)

If Instant Client is not available, oracledb falls back to thin mode automatically.
Thin mode works for most use cases but lacks:
- LDAP/OID authentication
- Kerberos authentication
- Some Oracle Net features (encryption, compression)
- BFILE data type support
