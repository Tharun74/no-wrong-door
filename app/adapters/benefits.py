import time
import httpx
import xml.etree.ElementTree as ET

from errors import SourceUnavailableError
class BenefitsAdapter:
    def __init__(
        self,
        base_url: str,
        timeout: float = 2.0,
        max_retries: int = 1
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

    def get_all(self):
        url = f"{self.base_url}/records"

        last_reason = "unknown error"

        for attempt in range(self.max_retries + 1):
            try:
                response = httpx.get(
                    url,
                    timeout=self.timeout
                )

                if response.status_code >= 500:
                    last_reason = f"HTTP {response.status_code}"

                    if attempt < self.max_retries:
                        time.sleep(0.1)
                        continue

                    raise SourceUnavailableError(
                        "benefits",
                        last_reason
                    )

                response.raise_for_status()

                root = ET.fromstring(response.text)

                return self._parse_records(root)

            except httpx.TimeoutException:
                last_reason = "timeout"

                if attempt < self.max_retries:
                    continue

                raise SourceUnavailableError(
                    "benefits",
                    last_reason
                )

            except httpx.RequestError as exc:
                last_reason = "connection error"

                if attempt < self.max_retries:
                    continue

                raise SourceUnavailableError(
                    "benefits",
                    last_reason
                )

            except ET.ParseError:
                raise SourceUnavailableError(
                    "benefits",
                    "invalid XML response"
                )

    def _parse_records(self, root):
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