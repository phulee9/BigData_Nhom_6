from fastapi import APIRouter, UploadFile, File, HTTPException
import fitz
import sys
from pathlib import Path
from io import BytesIO

# Add paths
BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "cv"))
sys.path.insert(0, str(BASE / "core"))
sys.path.insert(0, str(BASE))

from cv_extractor import extract_cv, dedup_skills
from models import CVUploadResponse, ManualInfoRequest

router = APIRouter()


def read_pdf_bytes(file_bytes: bytes) -> str:
    """Read PDF from bytes"""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            pages.append(text)
    doc.close()
    return "\n".join(pages)


@router.post("/api/upload-cv")
async def upload_cv(file: UploadFile = File(...)):
    """Upload CV (PDF/DOCX) and extract job title + skills"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file")
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".pdf", ".docx"]:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX supported")
    
    file_bytes = await file.read()
    
    try:
        # Read text from file
        if file_ext == ".pdf":
            cv_text = read_pdf_bytes(file_bytes)
        else:  # .docx
            try:
                from docx import Document
                doc = Document(BytesIO(file_bytes))
                cv_text = "\n".join([p.text for p in doc.paragraphs])
            except ImportError:
                raise HTTPException(
                    status_code=400,
                    detail="Please install: pip install python-docx"
                )
        
        if not cv_text.strip():
            raise HTTPException(status_code=400, detail="Cannot extract text from file")
        
        # Extract using Groq
        data = extract_cv(cv_text)
        if not data:
            raise HTTPException(status_code=400, detail="Failed to extract CV")
        
        skills_clean = dedup_skills(data.get("skills", []))
        
        return {
            "vi_tri_ung_tuyen": data.get("vi_tri_ung_tuyen", ""),
            "skills": skills_clean,
            "message": f"Extracted {len(skills_clean)} skills successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")


@router.post("/api/manual-info")
async def manual_info(request: ManualInfoRequest):
    """Nhap tay job title + skills"""
    if not request.job_title or not request.skills:
        raise HTTPException(status_code=400, detail="job_title and skills required")
    
    skills_clean = dedup_skills(request.skills)
    return CVUploadResponse(
        vi_tri_ung_tuyen=request.job_title.lower().strip(),
        skills=skills_clean,
        message="Submitted successfully"
    )
