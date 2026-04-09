from fastapi import APIRouter, HTTPException
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "core"))
sys.path.insert(0, str(BASE))

from recommend import recommend_skills
from core.loader import load_index
from models import RecommendSkillsRequest

router = APIRouter()

# Global state
_index = None
_df = None


def get_index():
    """Get or load FAISS index and metadata"""
    global _index, _df
    if _index is None or _df is None:
        _index, _df = load_index()
    return _index, _df


@router.post("/api/recommend-skills")
async def get_recommendations(request: RecommendSkillsRequest):
    """Goi y skills con thieu"""
    try:
        index, df = get_index()
        result = recommend_skills(
            cv_skills=request.skills,
            job_title=request.job_title,
            index=index,
            df=df,
            top_k=150,
            top_skills=10
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
