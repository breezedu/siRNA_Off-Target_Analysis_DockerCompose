# Deployment Checklist

## Pre-Deployment

### Windows System Requirements
- [ ] Windows 10/11 (64-bit)
- [ ] At least 8 GB RAM (16 GB recommended)
- [ ] 20 GB free disk space
- [ ] Administrator privileges
- [ ] Internet connection (for downloading Docker and dependencies)

### Software Installation
- [ ] Docker Desktop installed and running
- [ ] WSL 2 enabled and configured
- [ ] PowerShell 5.1+ or Windows Terminal

## Initial Setup

### 1. Extract Project
- [ ] Extract ZIP to known location (e.g., `C:\Users\YourName\Documents\siRNA-tool`)
- [ ] Verify all folders are present:
  - [ ] `backend/`
  - [ ] `frontend/`
  - [ ] `database/`
  - [ ] `docker-compose.yml` at root

### 2. Docker Configuration
- [ ] Docker Desktop is running (whale icon in system tray)
- [ ] Docker has at least 4 GB memory allocated (Settings → Resources)
- [ ] WSL 2 integration is enabled

### 3. Build Containers
```powershell
cd C:\Users\YourName\Documents\siRNA-tool
docker-compose build
```
- [ ] Backend built successfully
- [ ] Frontend built successfully
- [ ] Database pulled successfully
- [ ] Redis pulled successfully
- [ ] Worker built successfully

### 4. Start Services
```powershell
docker-compose up -d
```
- [ ] All 5 services show "Up" status
- [ ] No error messages in logs

### 5. Verify Services

**Check service status:**
```powershell
docker-compose ps
```
- [ ] `sirna-backend` is Up on port 8000
- [ ] `sirna-frontend` is Up on port 3000
- [ ] `sirna-database` is Up on port 5432
- [ ] `sirna-redis` is Up on port 6379
- [ ] `sirna-worker` is Up

**Check web access:**
- [ ] http://localhost:3000 loads (Frontend)
- [ ] http://localhost:8000/docs loads (API docs)
- [ ] http://localhost:8000/health returns `{"status": "healthy"}`

### 6. Database Setup

**Check database status:**
```powershell
curl.exe http://localhost:8000/api/database/status
```
- [ ] Returns status without errors
- [ ] `"ready": false` initially (expected - no data yet)

**Prepare transcriptome data:**
- [ ] Downloaded transcriptome FASTA file
- [ ] Placed in `database/data/` folder
- [ ] File is valid FASTA format

**Upload transcriptome:**
```powershell
$file = ".\database\data\human_refseq.fasta"  # Adjust filename
curl.exe -X POST -F "file=@$file" http://localhost:8000/api/upload/transcriptome
```
- [ ] Upload successful
- [ ] File appears in `/data/transcriptome` inside container

**Build database index:**
```powershell
curl.exe -X POST "http://localhost:8000/api/build-database?transcriptome_file=human_refseq.fasta"
```
- [ ] Build started successfully
- [ ] Monitor progress in worker logs: `docker-compose logs -f worker`
- [ ] Wait for completion (10-30 minutes depending on file size)

**Verify database is ready:**
```powershell
curl.exe http://localhost:8000/api/database/status
```
- [ ] `"ready": true`
- [ ] Transcript count > 0
- [ ] Seed index count > 0

## Testing

### Test Analysis (via Web UI)
- [ ] Navigate to http://localhost:3000
- [ ] Enter test sequence: `GUGAUGUAGCCUAUGACACAA`
- [ ] Name: `Test_Analysis_001`
- [ ] Click "Analyze Off-Targets"
- [ ] Analysis completes within 1 minute
- [ ] Results display correctly
- [ ] Can download CSV

### Test Analysis (via API)
```powershell
$body = @{
    sirnas = @(
        @{
            name = "API_Test"
            sequence = "GUGAUGUAGCCUAUGACACAA"
        }
    )
    max_seed_mismatches = 1
    energy_threshold = -10.0
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/analyze" -Method Post -Body $body -ContentType "application/json"
```
- [ ] Returns job_id
- [ ] Status check works
- [ ] Results retrievable when complete

## Performance Validation

### Load Testing (Optional)
- [ ] Submit 5 siRNAs simultaneously
- [ ] All complete within reasonable time
- [ ] No memory issues
- [ ] No crashes

### Resource Monitoring
- [ ] Check Docker Desktop stats (whale icon → Dashboard)
- [ ] Memory usage < 6 GB (with 8 GB allocated)
- [ ] CPU usage returns to idle after analysis
- [ ] No error logs appearing

## Documentation

- [ ] README.md is accessible and clear
- [ ] WINDOWS_SETUP.md provides clear instructions
- [ ] API documentation at /docs is functional
- [ ] .env.example shows all configurable options

## Backup & Recovery

### Create Backup
- [ ] Export database:
```powershell
docker-compose exec database pg_dump -U sirna_user sirna_offtarget > backup.sql
```
- [ ] Store backup safely
- [ ] Document backup location

### Test Recovery
- [ ] Stop services: `docker-compose stop`
- [ ] Remove volumes: `docker-compose down -v`
- [ ] Restart: `docker-compose up -d`
- [ ] Restore database:
```powershell
Get-Content backup.sql | docker-compose exec -T database psql -U sirna_user sirna_offtarget
```
- [ ] Verify data restored correctly

## Production Readiness

### Security (for production deployment)
- [ ] Change default database password in docker-compose.yml
- [ ] Update Redis password if exposed
- [ ] Enable HTTPS (if publicly accessible)
- [ ] Review CORS settings in backend/main.py
- [ ] Add authentication (if needed)

### Monitoring
- [ ] Set up log rotation
- [ ] Configure error alerting
- [ ] Monitor disk space
- [ ] Monitor database size

### Maintenance
- [ ] Schedule regular backups
- [ ] Plan for transcriptome updates
- [ ] Document update procedures
- [ ] Create rollback plan

## User Handoff

### Training
- [ ] Demo the web interface
- [ ] Show how to interpret results
- [ ] Explain parameter settings
- [ ] Show how to download results

### Support Documentation
- [ ] Provide README.md
- [ ] Provide WINDOWS_SETUP.md
- [ ] Share troubleshooting guide
- [ ] Document common issues

### Contact & Support
- [ ] Provide contact for technical issues
- [ ] Document escalation procedures
- [ ] Share update schedule
- [ ] Provide feedback mechanism

## Post-Deployment

### First Week
- [ ] Monitor for errors daily
- [ ] Check disk space
- [ ] Verify backups working
- [ ] Collect user feedback

### First Month
- [ ] Review performance metrics
- [ ] Optimize based on usage patterns
- [ ] Update documentation as needed
- [ ] Plan improvements

## Troubleshooting Reference

### Services Won't Start
```powershell
docker-compose logs
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Database Issues
```powershell
docker-compose restart database
docker-compose logs database
docker-compose exec database psql -U sirna_user -d sirna_offtarget
```

### Worker Not Processing
```powershell
docker-compose logs worker
docker-compose restart worker
```

### Frontend Not Loading
```powershell
docker-compose logs frontend
docker-compose restart frontend
```

### Complete Reset
```powershell
docker-compose down -v
docker system prune -a
docker-compose build
docker-compose up -d
```

## Sign-Off

- [ ] All checklist items completed
- [ ] System tested and validated
- [ ] Documentation provided
- [ ] User training completed
- [ ] Backup/recovery tested
- [ ] Support plan in place

**Deployed by:** _________________  
**Date:** _________________  
**Approved by:** _________________  
**Date:** _________________

## Notes

Record any issues, customizations, or important information:

```
_____________________________________________________________________________

_____________________________________________________________________________

_____________________________________________________________________________

_____________________________________________________________________________
```
