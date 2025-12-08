from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import random
import time
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('civicflow.db')
    c = conn.cursor()
    
    # ADDED 'description' column
    c.execute('''CREATE TABLE IF NOT EXISTS reports 
                 (id INTEGER PRIMARY KEY, location TEXT, issue TEXT, description TEXT,
                  sentiment_score REAL, priority_score INTEGER, status TEXT, timestamp TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS services 
                 (id INTEGER PRIMARY KEY, name TEXT, category TEXT, location_context TEXT, description TEXT)''')
    
    c.execute("SELECT count(*) FROM services")
    if c.fetchone()[0] == 0:
        services = [
            ("Free E-Library", "Education", "School Zone", "Digital access to books for students."),
            ("Scholarship Desk", "Education", "School Zone", "Apply for govt grants here."),
            ("Jan Aushadhi Kendra", "Health", "Hospital Area", "Generic medicines at 90% discount."),
            ("Emergency Blood Bank", "Health", "Hospital Area", "24/7 Plasma availability."),
            ("Senior Citizen Park", "Recreation", "Residential Area", "Walking tracks and yoga mats."),
            ("Free WiFi Zone", "Connectivity", "Marketplace", "High-speed public internet."),
        ]
        c.executemany("INSERT INTO services (name, category, location_context, description) VALUES (?,?,?,?)", services)
        print("[SYSTEM] Database initialized with Service Data.")

    conn.commit()
    conn.close()

init_db()

# --- UPDATED DATA MODEL ---
class ReportModel(BaseModel):
    location: str
    issue: str
    description: str  # <--- NEW FIELD
    sentiment_score: float

class LocationRequest(BaseModel):
    location: str

@app.get("/")
def read_root():
    return {"status": "System Online", "message": "CivicFlow AI Backend is Running"}

@app.post("/submit_report")
def submit_report(data: ReportModel):
    print(f"\n[INCOMING] Report: {data.issue} at {data.location}")
    time.sleep(0.2)
    
    score = 10 
    
    # --- LAYER 1: CONTEXT ---
    if data.location in ["School Zone", "Hospital Area"]:
        score += 50
        print(f"[AI CONTEXT] CRITICAL ZONE: {data.location} (+50 Risk)")
    elif data.location == "Main Highway":
        score += 30
        print(f"[AI CONTEXT] High Traffic Zone (+30 Risk)")
    else:
        print(f"[AI CONTEXT] Routine Zone.")
        
    # --- LAYER 2: SEMANTICS (Now checks Description too!) ---
    dangerous_keywords = ["Gas", "Leak", "Fire", "Spark", "Wire", "Manhole", "Explosion", "Accident", "Blood", "Smoke"]
    
    # Check Issue AND Description for danger
    full_text = f"{data.issue} {data.description}"
    is_dangerous = any(word.lower() in full_text.lower() for word in dangerous_keywords)
    
    if is_dangerous:
        score += 40
        print(f"[AI SEMANTICS] DANGER DETECTED in description/issue (+40 Risk)")
    else:
        print(f"[AI SEMANTICS] Classified as Routine.")
        
    # --- LAYER 3: SENTIMENT ---
    score += int(data.sentiment_score * 10)
    
    final_score = min(score, 100)
    print(f"[AI RESULT] Priority Score: {final_score}/100")
    
    # SAVE TO DB (Includes description)
    conn = sqlite3.connect('civicflow.db')
    c = conn.cursor()
    c.execute("INSERT INTO reports (location, issue, description, sentiment_score, priority_score, status, timestamp) VALUES (?,?,?,?,?,?,?)",
              (data.location, data.issue, data.description, data.sentiment_score, final_score, "Pending", datetime.now().strftime("%H:%M:%S")))
    conn.commit()
    conn.close()
    
    return {"message": "Success", "priority": final_score}

@app.post("/find_services")
def find_services(req: LocationRequest):
    conn = sqlite3.connect('civicflow.db')
    c = conn.cursor()
    c.execute("SELECT name, category, description FROM services WHERE location_context = ?", (req.location,))
    rows = c.fetchall()
    conn.close()
    return [{"name": r[0], "category": r[1], "desc": r[2]} for r in rows]

@app.get("/admin_stats")
def get_stats():
    conn = sqlite3.connect('civicflow.db')
    c = conn.cursor()
    # Now fetching description as well
    c.execute("SELECT * FROM reports ORDER BY priority_score DESC LIMIT 10")
    rows = c.fetchall()
    
    c.execute("SELECT COUNT(*) FROM reports WHERE priority_score > 80")
    critical_count = c.fetchone()[0]
    conn.close()
    
    # Row index 3 corresponds to 'description' based on CREATE TABLE order
    reports = [{"id": r[0], "loc": r[1], "issue": r[2], "desc": r[3], "score": r[5], "status": r[6]} for r in rows]
    return {"reports": reports, "critical": critical_count}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="127.0.0.1", port=8000, reload=True)