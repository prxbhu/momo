import os
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/calendar.events']
CREDENTIALS_FILE = os.getenv("GOOGLE_CALENDAR_CREDENTIALS", "/app/secrets/google_calendar.json")
TOKEN_FILE = "/app/secrets/token.json"

def get_calendar_service():
    """Authenticate and return Google Calendar service."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"Missing Google Calendar credentials at {CREDENTIALS_FILE}")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            # In a real headless setup, we'd use flow.run_console() or provide a manual auth way
            # Assuming token is already generated and placed for this container setup
            raise ValueError("Google Calendar token expired or missing. Needs manual auth.")
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    return build('calendar', 'v3', credentials=creds)

def get_calendar_events(days_ahead: int = 7) -> str:
    """Get upcoming calendar events.
    Args:
        days_ahead: How many days into the future to look (default 7)
    Returns:
        List of upcoming events with times and descriptions
    """
    try:
        service = get_calendar_service()
        
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        end_time = (datetime.datetime.utcnow() + datetime.timedelta(days=days_ahead)).isoformat() + 'Z'
        
        events_result = service.events().list(calendarId='primary', timeMin=now, timeMax=end_time,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            return f"No upcoming events found for the next {days_ahead} days."

        result = [f"Upcoming events for the next {days_ahead} days:"]
        for event in events:
             start = event['start'].get('dateTime', event['start'].get('date'))
             # Basic formatting
             try:
                 # Try parsing ISO format
                 dt = datetime.datetime.fromisoformat(start)
                 start_str = dt.strftime("%Y-%m-%d %H:%M")
             except ValueError:
                 start_str = start
                 
             result.append(f"- {start_str}: {event['summary']}")
        
        return "\n".join(result)
        
    except Exception as e:
        return f"Error fetching calendar events: {e}"

def create_calendar_event(title: str, date: str, time: str, duration_minutes: int = 60) -> str:
    """Create a new calendar event.
    Args:
        title: Event name
        date: Date in YYYY-MM-DD format
        time: Start time in HH:MM format (24h)
        duration_minutes: Event duration in minutes
    Returns:
        Confirmation message with event details
    """
    try:
        service = get_calendar_service()
        
        start_datetime = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        end_datetime = start_datetime + datetime.timedelta(minutes=duration_minutes)
        
        event = {
          'summary': title,
          'start': {
            'dateTime': start_datetime.isoformat(),
            'timeZone': 'UTC', # Should realistically use local timezone
          },
          'end': {
            'dateTime': end_datetime.isoformat(),
            'timeZone': 'UTC',
          },
        }

        created_event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Event created: '{title}' on {date} at {time}. Link: {created_event.get('htmlLink')}"
        
    except Exception as e:
         return f"Error creating calendar event: {e}"
