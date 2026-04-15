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
        # Default to Inbox (6 = olFolderInbox)
        folder = namespace.GetDefaultFolder(6)
        
        parts = folder_path.replace("\\", "/").split("/")
        if parts[0].lower() == "inbox":
            parts = parts[1:]
        elif parts[0].lower() == "deleted items":
            folder = namespace.GetDefaultFolder(3)
            parts = parts[1:]
            
        for part in parts:
            if part:
                folder = folder.Folders.Item(part)
        return folder
    except Exception as e:
        print(f"Error accessing folder {folder_path}: {e}")
        return None

def fetch_recent_unread_emails() -> list:
    """
    Connects to Outlook and returns unread emails matching the subject regex
    and received within the last 5 minutes.
    """
    try:
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

    # Calculate 5 minutes ago in UTC and local (some systems behave differently with pywin32 dates)
    now = datetime.datetime.now(datetime.timezone.utc)
    five_mins_ago = now - datetime.timedelta(minutes=5)
    
    recent_emails = []
    
    for item in items:
        # Filter only MailItems (Class = 43)
        if item.Class != 43:
            continue
            
        try:
            received_time = item.ReceivedTime
            # Make timezone aware if it's not
            if received_time.tzinfo is None:
                received_time = received_time.replace(tzinfo=datetime.timezone.utc)
                
            if received_time < five_mins_ago:
                # Since we sorted descending, the moment we hit an older email, we can break
                break

            if item.UnRead:
                subject = item.Subject or ""
                # Check regex
                if not regex or regex.search(subject):
                    recent_emails.append({
                        "entry_id": item.EntryID,
                        "subject": subject,
                        "body": item.Body or "",
                        "received_time": received_time.isoformat()
                    })
        except Exception as e:
            print(f"Error processing item: {e}")
            continue

    # Reverse to process oldest to newest within the 5 minute window
    recent_emails.reverse()
    return recent_emails
