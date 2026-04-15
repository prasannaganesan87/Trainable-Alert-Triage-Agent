# Trainable Alert Triage Agent

A sleek, local-first AI system that monitors a specific Microsoft Outlook folder for alert emails. It uses a human-in-the-loop approach with few-shot learning to gradually automate the classification of alerts ("Check" vs "Ignore").

## Architecture
- **Web UI (`app.py`)**: Built with FastAPI. Provides a beautiful dark-mode interface to quickly visualize emails and triage them, complete with AI suggestions.
- **Local Outlook Monitoring**: Uses `pywin32` to connect to your local Outlook client and poll the designated folder without needing MS Graph API.
- **Local Memory**: Stores all triage history in a simple `jsonl` file (`data/triage_history.jsonl`).

## Requirements
- Windows OS (with Microsoft Outlook client installed).
- Python 3.9+
- An API key for Google Gemini (or AWS Bedrock).

## Setup Instructions

1. **Install Dependencies**
   Run the following command in your terminal:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Settings**
   Edit the `config.yaml` to specify:
   - `outlook_folder`: The folder to monitor. (e.g. `Inbox/SRE/Dynatrace alerts`)
   - `filter_minutes`: The time window to look back for emails (default `60`).
   - `llm_provider`: Choose `gemini` or `bedrock`.

3. **Set up Environment Variables**
   Copy the `.env.example` file to create a new `.env` file:
   ```bash
   cp .env.example .env
   ```
   Insert your API keys inside `.env`.

## How to Run

Launch the local web server using Uvicorn:
```bash
uvicorn app:app --reload --port 3000
```
Then, open your browser and go to `http://localhost:3000` to access the Triage Dashboard!
