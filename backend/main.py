from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import os
from datetime import datetime

from core.analyzer import SiRNAAnalyzer
from database.db import get_db_session, init_db
from tasks import analyze_sirna_task

app = FastAPI(
    title="siRNA Off-Target Analysis Tool",
    description="Comprehensive off-target prediction for siRNA sequences",
    version="1.0.0"
)

# CORS middleware - Allow all origins for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

# Pydantic models
class SiRNASequence(BaseModel):
    name: str = Field(..., description="Identifier for this siRNA")
    sequence: str = Field(..., min_length=19, max_length=23, description="Guide strand sequence (19-23 nt)")
    
class AnalysisRequest(BaseModel):
    sirnas: List[SiRNASequence]
    max_seed_mismatches: int = Field(default=1, ge=0, le=2)
    energy_threshold: float = Field(default=-10.0, le=0.0)
    include_structure: bool = Field(default=True)

class OffTargetResult(BaseModel):
    gene_symbol: str
    transcript_id: str
    position: int
    delta_g: float
    risk_score: float
    seed_matches: str
    mismatches: int
    alignment: str

class AnalysisResponse(BaseModel):
    job_id: str
    status: str
    sirna_name: str
    high_risk_count: Optional[int] = None
    moderate_risk_count: Optional[int] = None
    low_risk_count: Optional[int] = None
    offtargets: Optional[List[OffTargetResult]] = None
    created_at: datetime

class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: Optional[int] = None
    message: Optional[str] = None

# Endpoints
@app.get("/")
async def root():
    return {
        "message": "siRNA Off-Target Analysis API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now()}

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_sirna(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """
    Submit siRNA sequence(s) for off-target analysis
    Returns job_id for tracking progress
    """
    try:
        # For now, process first siRNA (can be extended for batch)
        sirna = request.sirnas[0]
        
        # Validate sequence
        if not all(c in 'ACGTU' for c in sirna.sequence.upper()):
            raise HTTPException(
                status_code=400, 
                detail="Invalid sequence. Only A, C, G, T, U characters allowed"
            )
        
        # Submit to Celery - DON'T generate job_id, use Celery's task_id
        task = analyze_sirna_task.apply_async(
            kwargs={
                'sirna_name': sirna.name,
                'sirna_sequence': sirna.sequence,
                'max_seed_mismatches': request.max_seed_mismatches,
                'energy_threshold': request.energy_threshold,
                'include_structure': request.include_structure
            }
        )
        
        # Use Celery's task ID as the job ID
        job_id = task.id
        
        return AnalysisResponse(
            job_id=job_id,
            status="pending",
            sirna_name=sirna.name,
            created_at=datetime.now()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """
    Check the status of an analysis job
    """
    from celery.result import AsyncResult
    from tasks import celery_app
    
    result = AsyncResult(job_id, app=celery_app)
    
    if result.state == 'PENDING':
        return JobStatus(
            job_id=job_id,
            status='pending',
            message='Analysis is queued'
        )
    elif result.state == 'PROGRESS':
        return JobStatus(
            job_id=job_id,
            status='processing',
            progress=result.info.get('progress', 0),
            message=result.info.get('message', 'Processing...')
        )
    elif result.state == 'SUCCESS':
        return JobStatus(
            job_id=job_id,
            status='completed',
            progress=100,
            message='Analysis complete'
        )
    elif result.state == 'FAILURE':
        return JobStatus(
            job_id=job_id,
            status='failed',
            message=str(result.info)
        )
    else:
        return JobStatus(
            job_id=job_id,
            status='unknown',
            message=f'Unknown state: {result.state}'
        )

@app.get("/api/results/{job_id}")
async def get_results(job_id: str):
    """
    Retrieve completed analysis results
    """
    from celery.result import AsyncResult
    from tasks import celery_app
    
    result = AsyncResult(job_id, app=celery_app)
    
    if result.state != 'SUCCESS':
        raise HTTPException(
            status_code=400,
            detail=f"Results not ready. Current state: {result.state}"
        )
    
    return result.result

@app.post("/api/upload/transcriptome")
async def upload_transcriptome(file: UploadFile = File(...)):
    """
    Upload transcriptome FASTA file for database construction
    Admin endpoint for initial setup
    """
    if not file.filename.endswith(('.fasta', '.fa', '.fna')):
        raise HTTPException(
            status_code=400,
            detail="File must be in FASTA format (.fasta, .fa, .fna)"
        )
    
    # Save uploaded file
    upload_dir = "/data/transcriptome"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, file.filename)
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    return {
        "message": "Transcriptome file uploaded successfully",
        "filename": file.filename,
        "size": len(content),
        "path": file_path
    }

@app.post("/api/build-database")
async def build_database(background_tasks: BackgroundTasks, transcriptome_file: str):
    """
    Build seed index database from uploaded transcriptome
    This is a one-time setup process
    """
    from database.build import build_transcriptome_database
    
    file_path = f"/data/transcriptome/{transcriptome_file}"
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"Transcriptome file not found: {transcriptome_file}"
        )
    
    # Run database build in background
    background_tasks.add_task(build_transcriptome_database, file_path)
    
    return {
        "message": "Database build started",
        "transcriptome_file": transcriptome_file,
        "status": "Processing in background"
    }

@app.get("/api/database/status")
async def database_status():
    """
    Check if transcriptome database is ready
    """
    from database.db import check_database_ready
    
    is_ready, stats = check_database_ready()
    
    return {
        "ready": is_ready,
        "statistics": stats
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
