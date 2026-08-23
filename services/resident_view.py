from app.adapters.resident import ResidentAdapter
from app.adapters.benefits import BenefitsAdapter
from errors import SourceUnavailableError
from services.matching import build_match_index, match_resident

class ResidentViewService:

    def __init__(
        self,
        resident_adapter: ResidentAdapter,
        benefits_adapter: BenefitsAdapter,
    ):
        self.resident_adapter = resident_adapter
        self.benefits_adapter = benefits_adapter

    def get_resident_view(self, resident_id: str):
        try:
            resident = self.resident_adapter.get_by_id(resident_id)

            if resident is None:
                return None

            resident_status = {"status": "available"}

        except SourceUnavailableError as exc:
            resident = None
            resident_status = {"status": "unavailable", "reason": exc.reason}

        benefits_status = {
            "status": "not_linked",
            "reason": "no shared identifier between sources; matching not attempted",
        }

        matched_benefits = None
        matched_benefits_status = {"status": "not_attempted"}

        if resident is not None:
            try:
                benefits_records = self.benefits_adapter.get_all()
                match_index = build_match_index(benefits_records)
                record, match_status, reason = match_resident(resident, match_index)

                matched_benefits = record
                matched_benefits_status = {"status": match_status, "reason": reason}

            except SourceUnavailableError as exc:
                matched_benefits_status = {
                    "status": "unavailable",
                    "reason": f"could not attempt matching: {exc.reason}",
                }

        return {
            "resident": resident,
            "benefits": None,
            "matched_benefits": matched_benefits,
            "sources": {
                "residents": resident_status,
                "benefits": benefits_status,
                "matched_benefits": matched_benefits_status,
            },
        }