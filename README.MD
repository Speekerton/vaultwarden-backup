# Vaultwarden Backup Script

Automated backup solution for Vaultwarden that creates both encrypted archives and KeePassXC databases. Supports local storage (perfect for NFS) with optional cloud sync.

## Testing Status

WIP

## DISCLAIMER

Modified and Intended for personal use only.  
Use at your own risk.  
I am no expert. Always go through the code and verify.  
I have used AI to help save my time. But I ensure AI does not edit my files i.e. I verify every snippet it generates.  
If you feel there can be improvements feel free to send in PR or raise issues but I reserve the rights to merge them or work on the issues when I get the time.

## My Setup

Proxmox 8.4.13  
Vaultwarden Debian LXC  
Recommend to get the lxc setup script from [Proxmox Helper Scripts Community](https://community-scripts.github.io/ProxmoxVE/) but always go through the scripts before install.

## Forked From and Special Thanks to

[LazyMechanic/vaultwarden-backup](https://github.com/LazyMechanic/vaultwarden-backup)

## Features

- **Dual backup formats**: Encrypted tar.gz archives + KeePassXC .kdbx files
- **Zero downtime**: Uses SQLite online backup (service never stops)
- **Secure**: No passwords exposed in process lists
- **Optional Remotes**: Works with empty remote configuration
- **Integrity verification**: MD5/SHA1 checksums for all backups
- **Automated cleanup**: Configurable retention policy
- **Systemd integration**: Automated scheduling with timer

## Prerequisites

### Required Tools

Install these tools on your system (Mine is debian):  
**NPM sufferred multiple breaches at the time this README updated (2025-09-19). Ensure no packages and dependencies are affected**

#### Ubuntu/Debian

```bash
# Update package lists
sudo apt update && sudo apt upgrade -y

# Install core system tools
sudo apt install sqlite3 gnupg tar python3 python3-pip python3-venv python3-lxml curl

# Install Node.js and npm for Bitwarden CLI
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install nodejs

# Install Bitwarden CLI
sudo npm install -g @bitwarden/cli

# Install rclone (optional - only for cloud remotes)
sudo apt install rclone
# OR use official installer: curl https://rclone.org/install.sh | sudo bash

# Verify all dependencies
sqlite3 --version && gpg --version && tar --version && python3 --version && pip3 --version && systemctl --version && bw --version
python3 -c "import lxml; print('python3-lxml: OK')"
```

#### RHEL/CentOS

```bash
# Enable EPEL repository (required for some packages)
sudo yum install epel-release

# Install core system tools
sudo yum install sqlite gnupg2 tar python3 python3-pip curl

# Install python3-lxml
sudo yum install python3-lxml

# Install Node.js and npm for Bitwarden CLI
curl -fsSL https://rpm.nodesource.com/setup_lts.x | sudo bash -
sudo yum install nodejs

# Install Bitwarden CLI
sudo npm install -g @bitwarden/cli

# Install rclone (optional - only for cloud remotes)
sudo yum install rclone
# OR use official installer: curl https://rclone.org/install.sh | sudo bash

# Verify all dependencies
sqlite3 --version && gpg2 --version && tar --version && python3 --version && pip3 --version && systemctl --version && bw --version
python3 -c "import lxml; print('python3-lxml: OK')"
```

#### Fedora

```bash
# Install core system tools
sudo dnf install sqlite gnupg2 tar python3 python3-pip python3-lxml curl

# Install Node.js and npm for Bitwarden CLI
curl -fsSL https://rpm.nodesource.com/setup_lts.x | sudo bash -
sudo dnf install nodejs

# Install Bitwarden CLI
sudo npm install -g @bitwarden/cli

# Install rclone (optional - only for cloud remotes)
sudo dnf install rclone
# OR use official installer: curl https://rclone.org/install.sh | sudo bash

# Verify all dependencies
sqlite3 --version && gpg2 --version && tar --version && python3 --version && pip3 --version && systemctl --version && bw --version
python3 -c "import lxml; print('python3-lxml: OK')"
```

#### Alpine

```bash
# Install core system tools
sudo apk add sqlite gnupg tar python3 py3-pip py3-lxml curl openrc nodejs npm

# Install Bitwarden CLI
sudo npm install -g @bitwarden/cli

# Install rclone (optional - only for cloud remotes)
sudo apk add rclone
# OR use official installer: curl https://rclone.org/install.sh | sudo bash

# Verify all dependencies
sqlite3 --version && gpg --version && tar --version && python3 --version && pip3 --version && rc-service --version && bw --version
python3 -c "import lxml; print('python3-lxml: OK')"
```

#### Manual Node.js Installation (if you prefer this way)

```bash
# Download and install Node.js manually
wget https://nodejs.org/dist/v18.17.0/node-v18.17.0-linux-x64.tar.xz
sudo tar -xJf node-v18.17.0-linux-x64.tar.xz -C /usr/local --strip-components=1

# Add to PATH (add to ~/.bashrc for persistence)
export PATH="/usr/local/bin:$PATH"

# Verify installation
node --version && npm --version

# Install Bitwarden CLI
sudo npm install -g @bitwarden/cli
```

### Vaultwarden API Access

1. **Enable admin panel** in your Vaultwarden instance
2. **Create API key**:
   - Go to your Vaultwarden admin panel
   - Navigate to "Users"
   - Find your user account
   - Click "Create API Key"
   - Save the Client ID and Client Secret

## Installation

### 1. Download and Install

```bash
# Clone repository
sudo git clone https://github.com/Speekerton/vaultwarden-backup.git /opt/vaultwarden-backup
cd /opt/vaultwarden-backup

# Run installation script
sudo ./install.sh
```

This will:

- Install Python dependencies in a virtual environment
- Copy systemd service/timer files
- Create `/etc/vaultwarden-backup/.env` configuration file

### 2. Configure Environment

Edit the configuration file:

```bash
sudo nano /etc/vaultwarden-backup/.env

# Configure rclone remotes via `rclone config`
# Configure bw server via `bw config server <URL>`
# Configure environment variables in `.env` file
# Adjust the OnCalendar field in /etc/systemd/system/vaultwarden-backup.timer if needed
```

**Required settings:**

```bash
CLIENT_ID="your_bitwarden_client_id"
CLIENT_SECRET="your_bitwarden_client_secret"
DATA_DIR="/opt/vaultwarden/data"
BACKUPS_DIR="/var/backups"
BACKUPS_LAST_KEEP=30
MASTER_PASSWORD="your_vault_master_password"
VAULTWARDEN_URL="https://vault.yourdomain.com"

# For local-only backups (NFS setup)
REMOTES=""

# Optional: For cloud sync
# REMOTES="gdrive:vaultwarden-backups dropbox:backups"
# SYNC_ATTEMPTS=3
```

### 3. Set Permissions (Optional but Recommended for security purposes)

```bash
# Secure the configuration file
sudo chmod 600 /etc/vaultwarden-backup/.env
sudo chown root:root /etc/vaultwarden-backup/.env

# Create backups directory
sudo mkdir -p /var/backups
sudo chmod 755 /var/backups
```

## Manual Testing

### Test Individual Components

**1. Test Bitwarden CLI access:**

```bash
# Set environment
export BW_CLIENTID="your_client_id"
export BW_CLIENTSECRET="your_client_secret"

# Test login
bw config server https://vault.yourdomain.com
bw login --apikey
bw sync
bw logout
```

**2. Test backup script manually:**

```bash
# Run backup with verbose logging
cd /opt/vaultwarden-backup
sudo .venv/bin/python src/main.py -v

# Check for successful completion
echo $?  # Should output 0 for success
```

**3. Verify backup contents:**

```bash
# List created backups
ls -la /var/backups/

# Check latest backup contents
LATEST_BACKUP=$(ls -t /var/backups/ | head -n1)
ls -la "/var/backups/$LATEST_BACKUP"

# Should contain:
# - arch.tar.gz.gpg (encrypted archive)
# - passwords.kdbx (KeePass database)
```

**4. Test decryption:**

```bash
cd "/var/backups/$LATEST_BACKUP"

# Decrypt archive (will prompt for password)
gpg --decrypt arch.tar.gz.gpg > arch.tar.gz

# Extract and verify contents
tar -tzf arch.tar.gz
# Should show: arch/data/ arch/vaultwarden.json

# Test KeePass database
file passwords.kdbx
# Should show: passwords.kdbx: Keepass password database
```

### Troubleshooting Manual Tests

**Common issues:**

1. **"Command not found: bw"**

   ```bash
   # Install Bitwarden CLI
   npm install -g @bitwarden/cli
   ```

2. **"Permission denied" errors**

   ```bash
   # Check Vaultwarden data directory permissions
   sudo ls -la /opt/vaultwarden/data/
   
   # Ensure backup script can read Vaultwarden data
   sudo chmod 755 /opt/vaultwarden/data/
   ```

3. **"Database is locked" errors**

   ```bash
   # Check if Vaultwarden is running
   sudo systemctl status vaultwarden
   
   # The script uses online backup, this shouldn't happen
   # If it does, check SQLite WAL mode
   sudo sqlite3 /opt/vaultwarden/data/db.sqlite3 "PRAGMA journal_mode;"
   ```

4. **"Export failed" errors**

   ```bash
   # Test Bitwarden CLI manually
   export BITWARDENCLI_APPDATA_DIR="/etc/vaultwarden-backup"
   bw config server https://vault.yourdomain.com
   bw login --apikey
   bw unlock  # Enter master password
   bw export --format json  # Should output JSON
   ```

## Automated Setup

### 1. Configure Systemd Timer

Check the timer schedule:

```bash
sudo cat /etc/systemd/system/vaultwarden-backup.timer
```

Default runs daily at 5:00 AM. To change:

```bash
sudo nano /etc/systemd/system/vaultwarden-backup.timer

# Change OnCalendar line, examples:
# OnCalendar=*-*-* 02:00:00    # Daily at 2 AM
# OnCalendar=*-*-* */6:00:00   # Every 6 hours
# OnCalendar=Sun *-*-* 03:00:00 # Weekly on Sunday at 3 AM
```

### 2. Enable and Start Service

```bash
# Reload systemd after any changes
sudo systemctl daemon-reload

# Enable timer to start on boot
sudo systemctl enable vaultwarden-backup.timer

# Start timer immediately
sudo systemctl start vaultwarden-backup.timer

# Check timer status
sudo systemctl status vaultwarden-backup.timer
sudo systemctl list-timers vaultwarden-backup*
```

### 3. Monitor Service

```bash
# View recent logs
sudo journalctl -u vaultwarden-backup.service -f

# View timer logs
sudo journalctl -u vaultwarden-backup.timer

# Test service manually
sudo systemctl start vaultwarden-backup.service

# Check service status
sudo systemctl status vaultwarden-backup.service
```

## Cloud Storage (Optional)

If you want to sync backups to cloud storage:

### 1. Install and Configure rclone

```bash
# Install rclone
curl https://rclone.org/install.sh | sudo bash

# Configure cloud storage
sudo rclone config

# Test configuration
sudo rclone lsd your-remote:
```

### 2. Update Configuration

```bash
sudo nano /etc/vaultwarden-backup/.env

# Add your remotes
REMOTES="gdrive:vaultwarden-backups dropbox:backups"
SYNC_ATTEMPTS=3
```

### 3. Test Cloud Sync

```bash
# Test manual sync
sudo rclone sync /var/backups gdrive:vaultwarden-backups --dry-run

# Run actual sync
sudo rclone sync /var/backups gdrive:vaultwarden-backups
```

## Backup Verification

### Regular Verification Tasks

**1. Monthly restore test:**

```bash
# Create test directory
mkdir ~/vaultwarden-restore-test
cd ~/vaultwarden-restore-test

# Copy latest backup
LATEST=$(ls -t /var/backups/ | head -n1)
cp "/var/backups/$LATEST"/* .

# Test decryption
gpg --decrypt arch.tar.gz.gpg > arch.tar.gz

# Test KeePass database
# Try opening passwords.kdbx with KeePassXC
```

**2. Check backup integrity:**

```bash
# Verify checksums in logs
sudo journalctl -u vaultwarden-backup.service | grep -E "(MD5|SHA1)"

# Check backup sizes are reasonable
du -sh /var/backups/*
```

### Backup Contents

Each backup contains:

**Encrypted Archive (`arch.tar.gz.gpg`):**

- SQLite database (`db.sqlite3`)
- Configuration file (`config.json`)
- RSA keys (`rsa_key.*`)
- File attachments (`attachments/`)
- Send attachments (`sends/`)

**KeePass Database (`passwords.kdbx`):**

- All vault entries in KeePass format
- Organized by folders
- Compatible with KeePassXC

## Security Notes

- Master password is never stored in command history or process lists
- Temporary files are automatically cleaned up
- Configuration file should have 600 permissions if setup
- Consider encrypting the backup storage location
- Regularly test restore procedures
- Keep offline copies of critical passwords

## Monitoring

**Set up alerts for backup failures:**

```bash
# Check for recent successful backups
find /var/backups -name "*.gpg" -mtime -2

# Monitor disk space
df -h /var/backups

# Set up log monitoring (example with logwatch)
echo "vaultwarden-backup" >> /etc/logwatch/conf/services/vaultwarden-backup.conf
```
