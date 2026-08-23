from app.adapters.resident import ResidentAdapter
from app.adapters.benefits import BenefitsAdapter
from errors import SourceUnavailableError


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

        return {
            "resident": resident,
            "benefits": None,
            "sources": {
                "residents": resident_status,
                "benefits": benefits_status,
            },
        }