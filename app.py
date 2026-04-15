from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime

import outlook_watcher
import memory
import classifier

app = FastAPI(title="Trainable Alert Triage Web UI")

class EmailResponse(BaseModel):
    entry_id: str
    subject: str
    body: str
    html_body: str
    received_time: str

class TriageRequest(BaseModel):
    entry_id: str
    subject: str
    body: str
    decision: str
    comment: Optional[str] = None
    model_suggestion: Optional[str] = None
    confidence: Optional[float] = None

class ClassifyRequest(BaseModel):
    subject: str
    body: str

@app.get("/api/emails", response_model=List[EmailResponse])
def get_emails():
    try:
        processed = memory.get_processed_ids()
        all_emails = outlook_watcher.fetch_recent_unread_emails()
        
        # Filter processed
        pending_emails = [e for e in all_emails if e["entry_id"] not in processed]
        return pending_emails
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/classify")
def classify_email(req: ClassifyRequest):
    result = classifier.classify_alert(req.subject, req.body)
    if result:
        return {"suggestion": result.decision, "confidence": result.confidence, "reason": result.reason}
    return {"suggestion": None}

@app.post("/api/triage")
def triage_email(req: TriageRequest):
    record = memory.TriageRecord(
        timestamp=datetime.now().isoformat(),
        subject=req.subject,
        body=req.body,
        decision=req.decision,
        comment=req.comment,
        model_suggestion=req.model_suggestion,
        confidence=req.confidence,
        is_auto=False
    )
    memory.append_record(record)
    memory.mark_processed(req.entry_id)
    return {"status": "success"}

# Serve the static UI files under root
import os
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
