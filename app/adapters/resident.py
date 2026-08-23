import httpx

class ResidentAdapter:
    def __init__(self, baseUrl : str):
        self.baseUrl = baseUrl
    
    def get_by_id(self, resident_id : str):
        url = f"{self.baseUrl}/residents/{resident_id}"
        response = httpx.get(url)
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        
        return response.json()
    
    def get_all(self):
        seen_ids = set()
        results = []
        page = 1
        while True:
            response = httpx.get(f"{self.baseUrl}/residents", params={"page": page}, timeout=5.0)
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
