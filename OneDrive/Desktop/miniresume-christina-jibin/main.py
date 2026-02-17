import re
import uuid
from datetime import date, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, ValidationError, field_validator

app = FastAPI(
    title="Mini Resume Collector API",
    version="1.0.0",
    description="In-memory REST API for uploading and managing candidate resumes.",
)

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}
MAX_RESUME_SIZE_BYTES = 5 * 1024 * 1024
PHONE_PATTERN = re.compile(r"^[0-9+\-\s()]{7,20}$")

# Required in-memory store
candidates: dict[str, dict[str, Any]] = {}
store_lock = Lock()


class CandidateInput(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    dob: date
    contact_number: str = Field(..., min_length=7, max_length=20)
    contact_address: str = Field(..., min_length=5, max_length=300)
    education_qualification: str = Field(..., min_length=2, max_length=200)
    graduation_year: int
    years_of_experience: float = Field(..., ge=0, le=60)
    skill_set: list[str] = Field(..., min_length=1)

    @field_validator("full_name", "contact_address", "education_qualification")
    @classmethod
    def strip_text_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("contact_number")
    @classmethod
    def validate_contact_number(cls, value: str) -> str:
        cleaned = value.strip()
        if not PHONE_PATTERN.fullmatch(cleaned):
            raise ValueError("contact_number format is invalid")
        return cleaned

    @field_validator("dob")
    @classmethod
    def validate_dob(cls, value: date) -> date:
        if value >= date.today():
            raise ValueError("dob must be in the past")
        return value

    @field_validator("graduation_year")
    @classmethod
    def validate_graduation_year(cls, value: int) -> int:
        current_year = date.today().year
        if value < 1950 or value > current_year + 1:
            raise ValueError(f"graduation_year must be between 1950 and {current_year + 1}")
        return value

    @field_validator("skill_set")
    @classmethod
    def validate_skill_set(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            cleaned = item.strip()
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(cleaned)

        if not normalized:
            raise ValueError("skill_set must include at least one valid skill")
        return normalized


class CandidateResponse(CandidateInput):
    id: str
    resume_file_name: str
    created_at: datetime


def parse_skill_set(raw_skill_set: str) -> list[str]:
    return [item.strip() for item in raw_skill_set.split(",") if item.strip()]


def build_response(record: dict[str, Any]) -> CandidateResponse:
    return CandidateResponse(
        id=record["id"],
        full_name=record["full_name"],
        dob=record["dob"],
        contact_number=record["contact_number"],
        contact_address=record["contact_address"],
        education_qualification=record["education_qualification"],
        graduation_year=record["graduation_year"],
        years_of_experience=record["years_of_experience"],
        skill_set=record["skill_set"],
        resume_file_name=record["resume_file_name"],
        created_at=record["created_at"],
    )


def validate_candidate_input(
    *,
    full_name: str,
    dob: date,
    contact_number: str,
    contact_address: str,
    education_qualification: str,
    graduation_year: int,
    years_of_experience: float,
    skill_set: list[str],
) -> CandidateInput:
    try:
        return CandidateInput(
            full_name=full_name,
            dob=dob,
            contact_number=contact_number,
            contact_address=contact_address,
            education_qualification=education_qualification,
            graduation_year=graduation_year,
            years_of_experience=years_of_experience,
            skill_set=skill_set,
        )
    except ValidationError as exc:
        # Avoid non-serializable objects (e.g. ValueError in ctx.error) in HTTP error response.
        try:
            detail = exc.errors(include_url=False, include_context=False, include_input=False)
        except TypeError:
            detail = []
            for err in exc.errors():
                safe_err = dict(err)
                if "ctx" in safe_err and isinstance(safe_err["ctx"], dict):
                    safe_err["ctx"] = {k: str(v) for k, v in safe_err["ctx"].items()}
                if "input" in safe_err:
                    safe_err["input"] = str(safe_err["input"])
                detail.append(safe_err)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail) from exc


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/candidates", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    full_name: str = Form(...),
    dob: date = Form(...),
    contact_number: str = Form(...),
    contact_address: str = Form(...),
    education_qualification: str = Form(...),
    graduation_year: int = Form(...),
    years_of_experience: float = Form(...),
    skill_set: str = Form(..., description="Comma-separated skills. Example: Python, FastAPI, SQL"),
    resume: UploadFile = File(...),
) -> CandidateResponse:
    original_file_name = (resume.filename or "").strip()
    if not original_file_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resume file name is missing")

    extension = Path(original_file_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, DOC, and DOCX files are allowed",
        )

    parsed_skills = parse_skill_set(skill_set)
    candidate_input = validate_candidate_input(
        full_name=full_name,
        dob=dob,
        contact_number=contact_number,
        contact_address=contact_address,
        education_qualification=education_qualification,
        graduation_year=graduation_year,
        years_of_experience=years_of_experience,
        skill_set=parsed_skills,
    )

    resume_bytes = await resume.read()
    await resume.close()

    if not resume_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resume file cannot be empty")
    if len(resume_bytes) > MAX_RESUME_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Resume file exceeds {MAX_RESUME_SIZE_BYTES // (1024 * 1024)}MB limit",
        )

    candidate_id = str(uuid.uuid4())
    record: dict[str, Any] = {
        "id": candidate_id,
        "full_name": candidate_input.full_name,
        "dob": candidate_input.dob,
        "contact_number": candidate_input.contact_number,
        "contact_address": candidate_input.contact_address,
        "education_qualification": candidate_input.education_qualification,
        "graduation_year": candidate_input.graduation_year,
        "years_of_experience": candidate_input.years_of_experience,
        "skill_set": candidate_input.skill_set,
        "resume_file_name": original_file_name,
        "resume_content_type": resume.content_type or "application/octet-stream",
        "resume_bytes": resume_bytes,
        "created_at": datetime.utcnow(),
    }

    with store_lock:
        candidates[candidate_id] = record

    return build_response(record)


@app.get("/candidates", response_model=list[CandidateResponse], status_code=status.HTTP_200_OK)
def list_candidates(
    skill: str | None = Query(default=None, min_length=1),
    experience: float | None = Query(default=None, ge=0, le=60),
    graduation_year: int | None = Query(default=None, ge=1950, le=date.today().year + 1),
) -> list[CandidateResponse]:
    records = list(candidates.values())

    if skill:
        skill_lower = skill.strip().lower()
        records = [
            item
            for item in records
            if any(skill_lower in existing_skill.lower() for existing_skill in item["skill_set"])
        ]
    if experience is not None:
        records = [item for item in records if item["years_of_experience"] >= experience]
    if graduation_year is not None:
        records = [item for item in records if item["graduation_year"] == graduation_year]

    records.sort(key=lambda x: x["created_at"], reverse=True)
    return [build_response(item) for item in records]


@app.get("/candidates/{candidate_id}", response_model=CandidateResponse, status_code=status.HTTP_200_OK)
def get_candidate(candidate_id: str) -> CandidateResponse:
    record = candidates.get(candidate_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return build_response(record)


@app.delete("/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(candidate_id: str) -> Response:
    with store_lock:
        record = candidates.pop(candidate_id, None)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
