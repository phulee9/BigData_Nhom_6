from fastapi import APIRouter, HTTPException
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "core"))
sys.path.insert(0, str(BASE))

from roadmap import skill_gap_roadmap
from core.loader import load_index
from models import SkillRoadmapRequest

router = APIRouter()

_index = None
_df = None


def get_index():
    """Get or load FAISS index and metadata"""
    global _index, _df
    if _index is None or _df is None:
        _index, _df = load_index()
    return _index, _df


@router.post("/api/skill-roadmap")
async def get_roadmap(request: SkillRoadmapRequest):
    """Tao roadmap hoc skills"""
    try:
        _, df = get_index()
        result = skill_gap_roadmap(
            cv_skills=request.skills,
            job_title=request.job_title,
            df=df,
            top_n=5
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
