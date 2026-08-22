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