"""Root entry-point to run the Lumina FastAPI server and web dashboard."""

import sys
from pathlib import Path

# Automatically inject the src folder into Python module search path
root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir / "src"))

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  Starting Lumina Engine Server")
    print("  Backend API:      http://127.0.0.1:8000/api")
    print("  API Docs:         http://127.0.0.1:8000/docs")
    print("  Web Application:  http://127.0.0.1:8000/")
    print("=" * 60)
    uvicorn.run(
        "researchmind.api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
