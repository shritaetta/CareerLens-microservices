from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
import io
import os
import shutil
import uuid
import PyPDF2
import hashlib
from data_loader import loader
import database
from resume_enhancer import ResumeEnhancer

enhancer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global enhancer
    loader.load_data()
    database.init_db()
    enhancer = ResumeEnhancer(loader.model)
    yield

app = FastAPI(
    title="Internship Semantic Recommendation API with Feedback",
    lifespan=lifespan
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-Memory Feedback Store
# Structure: { "user_id": { "exclude_locations": [], "min_stipend": 0, "exclude_domains": [], "exclude_durations": [], "exclude_ids": [] } }
feedback_store: Dict[str, Dict[str, Any]] = {}

class ProfileRequest(BaseModel):
    user_id: str = "default_user"  # Fallback since frontend isn't logged in deeply
    skills: List[str]
    education: Optional[str] = ""
    achievements: Optional[str] = ""
    resume_text: Optional[str] = ""
    certificate_text: Optional[str] = ""

class FeedbackRequest(BaseModel):
    user_id: str = "default_user"
    internship_id: str
    reason: str
    metadata: Dict[str, Any] = {} # e.g. location, stipend string, domain etc

class SignupRequest(BaseModel):
    full_name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def keep_alive():
    return {"status": "ok", "message": "Recommendation API with Feedback Loop is running."}

@app.post("/signup")
def signup(request: SignupRequest):
    pwd_hash = hash_password(request.password)
    success = database.create_user(request.email, request.full_name, pwd_hash)
    if not success:
        return {"error": "Email already registered"}
    return {"status": "success", "user_id": request.email}

@app.post("/login")
def login(request: LoginRequest):
    user = database.get_user(request.email)
    if not user:
        return {"error": "Invalid email or password"}
    
    pwd_hash = hash_password(request.password)
    if user["password"] != pwd_hash:
        return {"error": "Invalid email or password"}
        
    return {"status": "success", "user_id": request.email}

@app.get("/internships/light")
def get_lightweight_internships():
    """Returns only ID and Title for dropdowns."""
    return loader.get_all_light()

class ATSEvaluationRequest(BaseModel):
    resume_text: str
    internship_id: str
    user_skills: List[str]

@app.post("/evaluate_ats")
def evaluate_resume_ats(request: ATSEvaluationRequest):
    return loader.evaluate_ats(
        resume_text=request.resume_text,
        internship_id=request.internship_id,
        user_skills=request.user_skills
    )

@app.post("/extract_pdf")
async def extract_pdf_text(file: UploadFile = File(...)):
    """Extracts raw string text from an uploaded PDF binary"""
    if not file.filename.lower().endswith('.pdf'):
        return {"error": "Uploaded file must be a PDF document."}
        
    try:
        content = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        return {"filename": file.filename, "extracted_text": text.strip()}
    except Exception as e:
        return {"error": str(e)}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Saves generic physical file and returns a static URL endpoint"""
    try:
        ext = os.path.splitext(file.filename or "")[1]
        saved_filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(UPLOAD_DIR, saved_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {
            "filename": saved_filename, 
            "url": f"/uploads/{saved_filename}"
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/feedback")
def handle_feedback(feedback: FeedbackRequest):
    uid = feedback.user_id
    if uid not in feedback_store:
        feedback_store[uid] = {
            "exclude_locations": [],
            "min_stipend": -1,
            "exclude_domains": [],
            "exclude_durations": [],
            "exclude_ids": []
        }
        
    user_constraints = feedback_store[uid]
    reason = feedback.reason
    
    # Process constraint based on reason
    if reason == "location_not_suitable":
        loc = feedback.metadata.get("location")
        if loc and loc not in user_constraints["exclude_locations"]:
            user_constraints["exclude_locations"].append(loc)
            
    elif reason == "low_stipend":
        # Extract numerical value from metadata
        from data_loader import parse_numeric_stipend
        current_numeric = parse_numeric_stipend(feedback.metadata.get("stipend", '0'))
        if current_numeric > user_constraints["min_stipend"]:
            user_constraints["min_stipend"] = current_numeric
            
    elif reason == "not_my_domain":
        dom = feedback.metadata.get("domain")
        if dom and dom not in user_constraints["exclude_domains"]:
            user_constraints["exclude_domains"].append(dom)
            
    elif reason == "duration_not_suitable":
        dur = feedback.metadata.get("duration")
        if dur and dur not in user_constraints["exclude_durations"]:
            user_constraints["exclude_durations"].append(dur)
            
    elif reason == "skills_mismatch":
        # Cannot easily skew complex embeddings dynamically, so we strictly ban this ID
        pass 
        
    # Always ban the specific ID if they disliked it
    user_constraints["exclude_ids"].append(str(feedback.internship_id))
    
    return {"status": "success", "constraints_updated": True, "active_constraints": user_constraints}


@app.post("/recommend")
def recommend_internships(profile: ProfileRequest):
    unified_text_parts = []
    
    if profile.skills:
        unified_text_parts.append(f"Skills: {', '.join(profile.skills)}")
    if profile.education:
        unified_text_parts.append(f"Education: {profile.education}")
    if profile.achievements:
        unified_text_parts.append(f"Achievements: {profile.achievements}")
    if profile.resume_text:
        unified_text_parts.append(f"Resume: {profile.resume_text}")
    if profile.certificate_text:
        unified_text_parts.append(f"Certificates: {profile.certificate_text}")
        
    unified_profile_text = " | ".join(unified_text_parts)
    
    # Fetch user constraints
    uid = profile.user_id
    constraints = feedback_store.get(uid, {})
    
    # Fetch recommendations with Constraints logic applied
    recommendations = loader.get_recommendations(unified_profile_text, top_n=3, constraints=constraints)
    return recommendations

@app.get("/profile/{user_id}")
def get_user_profile(user_id: str):
    profile = database.get_profile(user_id)
    if not profile:
        return {"error": "Profile not found"}
    return {"user_id": user_id, "profile_data": profile}

@app.post("/profile/{user_id}")
def save_user_profile(user_id: str, payload: Dict[str, Any]):
    database.save_profile(user_id, payload)
    return {"status": "success"}

@app.post("/enhance_profile")
def enhance_profile(payload: Dict[str, Any]):
    if not enhancer:
        return {"error": "Enhancer not initialized"}
    try:
        enhanced = enhancer.process_profile(payload)
        return {"status": "success", "enhanced_profile": enhanced}
    except Exception as e:
        return {"error": str(e)}
