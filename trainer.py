import time
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from datetime import datetime
import yaml
from pathlib import Path

import memory
import shift_manager
import classifier
from outlook_watcher import fetch_recent_unread_emails

console = Console()

# Load config
config_path = Path("config.yaml")
if config_path.exists():
    with open(config_path, "r") as f:
        CONFIG = yaml.safe_load(f)
else:
    CONFIG = {"poll_interval": 60, "auto_mode_threshold": 0.85, "min_examples_required": 30}

def run_assisted_cycle():
    """Fetches emails and uses LLM for assisted triage."""
    processed = memory.get_processed_ids()
    emails = fetch_recent_unread_emails()
    
    for email in emails:
        entry_id = email["entry_id"]
        if entry_id in processed:
            continue
            
        console.print("\n" + "="*50)
        console.print(Panel(f"[bold cyan]Subject:[/bold cyan] {email['subject']}\n[bold cyan]Received:[/bold cyan] {email['received_time']}", title="New Alert (Assisted)"))
        
        body_snippet = email["body"][:300] + ("..." if len(email["body"]) > 300 else "")
        console.print(f"[dim]{body_snippet}[/dim]")
        
        # Check LLM
        with console.status("[bold blue]Thinking...[/bold blue]"):
            result = classifier.classify_alert(email["subject"], email["body"])
        
        # -----------------------------
        # Phase 3: Auto Mode Logic
        # -----------------------------
        history_len = len(memory.load_history())
        auto_threshold = float(CONFIG.get("auto_mode_threshold", 0.85))
        min_examples = int(CONFIG.get("min_examples_required", 30))
        
        if result:
            auto_active = shift_manager.is_auto_mode_active()
            if auto_active and history_len >= min_examples and result.confidence >= auto_threshold:
                console.print(f"[bold green]Auto-Classified:[/bold green] {result.decision} (Confidence: {result.confidence:.2f})")
                console.print(f"[italic]Reasoning:[/italic] {result.reason}")
                
                record = memory.TriageRecord(
                    timestamp=datetime.now().isoformat(),
                    subject=email["subject"],
                    body=email["body"],
                    decision=result.decision,
                    model_suggestion=result.decision,
                    confidence=result.confidence,
                    is_auto=True
                )
                memory.append_record(record)
                memory.mark_processed(entry_id)
                continue
        
        # -----------------------------
        # Phase 2: Assisted Logic
        # -----------------------------
        if result:
            color = "green" if result.decision == "Check" else "yellow"
            console.print(f"\n[bold magenta]AI Suggestion:[/bold magenta] [{color}]{result.decision}[/{color}] (Confidence: {result.confidence:.2f})")
            console.print(f"[bold magenta]Reason:[/bold magenta] {result.reason}\n")
        else:
            console.print("\n[bold red]Failed to get AI suggestion. Defaulting to manual triage.[/bold red]\n")
            
        decision_map = {"c": "Check", "i": "Ignore"}
        valid_input = False
        decision = ""
        while not valid_input:
            prompt_str = "[bold yellow]Action[/bold yellow] (\[C]heck / \[I]gnore / \[S]kip"
            if result:
                prompt_str += " / \[A]ccept Suggestion"
            prompt_str += ")"
                
            choice = Prompt.ask(prompt_str).lower()
            
            if choice == 'a' and result:
                decision = result.decision
                valid_input = True
            elif choice in ['c', 'i', 's']:
                valid_input = True
                if choice == 's':
                    console.print("[yellow]Skipping email.[/yellow]")
                    memory.mark_processed(entry_id)
                    break
                else:
                    decision = decision_map[choice]
            else:
                console.print("[red]Invalid choice.[/red]")
                
        if choice == 's':
            continue

        comment = Prompt.ask("Comment (optional)")
        
        # Save to history
        record = memory.TriageRecord(
            timestamp=datetime.now().isoformat(),
            subject=email["subject"],
            body=email["body"],
            decision=decision,
            model_suggestion=result.decision if result else None,
            confidence=result.confidence if result else None,
            comment=comment if comment else None,
            is_auto=False
        )
        memory.append_record(record)
        memory.mark_processed(entry_id)
        
        color = "green" if decision == "Check" else "yellow"
        console.print(f"[{color}]Saved: {decision}[/{color}]")

