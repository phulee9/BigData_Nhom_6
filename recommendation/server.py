"""
FastAPI Backend for Skill Recommender
Main server entry point
"""
import sys
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Setup paths
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR / "core"))
sys.path.insert(0, str(BASE_DIR / "cv"))
sys.path.insert(0, str(BASE_DIR))

load_dotenv(BASE_DIR.parent / ".env")

# Import routers
from routers.cv_router import router as cv_router
from routers.recommendations_router import router as rec_router
from routers.roadmap_router import router as roadmap_router
from routers.career_router import router as career_router

from core.loader import load_index

# Create app
app = FastAPI(
    title="Skill Recommender API",
    version="1.0",
    description="API for job skills recommendation system"
)

# CORS - Allow all origins or restrict to frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load resources at startup
@app.on_event("startup")
async def startup():
    """Preload FAISS index and models at startup"""
    print("\n" + "="*60)
    print("  ⏳ Initializing Skill Recommender API...")
    print("="*60)
    try:
        index, df = load_index()
        print(f"✓ FAISS index loaded: {index.ntotal:,} vectors")
        print(f"✓ Metadata loaded: {len(df):,} jobs")
        print("="*60)
    except Exception as e:
        print(f"ERROR: {e}")
        raise


# Include routers
app.include_router(cv_router)
app.include_router(rec_router)
app.include_router(roadmap_router)
app.include_router(career_router)


# API Routes
@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Skill Recommender API",
        "version": "1.0",
        "docs_url": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "message": "API is running"}


@app.get("/api/endpoints")
async def endpoints():
    """List all available endpoints"""
    return {
        "CV": [
            "POST /api/upload-cv - Upload CV file (PDF/DOCX)",
            "POST /api/manual-info - Manual job title + skills input"
        ],
        "Recommendations": [
            "POST /api/recommend-skills - Get skill recommendations"
        ],
        "Roadmap": [
            "POST /api/skill-roadmap - Get learning roadmap for skills"
        ],
        "Career": [
            "POST /api/career-switch - Analyze career switch feasibility"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("  🚀 Starting Skill Recommender API Server")
    print("="*60)
    print("  📍 Server: http://0.0.0.0:8000")
    print("  📖 Docs:   http://localhost:8000/docs")
    print("="*60 + "\n")
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
