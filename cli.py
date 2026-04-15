import time
import typer
import yaml
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from datetime import datetime

import shift_manager
import memory
import trainer
from outlook_watcher import fetch_recent_unread_emails

app = typer.Typer(help="Trainable Alert Triage Agent")
console = Console()

# Load config
config_path = Path("config.yaml")
if config_path.exists():
    with open(config_path, "r") as f:
        CONFIG = yaml.safe_load(f)
else:
    CONFIG = {"poll_interval": 60}

# Processed state is now in memory.py

@app.command()
def start_shift():
    """Start shift and begin monitoring Outlook for alerts."""
    if not shift_manager.start_shift():
        console.print("[bold yellow]Shift is already active.[/bold yellow]")
        return
    
    console.print(f"[bold green]Shift started at {datetime.now().strftime('%H:%M:%S')}. Monitoring...[/bold green]")
    poll_interval = CONFIG.get("poll_interval", 60)
    
    try:
        while True:
            # Check if shift was ended externally
            if not shift_manager.is_shift_active():
                console.print("[bold yellow]Shift was ended externally. Stopping monitor.[/bold yellow]")
                break
                
            run_triage_cycle()
            time.sleep(poll_interval)
            
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Stopping monitor...[/bold yellow]")
        shift_manager.end_shift()
        console.print("[bold green]Shift ended.[/bold green]")

@app.command()
def end_shift():
    """End the current shift."""
    if shift_manager.end_shift():
        console.print("[bold green]Shift ended successfully.[/bold green]")
    else:
        console.print("[bold yellow]No active shift to end.[/bold yellow]")

@app.command()
def status():
    """Check the current status of the agent."""
    state = shift_manager.load_state()
    active = state.get("shift_active", False)
    status_msg = "[bold green]Active[/bold green]" if active else "[bold red]Inactive[/bold red]"
    console.print(f"Shift Status: {status_msg}")
    if active:
        console.print(f"Started At: {state.get('shift_start')}")
    console.print(f"Auto Mode: {state.get('auto_mode', False)}")
    
    history = memory.load_history()
    console.print(f"Total Triaged Alerts: {len(history)}")

def run_triage_cycle():
    """Fetches emails and prompts user for manual triage."""
    processed = memory.get_processed_ids()
    emails = fetch_recent_unread_emails()
    
    for email in emails:
        entry_id = email["entry_id"]
        if entry_id in processed:
            continue
            
        # Display Email
        console.print("\n" + "="*50)
        console.print(Panel(f"[bold cyan]Subject:[/bold cyan] {email['subject']}\n[bold cyan]Received:[/bold cyan] {email['received_time']}", title="New Alert"))
        
        # Snippet
        body_snippet = email["body"][:300] + ("..." if len(email["body"]) > 300 else "")
        console.print(f"[dim]{body_snippet}[/dim]")
        
        # Ask for Triage
        decision_map = {"c": "Check", "i": "Ignore"}
        valid_input = False
        decision = ""
        while not valid_input:
            choice = Prompt.ask("[bold yellow]Triage Action[/bold yellow] (\[C]heck / \[I]gnore / \[S]kip)").lower()
            if choice in ['c', 'i', 's']:
                valid_input = True
                if choice == 's':
                    console.print("[yellow]Skipping email.[/yellow]")
                    memory.mark_processed(entry_id)
                    continue
                else:
                    decision = decision_map[choice]
            else:
                console.print("[red]Invalid choice. Enter C, I, or S.[/red]")
        
        if choice == 's':
            continue

        comment = Prompt.ask("Comment (optional)")
        
        # Save to history
        record = memory.TriageRecord(
            timestamp=datetime.now().isoformat(),
            subject=email["subject"],
            body=email["body"],
            decision=decision,
            comment=comment if comment else None
        )
        memory.append_record(record)
        memory.mark_processed(entry_id)
        
        color = "green" if decision == "Check" else "yellow"
        console.print(f"[{color}]Saved: {decision}[/{color}]")

@app.command()
def train():
    """Start shift in assisted mode (Phase 2), utilizing LLM suggestions."""
    if not shift_manager.start_shift():
        console.print("[bold yellow]Shift is already active. Please end the current shift to restart in train mode.[/bold yellow]")
        return
        
    console.print(f"[bold green]Train Mode Shift started at {datetime.now().strftime('%H:%M:%S')}. Monitoring...[/bold green]")
    poll_interval = CONFIG.get("poll_interval", 60)
    
    try:
        while True:
            if not shift_manager.is_shift_active():
                console.print("[bold yellow]Shift ended externally.[/bold yellow]")
                break
                
            trainer.run_assisted_cycle()
            time.sleep(poll_interval)
            
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Stopping monitor...[/bold yellow]")
        shift_manager.end_shift()
        console.print("[bold green]Shift ended.[/bold green]")

@app.command()
def auto_on():
    """Enable automatic classification (Phase 3)."""
    shift_manager.toggle_auto_mode(True)
    console.print("[bold green]Auto mode ENABLED.[/bold green]")
    
@app.command()
def auto_off():
    """Disable automatic classification."""
    shift_manager.toggle_auto_mode(False)
    console.print("[bold yellow]Auto mode DISABLED.[/bold yellow]")

@app.command()
def review_last(n: int = 5):
    """Review the last N auto-classified items."""
    history = memory.load_history()
    auto_items = [r for r in history if r.is_auto]
    
    if not auto_items:
        console.print("No auto-classified items found.")
        return
        
    for item in auto_items[-n:]:
        console.print("\n" + "-"*40)
        console.print(f"[cyan]Time:[/cyan] {item.timestamp}")
        console.print(f"[cyan]Subject:[/cyan] {item.subject}")
        console.print(f"[cyan]Decision:[/cyan] {item.decision} (Confidence: {item.confidence})")


if __name__ == "__main__":
    app()
