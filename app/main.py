from fastapi import FastAPI

app = FastAPI(title = "No Wrong Door")

@app.get("/health")
def health():
    return { "status" : "ok" }