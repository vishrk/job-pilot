from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import answers, companies, documents, form_maps, hunts, matches, profile

app = FastAPI(title="JobPilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_origin_regex=r"chrome-extension://.*",  # the extension calls this API cross-origin
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile.router)
app.include_router(companies.router)
app.include_router(matches.router)
app.include_router(hunts.router)
app.include_router(documents.router)
app.include_router(form_maps.router)
app.include_router(answers.router)


@app.get("/health")
def health():
    return {"status": "ok"}
