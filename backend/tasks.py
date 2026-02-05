from celery import Celery, Task
import os
import sys
import time

# Add the app directory to Python path
sys.path.insert(0, '/app')

# Initialize Celery
celery_app = Celery(
    'sirna_offtarget',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
)

@celery_app.task(bind=True)
def analyze_sirna_task(
    self,
    sirna_name: str,
    sirna_sequence: str,
    max_seed_mismatches: int = 1,
    energy_threshold: float = -10.0,
    include_structure: bool = True
):
    """
    Background task for siRNA off-target analysis
    Uses self.request.id as the job_id
    """
    try:
        # Import here to avoid circular imports and ensure path is set
        try:
            from core.analyzer import SiRNAAnalyzer
        except ModuleNotFoundError:
            import core.analyzer
            SiRNAAnalyzer = core.analyzer.SiRNAAnalyzer
        
        # Get the Celery task ID to use as job_id
        job_id = self.request.id
        
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'progress': 10, 'message': 'Initializing analyzer...'}
        )
        
        # Initialize analyzer
        analyzer = SiRNAAnalyzer()
        
        # Update state
        self.update_state(
            state='PROGRESS',
            meta={'progress': 20, 'message': 'Searching for seed matches...'}
        )
        
        # Run analysis
        results = analyzer.analyze(
            sirna_sequence=sirna_sequence,
            max_seed_mismatches=max_seed_mismatches,
            energy_threshold=energy_threshold,
            include_structure=include_structure
        )
        
        # Update state
        self.update_state(
            state='PROGRESS',
            meta={'progress': 80, 'message': 'Calculating risk scores...'}
        )
        
        # Format results
        formatted_results = {
            'job_id': job_id,
            'sirna_name': sirna_name,
            'sirna_sequence': sirna_sequence,
            'high_risk_count': len([r for r in results if r['risk_score'] > 0.7]),
            'moderate_risk_count': len([r for r in results if 0.5 <= r['risk_score'] <= 0.7]),
            'low_risk_count': len([r for r in results if r['risk_score'] < 0.5]),
            'total_offtargets': len(results),
            'offtargets': results[:100]  # Return top 100
        }
        
        return formatted_results
        
    except Exception as e:
        import traceback
        error_msg = f"Error in analysis: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        
        self.update_state(
            state='FAILURE',
            meta={
                'exc_type': type(e).__name__,
                'exc_message': str(e),
                'traceback': traceback.format_exc()
            }
        )
        raise

@celery_app.task
def build_database_task(transcriptome_file_path: str):
    """
    Background task for building transcriptome database
    """
    try:
        from database.build import build_transcriptome_database
    except ModuleNotFoundError:
        import database.build
        build_transcriptome_database = database.build.build_transcriptome_database
    
    try:
        build_transcriptome_database(transcriptome_file_path)
        return {"status": "success", "message": "Database built successfully"}
    except Exception as e:
        import traceback
        error_msg = f"Error building database: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return {"status": "error", "message": str(e)}
