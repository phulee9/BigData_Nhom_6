from fastapi import APIRouter, HTTPException
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "core"))
sys.path.insert(0, str(BASE))

from career_switch import career_switch_analysis
from core.loader import load_index
from models import CareerSwitchRequest

router = APIRouter()

_index = None
_df = None


def get_index():
    """Get or load FAISS index and metadata"""
    global _index, _df
    if _index is None or _df is None:
        _index, _df = load_index()
    return _index, _df


@router.post("/api/career-switch")
async def career_analysis(request: CareerSwitchRequest):
    """Phan tich chuyen huong nghe nghiep"""
    try:
        _, df = get_index()
        result = career_switch_analysis(
            job_from=request.job_from,
            job_to=request.job_to,
            cv_skills=request.skills,
            df=df,
            top_n=20
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
