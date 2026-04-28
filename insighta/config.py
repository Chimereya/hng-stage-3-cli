import os
import json
from pathlib import Path




CREDENTIALS_DIR  = Path.home() / ".insighta"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"


API_URL = "https://hng-stage-3-backend.vercel.app"





def save_credentials(access_token: str, refresh_token: str, user: dict) -> None:
    """
    Saves tokens and user info to /.insighta/credentials.json.
    Creates the directory if it doesn't exist.
    """
    # Create /.insighta/ folder if it doesn't exist
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

    credentials = {
        "access_token" : access_token,
        "refresh_token": refresh_token,
        "user"         : user
    }

    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(credentials, f, indent=2)




def load_credentials() -> dict | None:
    """
    Loads credentials from /.insighta/credentials.json file.
    Returns None if the file doesn't exist (not logged in).
    """
    if not CREDENTIALS_FILE.exists():
        return None

    with open(CREDENTIALS_FILE, "r") as f:
        return json.load(f)




def clear_credentials() -> None:
    """
    Deletes the credentials file.
    Called on logout.
    """
    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()




def get_access_token() -> str | None:
    """
    Returns just the access token if credentials exist.
    Returns None if not logged in.
    """
    creds = load_credentials()
    if not creds:
        return None
    return creds.get("access_token")




def get_refresh_token() -> str | None:
    """
    Returns just the refresh token if credentials exist.
    Returns None if not logged in.
    """
    creds = load_credentials()
    if not creds:
        return None
    return creds.get("refresh_token")




def update_tokens(access_token: str, refresh_token: str) -> None:
    """
    This updates just the tokens without touching user info.
    Called after a successful token refresh.
    """
    creds = load_credentials()
    if creds:
        creds["access_token"]  = access_token
        creds["refresh_token"] = refresh_token
        CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump(creds, f, indent=2)



# Returns True if credentials file exists, False otherwise.
def is_logged_in() -> bool:
   
    return CREDENTIALS_FILE.exists()