# Trainable Alert Triage Agent

A lightweight, local-first AI system that monitors a specific Microsoft Outlook folder for alert emails. It uses a human-in-the-loop approach with few-shot learning to gradually automate the classification of alerts ("Check" vs "Ignore").

## Features
- **Local Outlook Monitoring**: Uses `pywin32` to connect to your local Outlook client and poll the designated folder without needing MS Graph API.
- **Assisted Triage (Phase 2)**: Retrieves similar past alerts and queries an LLM (Gemini or Bedrock) for a suggestion.
- **Auto Classification (Phase 3)**: Fully auto-classifies alerts if the LLM's confidence exceeds a set threshold and enough manual examples exist.
- **Shift Management**: Provides commands like `start-shift` and `end-shift` to only poll during active work hours.
- **Local Memory**: Stores all triage history in a simple `jsonl` file (`data/triage_history.jsonl`).

## Requirements
- Windows OS (with Microsoft Outlook installed).
- Python 3.9+
- An API key for Claude via AWS Bedrock, or Google Gemini.

## Setup Instructions

1. **Install Dependencies**
   Run the following command in your terminal:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Settings**
   Edit the `config.yaml` to specify:
   - `outlook_folder`: The folder to monitor. (e.g. `Inbox`, `Inbox/Alerts`)
   - `subject_regex`: Filters emails. Leave blank or use patterns like `^(?i)(alert|warning)`
   - `llm_provider`: Choose `gemini` or `bedrock`.
   - `model_name`: Set the appropriate model name.

3. **Set up Environment Variables**
   Copy the `.`env.example` file and configure it:
   ```bash
   cp .env.example .env
   ```
   Add your respective API keys.

## Commands / How to Run

Use `python cli.py --help` for available commands.

**1. Start Manual Shift**
Monitors the folder and asks you to triage incoming matching alerts.
```bash
python cli.py start-shift
```

**2. End Shift**
Gracefully marks the shift as ended.
```bash
python cli.py end-shift
```

**3. Train / Assisted Mode**
Like `start-shift`, but asks the LLM for suggestions first based on past triaged history.
```bash
python cli.py train
```

**4. Toggle Auto mode**
Enables or disables Phase 3 fully automated triage.
```bash
python cli.py auto-on
python cli.py auto-off
```

**5. Review Automations**
See the recent auto-classified items.
```bash
python cli.py review-last 10
```

**6. Status**
Shows the current state of shifts and amount of memories gathered.
```bash
python cli.py status
```
