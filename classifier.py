import os
import json
import yaml
import requests
from pathlib import Path
from rapidfuzz import process, fuzz
from typing import List, Dict, Optional
from pydantic import BaseModel, ValidationError

import memory

# Load config
config_path = Path("config.yaml")
if config_path.exists():
    with open(config_path, "r") as f:
        CONFIG = yaml.safe_load(f)
else:
    CONFIG = {"llm_provider": "gemini", "model_name": "gemini-1.5-pro-latest"}

class ClassifierResult(BaseModel):
    decision: str
    confidence: float
    reason: str

def get_similar_examples(new_subject: str, new_body: str, top_k: int = 5) -> List[memory.TriageRecord]:
    """Find the top_k most similar past examples using rapidfuzz."""
    history = memory.load_history()
    if not history:
        return []
    
    # Simple similarity based on subject mostly, and a bit of body
    # We will score each record
    scored_records = []
    for record in history:
        subject_score = fuzz.ratio(new_subject.lower(), record.subject.lower())
        # Truncate body for faster comparison
        body_score = fuzz.ratio(new_body[:500].lower(), record.body[:500].lower())
        
        # Weighted score (subject is more important)
        final_score = (subject_score * 0.7) + (body_score * 0.3)
        scored_records.append((final_score, record))
        
    scored_records.sort(key=lambda x: x[0], reverse=True)
    return [rec for score, rec in scored_records[:top_k]]

def build_prompt(new_subject: str, new_body: str, examples: List[memory.TriageRecord]) -> str:
    prompt = "You are an AI assistant that triages system alerts.\n"
    prompt += "Your task is to classify the new alert into 'Check' or 'Ignore' based on past examples.\n\n"
    
    if examples:
        prompt += "### Past Examples ###\n"
        for i, ex in enumerate(examples):
            prompt += f"Example {i+1}:\n"
            prompt += f"Subject: {ex.subject}\n"
            prompt += f"Body Snippet: {ex.body[:300]}\n"
            prompt += f"Decision: {ex.decision}\n"
            if ex.comment:
                prompt += f"Human Comment: {ex.comment}\n"
            prompt += "\n"
            
    prompt += "### New Alert to Triage ###\n"
    prompt += f"Subject: {new_subject}\n"
    prompt += f"Body: {new_body}\n\n"
    prompt += "Instructions:\n"
    prompt += "1. Output valid JSON only.\n"
    prompt += "2. The JSON must have the following keys: 'decision' (exactly 'Check' or 'Ignore'), 'confidence' (float 0-1), 'reason' (short string).\n"
    prompt += "3. Prefer 'Check' if you are unsure.\n"
    return prompt

def call_gemini(prompt: str) -> Optional[ClassifierResult]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found in environment.")
        return None
        
    model = CONFIG.get("model_name", "gemini-1.5-pro-latest")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }
    
    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        data = resp.json()
        
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        result_dict = json.loads(text)
        return ClassifierResult(**result_dict)
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return None

def call_bedrock(prompt: str) -> Optional[ClassifierResult]:
    import boto3
    try:
        client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        model_id = CONFIG.get("model_name", "anthropic.claude-3-haiku-20240307-v1:0")
        
        # Simple converse API wrapper
        messages = [{"role": "user", "content": [{"text": prompt + "\n\nOutput only JSON."}]}]
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": messages
        })
        
        resp = client.invoke_model(
            modelId=model_id,
            body=body,
            contentType="application/json",
            accept="application/json"
        )
        
        response_body = json.loads(resp.get("body").read().decode("utf-8"))
        text = response_body["content"][0]["text"]
        
        # Simple extraction if bounded by backticks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            
        result_dict = json.loads(text)
        return ClassifierResult(**result_dict)
    except Exception as e:
        print(f"Error calling Bedrock: {e}")
        return None

def classify_alert(new_subject: str, new_body: str) -> Optional[ClassifierResult]:
    examples = get_similar_examples(new_subject, new_body, top_k=5)
    prompt = build_prompt(new_subject, new_body, examples)
    
    provider = CONFIG.get("llm_provider", "gemini").lower()
    
    if provider == "gemini":
        return call_gemini(prompt)
    elif provider == "bedrock":
        return call_bedrock(prompt)
    else:
        print(f"Unknown provider: {provider}")
        return None
