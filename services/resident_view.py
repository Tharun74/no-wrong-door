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
        """
        Assemble a unified view of one resident from both sources.

        Degradation policy
        ------------------
        - Resident source returns 404  → return None so the caller can issue a
          proper 404 to the client.  The resident is confirmed not to exist.
        - Resident source is unavailable → return a partial view with
          resident: null and sources.residents.status = "unavailable".
          We still attempt benefits so the caller gets as much as possible.
        - Benefits source is unavailable → return resident data with
          benefits: null and sources.benefits.status = "unavailable".
        - Both sources unavailable → return both as null with both statuses set.
          The caller always gets a 200 with a machine-readable explanation.
        """

        # --- resident source ---
        try:
            resident = self.resident_adapter.get_by_id(resident_id)

            if resident is None:
                # Confirmed not found — propagate so caller returns 404.
                return None

            resident_status = {"status": "available"}

        except SourceUnavailableError as exc:
            # Cannot confirm existence; return partial rather than an error.
            resident = None
            resident_status = {"status": "unavailable", "reason": exc.reason}

        # --- benefits source (always attempted, even if resident failed) ---
        try:
            benefits = self.benefits_adapter.get_all()
            benefits_status = {"status": "available"}

        except SourceUnavailableError as exc:
            benefits = None
            benefits_status = {"status": "unavailable", "reason": exc.reason}

        return {
            "resident": resident,
            "benefits": benefits,
            "sources": {
                "residents": resident_status,
                "benefits": benefits_status,
            },
        }