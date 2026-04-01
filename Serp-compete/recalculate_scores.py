from src.database import DatabaseManager
from src.semantic import SemanticAuditor
import sys

def recalculate_last_run():
    db = DatabaseManager()
    auditor = SemanticAuditor()
    
    run_id = db.get_latest_run_id()
    if not run_id:
        print("No runs found to recalculate.")
        return
        
    print(f"Recalculating scores for Run ID: {run_id}")
    urls = db.get_run_urls(run_id)
    
    if not urls:
        print("No URLs found for the last run in traffic_magnets.")
        return
        
    for url in urls:
        print(f"Processing {url}...")
        content = auditor.scrape_content(url)
        if content:
            scores = auditor.analyze_text(content)
            db.update_traffic_magnet_scores(run_id, url, scores['medical_score'], scores['systems_score'])
            print(f"  Updated: Medical {scores['medical_score']}, Systems {scores['systems_score']}")
        else:
            print(f"  Failed to scrape {url}")

    print("Recalculation complete.")

if __name__ == "__main__":
    recalculate_last_run()
