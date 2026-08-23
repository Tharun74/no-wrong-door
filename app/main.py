from fastapi import FastAPI, HTTPException

from app.adapters.resident import ResidentAdapter
from app.adapters.benefits import BenefitsAdapter
from services.resident_view import ResidentViewService
from errors import SourceUnavailableError


app = FastAPI(title="No Wrong Door")


resident_adapter = ResidentAdapter(
    "http://127.0.0.1:8081"
)

benefits_adapter = BenefitsAdapter(
    "http://127.0.0.1:8082",
    max_retries=2,
)

resident_view_service = ResidentViewService(
    resident_adapter,
    benefits_adapter
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/residents")
def list_residents():
    try:
        residents, partial, partial_reason = resident_adapter.get_all()
        if partial:
            resident_status = {
                "status": "degraded",
                "reason": f"pagination stopped early: {partial_reason}",
            }
        else:
            resident_status = {"status": "available"}
    except SourceUnavailableError as exc:
        residents = []
        resident_status = {"status": "unavailable", "reason": exc.reason}

    return {
        "count": len(residents),
        "residents": residents,
        "sources": {
            "residents": resident_status,
        },
    }


@app.get("/api/v1/residents/{resident_id}")
def get_resident(resident_id: str):

    result = resident_view_service.get_resident_view(
        resident_id
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Resident not found"
        )

    return result

@app.get("/api/v1/benefits")
def list_benefits():
    try:
        benefits = benefits_adapter.get_all()
        benefits_status = {"status": "available"}
    except SourceUnavailableError as exc:
        benefits = []
        benefits_status = {"status": "unavailable", "reason": exc.reason}

    return {
        "count": len(benefits),
        "benefits": benefits,
        "sources": {
            "benefits": benefits_status,
        },
    }