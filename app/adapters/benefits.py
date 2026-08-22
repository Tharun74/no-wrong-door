import httpx
import xml.etree.ElementTree as ET


class BenefitsAdapter:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def get_all(self):
        url = f"{self.base_url}/records"

        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()

        root = ET.fromstring(response.text)

        records = []

        for record in root.findall("Record"):
            records.append({
                "ref": record.findtext("Ref"),
                "name": record.findtext("Name"),
                "born": record.findtext("Born"),
                "address": record.findtext("Addr"),
                "town": record.findtext("Town"),
                "benefit_code": record.findtext("BenefitCode"),
                "review_due": record.findtext("ReviewDue")
            })

        return records