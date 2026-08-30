"""FinSight AI — Main Application Entrypoint.

Launches the FastAPI server and modern Web UI at http://localhost:8000
"""
import uvicorn


def main():
    print("=" * 60)
    print("FinSight AI — Document Intelligence & Research Studio")
    print("Launching Web Application UI on http://localhost:8000")
    print("API Documentation available on http://localhost:8000/docs")
    print("=" * 60)
    uvicorn.run("finsight_agent.api.server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
