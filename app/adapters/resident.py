import time
import httpx

from errors import SourceUnavailableError


class ResidentAdapter:
    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        max_retries: int = 1,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

    def get_by_id(self, resident_id: str):
        url = f"{self.base_url}/residents/{resident_id}"
        last_reason = "unknown error"

        for attempt in range(self.max_retries + 1):
            try:
                response = httpx.get(url, timeout=self.timeout)

                if response.status_code == 404:
                    return None  # resident genuinely does not exist

                if response.status_code >= 500:
                    last_reason = f"HTTP {response.status_code}"
                    if attempt < self.max_retries:
                        time.sleep(0.1)
                        continue
                    raise SourceUnavailableError("residents", last_reason)

                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException:
                last_reason = "timeout"
                if attempt < self.max_retries:
                    continue
                raise SourceUnavailableError("residents", last_reason)

            except httpx.RequestError:
                last_reason = "connection error"
                if attempt < self.max_retries:
                    continue
                raise SourceUnavailableError("residents", last_reason)

    def get_all(self):
        seen_ids: set = set()
        results = []
        page = 1

        while True:
            response = httpx.get(
                f"{self.base_url}/residents",
                params={"page": page},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            for r in data["results"]:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    results.append(r)

            if not data["has_more"]:
                break

            page += 1

        return results
