# siRNA Off-Target Analysis Tool

A comprehensive web-based tool for predicting siRNA off-target effects using seed-based matching and thermodynamic scoring.

## Features

- **Seed-based search**: Focuses on positions 2-8 (primary determinant of targeting)
- **Thermodynamic scoring**: Nearest-neighbor free energy calculations
- **Risk assessment**: Combined scoring with sequence context and structure
- **Interactive web UI**: Real-time analysis with visual results
- **Background processing**: Celery-based job queue for scalable analysis
- **PostgreSQL database**: Indexed transcriptome for fast lookups

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│   React     │─────▶│   FastAPI    │─────▶│  PostgreSQL  │
│  Frontend   │      │   Backend    │      │   Database   │
│  (Port 3000)│      │  (Port 8000) │      │  (Port 5432) │
└─────────────┘      └──────────────┘      └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │    Redis +   │
                     │    Celery    │
                     │   Workers    │
                     └──────────────┘
```

## Prerequisites (Windows)

1. **Docker Desktop for Windows**
   - Download from: https://www.docker.com/products/docker-desktop/
   - Install and restart your computer
   - Ensure WSL 2 backend is enabled (Settings → General → Use WSL 2)

2. **Git for Windows** (optional, for cloning)
   - Download from: https://git-scm.com/download/win

## Installation & Setup

### Step 1: Extract/Clone the Project

If you received this as a ZIP file:
```bash
# Extract to a location like C:\Users\YourName\siRNA-tool
# Open PowerShell or Command Prompt in that directory
cd C:\Users\YourName\siRNA-tool
```

Or clone from repository:
```bash
git clone <repository-url>
cd sirna-offtarget-tool
```

### Step 2: Verify Docker is Running

```bash
docker --version
docker-compose --version
```

You should see version numbers. If not, start Docker Desktop.

### Step 3: Build and Start Services

```bash
# Build all containers (first time only, takes 5-10 minutes)
docker-compose build

# Start all services
docker-compose up -d

# Check if services are running
docker-compose ps
```

Expected output:
```
NAME                 STATUS              PORTS
sirna-backend        Up                  0.0.0.0:8000->8000
sirna-frontend       Up                  0.0.0.0:3000->3000
sirna-database       Up                  0.0.0.0:5432->5432
sirna-redis          Up                  0.0.0.0:6379->6379
sirna-worker         Up
```

### Step 4: Access the Application

Open your web browser and navigate to:
- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs

## Loading Transcriptome Data

### Option 1: Upload via Web UI (Coming Soon)

The UI will have an admin panel for uploading FASTA files.

### Option 2: Load via API

1. **Download Human Transcriptome**

Download from NCBI RefSeq or Ensembl. Example:
```bash
# Human RefSeq mRNA (example URL - check NCBI for latest)
# Download to: sirna-offtarget-tool/database/data/human_refseq.fasta
```

2. **Upload File**

Using PowerShell:
```powershell
$file = "C:\Users\YourName\siRNA-tool\database\data\human_refseq.fasta"
curl.exe -X POST -F "file=@$file" http://localhost:8000/api/upload/transcriptome
```

Or using curl (if installed):
```bash
curl -X POST -F "file=@./database/data/human_refseq.fasta" http://localhost:8000/api/upload/transcriptome
```

3. **Build Database**

```bash
curl -X POST "http://localhost:8000/api/build-database?transcriptome_file=human_refseq.fasta"
```

This process takes 10-30 minutes depending on file size. Monitor progress:
```bash
# View worker logs
docker-compose logs -f worker
```

4. **Check Database Status**

```bash
curl http://localhost:8000/api/database/status
```

Expected response:
```json
{
  "ready": true,
  "statistics": {
    "transcripts": 45000,
    "seed_indices": 2500000,
    "status": "ready"
  }
}
```

## Usage

### Via Web Interface

1. Navigate to http://localhost:3000
2. Enter your siRNA sequence (19-23 nucleotides)
3. Adjust parameters:
   - **Max Seed Mismatches**: 0-2 (default: 1)
   - **Energy Threshold**: -15 to -5 kcal/mol (default: -10)
4. Click "Analyze Off-Targets"
5. Wait 30-60 seconds for results
6. Review results:
   - Summary statistics
   - Interactive chart
   - Sortable table
7. Download results as CSV

### Via API

Example using PowerShell:
```powershell
$body = @{
    sirnas = @(
        @{
            name = "siRNA_Test"
            sequence = "GUGAUGUAGCCUAUGACACAA"
        }
    )
    max_seed_mismatches = 1
    energy_threshold = -10.0
    include_structure = $true
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/analyze" -Method Post -Body $body -ContentType "application/json"

Write-Host "Job ID: $($response.job_id)"

# Check status
Invoke-RestMethod -Uri "http://localhost:8000/api/status/$($response.job_id)"

# Get results (when completed)
Invoke-RestMethod -Uri "http://localhost:8000/api/results/$($response.job_id)"
```

## Managing the Application

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose stop
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f worker
```

### Restart Services
```bash
docker-compose restart
```

### Rebuild After Code Changes
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

### Remove All Data (Clean Slate)
```bash
docker-compose down -v
```

## Troubleshooting

### Port Already in Use

If you see errors about ports 3000, 8000, 5432, or 6379 being in use:

1. Check what's using the port:
```powershell
netstat -ano | findstr :3000
```

2. Either stop the conflicting service or change ports in `docker-compose.yml`

### Docker Desktop Not Starting

- Ensure Hyper-V is enabled (Windows Features)
- Ensure WSL 2 is installed and updated
- Restart Docker Desktop
- Check Docker Desktop settings → Resources

### Database Connection Errors

```bash
# Check if database is ready
docker-compose logs database

# Restart database
docker-compose restart database

# Check backend can connect
docker-compose logs backend
```

### Services Not Starting

```bash
# Check service status
docker-compose ps

# View detailed logs
docker-compose logs backend
docker-compose logs worker

# Rebuild specific service
docker-compose build backend
docker-compose up -d backend
```

### Slow Analysis

- Ensure database is fully indexed (check `/api/database/status`)
- Check worker is running: `docker-compose ps worker`
- Increase worker count in `docker-compose.yml` (scale up)

### Out of Memory

Docker Desktop settings:
- Settings → Resources → Advanced
- Increase Memory to at least 4 GB (8 GB recommended)

## Development

### Backend Development

```bash
# Enter backend container
docker-compose exec backend bash

# Run Python shell
python

# Run tests (if implemented)
pytest
```

### Frontend Development

```bash
# Enter frontend container
docker-compose exec frontend sh

# Install new package
npm install <package-name>
```

### Database Management

```bash
# Connect to PostgreSQL
docker-compose exec database psql -U sirna_user -d sirna_offtarget

# Common queries
\dt                          # List tables
SELECT COUNT(*) FROM transcripts;
SELECT COUNT(*) FROM seed_index;
\q                           # Quit
```

## Project Structure

```
sirna-offtarget-tool/
├── docker-compose.yml       # Orchestration
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py             # FastAPI app
│   ├── tasks.py            # Celery tasks
│   ├── core/
│   │   └── analyzer.py     # Core analysis logic
│   └── database/
│       ├── models.py       # SQLAlchemy models
│       ├── db.py           # Database connection
│       └── build.py        # Database builder
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── public/
│   └── src/
│       ├── App.js
│       ├── App.css
│       └── components/
│           ├── SequenceInput.js
│           ├── StatusMonitor.js
│           └── ResultsDisplay.js
└── database/
    ├── init.sql
    └── data/               # Place FASTA files here
```

## Performance Optimization

### For Large Transcriptomes

1. **Increase Database Resources**
   - Edit `docker-compose.yml` → database → deploy → resources

2. **Add More Workers**
```yaml
worker:
  # In docker-compose.yml
  deploy:
    replicas: 4  # Run 4 workers
```

3. **Use SSD Storage**
   - Ensure Docker Desktop data directory is on SSD

### For Batch Analysis

Use the API to submit multiple siRNAs:
```python
import requests
import time

sirnas = [
    {"name": "siRNA_1", "sequence": "GUGAUGUAGCCUAUGACACAA"},
    {"name": "siRNA_2", "sequence": "GCUACUGCUUACGAUCGAUAA"},
    # ... more siRNAs
]

job_ids = []
for sirna in sirnas:
    response = requests.post("http://localhost:8000/api/analyze", json={
        "sirnas": [sirna],
        "max_seed_mismatches": 1,
        "energy_threshold": -10.0
    })
    job_ids.append(response.json()["job_id"])

# Wait and collect results
for job_id in job_ids:
    while True:
        status = requests.get(f"http://localhost:8000/api/status/{job_id}").json()
        if status["status"] == "completed":
            results = requests.get(f"http://localhost:8000/api/results/{job_id}").json()
            print(f"Completed: {results['sirna_name']}")
            break
        time.sleep(5)
```

## Citation

If you use this tool in your research, please cite:
- Turner Nearest-Neighbor Parameters (2004)
- Birmingham et al. (2006) - 3' UTR seed matches and RNAi off-targets

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
1. Check logs: `docker-compose logs`
2. Review troubleshooting section above
3. Open an issue on GitHub (if applicable)

## Contributors

Developed for bioinformatics siRNA analysis workflows.
