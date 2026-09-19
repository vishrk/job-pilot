from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import companies, hunts, matches, profile

app = FastAPI(title="JobPilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile.router)
app.include_router(companies.router)
app.include_router(matches.router)
app.include_router(hunts.router)


@app.get("/health")
def health():
    return {"status": "ok"}
