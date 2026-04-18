import win32com.client
import datetime
import re
import yaml
from pathlib import Path

# Load config
config_path = Path("config.yaml")
if config_path.exists():
    with open(config_path, "r") as f:
        CONFIG = yaml.safe_load(f)
else:
    CONFIG = {"outlook_folder": "Inbox", "subject_regex": "(?i)^(alert|warning|critical|issue)"}

def get_outlook_folder(namespace, folder_path: str):
    """
    Navigate to a specific folder within Outlook. 
    folder_path could be just 'Inbox' or 'Inbox/Alerts'.
    """
    try:
        parts = folder_path.replace("\\", "/").split("/")
        
        if parts[0].lower() == "inbox":
            folder = namespace.GetDefaultFolder(6)
            parts = parts[1:]
        elif parts[0].lower() == "deleted items":
            folder = namespace.GetDefaultFolder(3)
            parts = parts[1:]
        else:
            try:
                # Try from root namespace if not Inbox
                folder = namespace.Folders.Item(parts[0])
                parts = parts[1:]
            except Exception:
                # Fallback to Inbox
                folder = namespace.GetDefaultFolder(6)
                
        for part in parts:
            if part:
                folder = folder.Folders.Item(part)
        return folder
    except Exception as e:
        print(f"Error accessing folder '{folder_path}' (Are you sure it exists exactly as spelled?): {e}")
        return None

def fetch_recent_unread_emails() -> list:
    """
    Connects to Outlook and returns unread emails matching the subject regex
    and received within the last 5 minutes.
    """
    import pythoncom
    try:
        pythoncom.CoInitialize()
        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    except Exception as e:
        print(f"Failed to connect to Outlook: {e}")
        return []

    folder = get_outlook_folder(outlook, CONFIG.get("outlook_folder", "Inbox"))
    if not folder:
        return []

    items = folder.Items
    items.Sort("[ReceivedTime]", True) # Sort descending by date
    
    subject_pattern = CONFIG.get("subject_regex", "")
    regex = re.compile(subject_pattern) if subject_pattern else None

    # Lookback window for emails
    lookback_minutes = int(CONFIG.get("filter_minutes", 60))
    now = datetime.datetime.now()
    time_limit = now - datetime.timedelta(minutes=lookback_minutes)
    
    # Format time limit for Outlook Classic Restrict: "MM/DD/YYYY HH:MM AM"
    time_filter_str = time_limit.strftime("%m/%d/%Y %I:%M %p")
    
    try:
        # Offload filtering directly to Outlook Classic's COM interface
        restricted_items = folder.Items.Restrict(f"[UnRead] = True AND [ReceivedTime] >= '{time_filter_str}'")
        restricted_items.Sort("[ReceivedTime]", True)
    except Exception as e:
        print(f"Error applying restriction in Outlook Classic: {e}")
        restricted_items = folder.Items
        restricted_items.Sort("[ReceivedTime]", True)
    
    recent_emails = []
    
    for item in restricted_items:
        try:
            # We intentionally skip the class checking (item.Class != 43) because 
            # some internal system alerts arrive as ReportItems or custom classes.
            subject = getattr(item, "Subject", "")
            if not subject:
                continue
                
            if regex and not regex.search(subject):
                continue
                
            try:
                html_body = item.HTMLBody
            except Exception:
                html_body = ""
                
            try:
                body = item.Body or ""
            except Exception:
                body = ""
                
            try:
                rt = item.ReceivedTime
                rt_iso = rt.isoformat() if hasattr(rt, 'isoformat') else str(rt)
            except Exception:
                rt_iso = datetime.datetime.now().isoformat()
                
            # If the fallback loop triggers, double check unread flag
            if not getattr(item, "UnRead", False):
                continue
            
            recent_emails.append({
                "entry_id": getattr(item, "EntryID", "unknown"),
                "subject": subject,
                "body": body,
                "html_body": html_body,
                "received_time": rt_iso
            })
        except Exception as e:
            continue

    recent_emails.reverse()
    return recent_emails
