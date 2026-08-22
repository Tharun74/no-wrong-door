from fastapi import FastAPI
from app.adapters.resident import ResidentAdapter

app = FastAPI(title = "No Wrong Door")

resident_adapter = ResidentAdapter("http://127.0.0.1:8081")

@app.get("/health")
def health():
    return { "status" : "ok" }

@app.get("/api/v1/residents/{resident_id}")
def get_resident(resident_id : str):
    resident = resident_adapter.get_by_id(resident_id)
    
    if resident is None:
        return {"error" : "resident not found"}
    
    return resident