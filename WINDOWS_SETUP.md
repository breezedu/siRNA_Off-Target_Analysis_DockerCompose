# Windows Quick Start Guide

## Step-by-Step Setup for Windows Users

### 1. Install Docker Desktop

1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop/
2. Run the installer
3. **Important**: During installation, ensure "Use WSL 2 instead of Hyper-V" is selected
4. Restart your computer when prompted
5. After restart, launch Docker Desktop
6. Accept the service agreement
7. Wait for Docker Desktop to start (whale icon in system tray)

### 2. Verify Installation

Open PowerShell (Windows key + X, then select "Windows PowerShell" or "Terminal"):

```powershell
docker --version
docker-compose --version
```

You should see something like:
```
Docker version 24.0.x
Docker Compose version v2.x.x
```

### 3. Extract the Tool

1. Extract the ZIP file to a convenient location, e.g., `C:\Users\YourName\Documents\siRNA-tool`
2. Open PowerShell
3. Navigate to the extracted folder:

```powershell
cd C:\Users\YourName\Documents\siRNA-tool
```

### 4. Start the Application

```powershell
# Build all containers (first time - takes 5-10 minutes)
docker-compose build

# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps
```

You should see all services showing "Up" status.

### 5. Access the Application

Open your web browser (Chrome, Edge, or Firefox) and go to:
- http://localhost:3000

You should see the siRNA Off-Target Analysis Tool interface!

### 6. Load Sample Data (Optional)

Before analyzing siRNAs, you need transcriptome data. You can:

**Option A: Use a small test dataset** (recommended for first-time setup)
1. Create a small test FASTA file at `C:\Users\YourName\Documents\siRNA-tool\database\data\test.fasta`
2. Add a few transcript sequences:

```
>NM_000001 Test Gene 1
AUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGC
>NM_000002 Test Gene 2  
GCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAU
```

3. Upload via PowerShell:

```powershell
cd C:\Users\YourName\Documents\siRNA-tool

# Upload the file
$file = ".\database\data\test.fasta"
curl.exe -X POST -F "file=@$file" http://localhost:8000/api/upload/transcriptome

# Build database
curl.exe -X POST "http://localhost:8000/api/build-database?transcriptome_file=test.fasta"

# Check status (wait a minute, then run)
curl.exe http://localhost:8000/api/database/status
```

**Option B: Download human transcriptome** (for real analysis)
- Go to NCBI RefSeq: https://www.ncbi.nlm.nih.gov/refseq/
- Download human mRNA FASTA file
- Place in `database/data/` folder
- Follow upload steps from Option A

### 7. Run Your First Analysis

1. Go to http://localhost:3000
2. Enter a test siRNA sequence: `GUGAUGUAGCCUAUGACACAA`
3. Give it a name: `Test_siRNA_001`
4. Click "Analyze Off-Targets"
5. Wait 30-60 seconds
6. View results!

## Common Issues & Solutions

### Issue: "Docker Desktop is not running"

**Solution:**
1. Press Windows key and type "Docker Desktop"
2. Launch Docker Desktop
3. Wait for the whale icon to appear in system tray (bottom-right)
4. Try your command again

### Issue: "Port 3000 is already in use"

**Solution:**
Check what's using port 3000:
```powershell
netstat -ano | findstr :3000
```

Option 1: Stop the other service
Option 2: Change the port in `docker-compose.yml`:
```yaml
frontend:
  ports:
    - "3001:3000"  # Changed from 3000:3000
```
Then access at http://localhost:3001

### Issue: "Cannot connect to Docker daemon"

**Solution:**
1. Open Docker Desktop settings (right-click whale icon)
2. Go to "Resources" → "WSL Integration"
3. Enable integration with your WSL distro
4. Restart Docker Desktop

### Issue: Services won't start / "Exited (1)"

**Solution:**
```powershell
# Check logs to see what failed
docker-compose logs backend
docker-compose logs database

# Often fixed by removing and rebuilding
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Issue: Analysis takes forever / hangs

**Solution:**
1. Check database is ready:
```powershell
curl.exe http://localhost:8000/api/database/status
```

2. Check worker is running:
```powershell
docker-compose ps worker
```

3. View worker logs:
```powershell
docker-compose logs -f worker
```

### Issue: "Out of memory" errors

**Solution:**
1. Open Docker Desktop
2. Settings → Resources → Advanced
3. Increase Memory to 4-8 GB
4. Click "Apply & Restart"

## Daily Usage

### To Start
```powershell
cd C:\Users\YourName\Documents\siRNA-tool
docker-compose up -d
```

Wait 30 seconds, then open http://localhost:3000

### To Stop
```powershell
cd C:\Users\YourName\Documents\siRNA-tool
docker-compose stop
```

### To View Logs (if something goes wrong)
```powershell
docker-compose logs -f
```
Press Ctrl+C to exit

### To Update Code (if you make changes)
```powershell
docker-compose down
docker-compose build
docker-compose up -d
```

## Getting Help

1. **Check logs first:**
   ```powershell
   docker-compose logs backend
   docker-compose logs worker
   ```

2. **Restart services:**
   ```powershell
   docker-compose restart
   ```

3. **Complete reset (if nothing else works):**
   ```powershell
   docker-compose down -v
   docker-compose build --no-cache
   docker-compose up -d
   ```

## Performance Tips

- **Use SSD**: Ensure project is on SSD, not HDD
- **Increase Docker memory**: Settings → Resources → Advanced → 8 GB
- **Close other applications**: Free up RAM for Docker
- **Update Docker**: Keep Docker Desktop up to date

## Next Steps

Once you have it running:
1. Upload a real transcriptome (human RefSeq)
2. Test with your own siRNA sequences
3. Experiment with different parameters
4. Download results as CSV for further analysis
5. Integrate with your analysis pipeline via API

## Need More Help?

- Check the main README.md for detailed documentation
- Review API documentation at http://localhost:8000/docs
- Check Docker Desktop logs (Settings → Troubleshoot → View Logs)

Happy analyzing! 🧬
