import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Models ----------
class ProjectIn(BaseModel):
    title: str = Field(...)
    image: str = Field(...)
    location: Optional[str] = None
    year: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class Project(ProjectIn):
    id: str


class ContactIn(BaseModel):
    name: str
    email: EmailStr
    message: str


class Contact(ContactIn):
    id: str


# ---------- Helpers ----------
def serialize_doc(doc: dict) -> dict:
    d = dict(doc)
    if d.get("_id") is not None:
        d["id"] = str(d.pop("_id"))
    # Convert datetime fields to isoformat strings if present
    for k in ("created_at", "updated_at"):
        if k in d and hasattr(d[k], "isoformat"):
            d[k] = d[k].isoformat()
    return d


def ensure_seed_projects() -> None:
    if db is None:
        return
    count = db["projects"].count_documents({})
    if count == 0:
        seed = [
            {
                "title": "Casa Horizonte",
                "image": "https://images.unsplash.com/photo-1494526585095-c41746248156?q=80&w=1600&auto=format&fit=crop",
                "location": "Monterey, CA",
                "year": "2023",
                "tags": ["Residential", "Coastal"],
                "description": "A cliffside residence framing expansive Pacific views through disciplined apertures and warm concrete."
            },
            {
                "title": "Gallery of Light",
                "image": "https://images.unsplash.com/photo-1487956382158-bb926046304a?q=80&w=1600&auto=format&fit=crop",
                "location": "Santa Fe, NM",
                "year": "2022",
                "tags": ["Cultural"],
                "description": "Adaptive reuse gallery washed in high desert light with calibrated roof lanterns."
            },
            {
                "title": "Courtyard House",
                "image": "https://images.unsplash.com/photo-1487958449943-2429e8be8625?q=80&w=1600&auto=format&fit=crop",
                "location": "Austin, TX",
                "year": "2021",
                "tags": ["Residential", "Courtyard"],
                "description": "A quiet inward-facing plan organized around a planted court and deep overhangs."
            },
            {
                "title": "Cliffside Studio",
                "image": "https://images.unsplash.com/photo-1502005229762-cf1b2da7c3f5?q=80&w=1600&auto=format&fit=crop",
                "location": "Big Sur, CA",
                "year": "2020",
                "tags": ["Studio"],
                "description": "A minimal artist studio perched on a rocky outcrop, tuned to the horizon."
            },
        ]
        # add timestamps similar to create_document
        from datetime import datetime, timezone
        for s in seed:
            s["created_at"] = datetime.now(timezone.utc)
            s["updated_at"] = datetime.now(timezone.utc)
        db["projects"].insert_many(seed)


# ---------- Routes ----------
@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


@app.get("/projects", response_model=List[Project])
def list_projects():
    ensure_seed_projects()
    docs = get_documents("projects")
    # sort by year desc if present
    try:
        docs.sort(key=lambda d: int(d.get("year", 0)), reverse=True)
    except Exception:
        pass
    return [serialize_doc(d) for d in docs]


@app.post("/projects", response_model=Project, status_code=201)
def create_project(project: ProjectIn):
    inserted_id = create_document("projects", project)
    created = db["projects"].find_one({"_id": ObjectId(inserted_id)})
    return serialize_doc(created)


@app.post("/contact", response_model=Contact, status_code=201)
def submit_contact(data: ContactIn):
    inserted_id = create_document("contacts", data)
    created = db["contacts"].find_one({"_id": ObjectId(inserted_id)})
    return serialize_doc(created)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
