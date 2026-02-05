# siRNA Off-Target Tool - Quick Reference Card

## Essential Commands (PowerShell)

### Starting & Stopping

```powershell
# Navigate to project
cd C:\Users\YourName\Documents\siRNA-tool

# Start all services
docker-compose up -d

# Stop all services
docker-compose stop

# Stop and remove everything (clean slate)
docker-compose down -v
```

### Checking Status

```powershell
# View running services
docker-compose ps

# View logs (all services)
docker-compose logs -f

# View logs (specific service)
docker-compose logs -f backend
docker-compose logs -f worker

# Check health
curl.exe http://localhost:8000/health
```

### Accessing the Application

- **Web Interface**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Database Status**: http://localhost:8000/api/database/status

### Database Operations

```powershell
# Upload transcriptome
$file = ".\database\data\your_file.fasta"
curl.exe -X POST -F "file=@$file" http://localhost:8000/api/upload/transcriptome

# Build database
curl.exe -X POST "http://localhost:8000/api/build-database?transcriptome_file=your_file.fasta"

# Check database status
curl.exe http://localhost:8000/api/database/status

# Connect to database directly
docker-compose exec database psql -U sirna_user -d sirna_offtarget
```

### Analysis (API)

```powershell
# Submit analysis
$body = @{
    sirnas = @(@{
        name = "My_siRNA"
        sequence = "GUGAUGUAGCCUAUGACACAA"
    })
    max_seed_mismatches = 1
    energy_threshold = -10.0
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/analyze" -Method Post -Body $body -ContentType "application/json"

# Get job ID
$jobId = $response.job_id

# Check status
Invoke-RestMethod -Uri "http://localhost:8000/api/status/$jobId"

# Get results
Invoke-RestMethod -Uri "http://localhost:8000/api/results/$jobId"
```

### Troubleshooting

```powershell
# Restart services
docker-compose restart

# Rebuild after code changes
docker-compose down
docker-compose build
docker-compose up -d

# View container details
docker-compose ps -a

# Check Docker disk usage
docker system df

# Clean up unused resources
docker system prune
```

### Backup & Restore

```powershell
# Backup database
docker-compose exec database pg_dump -U sirna_user sirna_offtarget > backup_$(Get-Date -Format 'yyyyMMdd').sql

# Restore database
Get-Content backup_20240215.sql | docker-compose exec -T database psql -U sirna_user sirna_offtarget
```

## Common Issues

### "Cannot connect to Docker daemon"
→ Start Docker Desktop (Windows key → "Docker Desktop")

### "Port already in use"
→ Change port in `docker-compose.yml` or stop conflicting service

### "Out of memory"
→ Docker Desktop → Settings → Resources → Increase Memory to 8GB

### Services stuck "Starting"
→ `docker-compose down -v` then `docker-compose up -d`

### Analysis hanging
→ Check worker: `docker-compose logs worker`
→ Check database status: `curl.exe http://localhost:8000/api/database/status`

### Database not ready
→ Verify transcriptome uploaded and indexed
→ Check build progress: `docker-compose logs -f worker`

## Parameters Reference

### Max Seed Mismatches
- **0**: Exact match only (very stringent)
- **1**: Allow 1 mismatch in seed (recommended)
- **2**: Allow 2 mismatches (very permissive)

### Energy Threshold (kcal/mol)
- **-15**: Only strong binders (stringent)
- **-10**: Moderate binders (recommended)
- **-5**: Include weak binders (permissive)

### Risk Score Interpretation
- **> 0.7**: High risk off-target
- **0.5 - 0.7**: Moderate risk
- **< 0.5**: Low risk

## File Locations

### Project Structure
```
siRNA-tool/
├── backend/           # Python/FastAPI code
├── frontend/          # React code
├── database/
│   └── data/         # PUT FASTA FILES HERE
├── docker-compose.yml # Main config
└── README.md         # Full documentation
```

### Data Volumes
- Database data: Docker volume `sirna-offtarget-tool_postgres_data`
- Redis data: Docker volume `sirna-offtarget-tool_redis_data`
- Transcriptome files: Docker volume `sirna-offtarget-tool_transcriptome_data`

## Performance Tips

- Use SSD for project location
- Allocate 8GB RAM to Docker
- Close unnecessary applications
- Use batch API for multiple siRNAs
- Index database before heavy usage

## Support

1. Check logs: `docker-compose logs`
2. Review README.md for detailed docs
3. Check WINDOWS_SETUP.md for setup issues
4. Visit http://localhost:8000/docs for API reference

---

**Keep this card handy for quick reference!**

Print and laminate for desk reference, or save to desktop for easy access.
