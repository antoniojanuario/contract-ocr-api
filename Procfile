web: python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
worker: python run_worker.py
release: python scripts/migrate_db.py