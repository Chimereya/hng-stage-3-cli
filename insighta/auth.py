import click
import requests
import threading
import webbrowser
import hashlib
import base64
import secrets
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from .config import (
    API_URL,
    save_credentials,
    clear_credentials,
    load_credentials,
    get_access_token,
    get_refresh_token,
    update_tokens,
    is_logged_in
)
from .display import (
    console,
    print_success,
    print_error,
    print_info,
    print_user,
    Loader
)



def generate_pkce_pair():
    """
    This Generates a code_verifier and code_challenge pair.
    The CLI will generate its own PKCE.
    """
    code_verifier  = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return code_verifier, code_challenge




def refresh_access_token() -> bool:
   
    refresh_token = get_refresh_token()
    if not refresh_token:
        return False

    try:
        response = requests.post(
            f"{API_URL}/auth/refresh",
            json={"refresh_token": refresh_token},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            access_token = data["access_token"]
            refresh_token = data["refresh_token"]
            update_tokens(access_token, refresh_token)
            return True

        return False

    except requests.exceptions.RequestException:
        return False



# AUTHENTICATED REQUEST

def make_request(method: str, endpoint: str, **kwargs) -> requests.Response:
    """
    Makes an authenticated request to the backend.
    Automatically refreshes the token if expired (that is 401).
    Prompts re-login if refresh also fails.

    """
    access_token = get_access_token()

    if not access_token:
        print_error("You are not logged in. Run: insighta login")
        raise SystemExit(1)

    headers = {
        "Authorization" : f"Bearer {access_token}",
        "X-API-Version" : "1",
        **kwargs.pop("headers", {})
    }

    response = requests.request(
        method,
        f"{API_URL}{endpoint}",
        headers=headers,
        **kwargs
    )

    # Token expired : trying to refresh
    if response.status_code == 401:
        print_info("Token expired, refreshing...")

        if refresh_access_token():
            # Retry with new token
            headers["Authorization"] = f"Bearer {get_access_token()}"
            response = requests.request(
                method,
                f"{API_URL}{endpoint}",
                headers=headers,
                **kwargs
            )
        else:
            # Refresh also failed so the user is logged out
            print_error("Session expired. Please run: insighta login")
            raise SystemExit(1)

    return response




# Local call back server
class CallbackHandler(BaseHTTPRequestHandler):
    """
    Temporary local HTTP server that catches the
    GitHub OAuth callback and extracts the code + state.
    """
    code  = None
    state = None

    def do_GET(self):
        # Parse the callback URL
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        # Extract code and state
        CallbackHandler.code  = params.get("code",  [None])[0]
        CallbackHandler.state = params.get("state", [None])[0]

        # Send a nice response to the browser
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"""
            <html>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h2>Authentication Successful!</h2>
                <p>You can close this tab and return to your terminal.</p>
            </body>
            </html>
        """)

    def log_message(self, format, *args):
        # Suppress server logs
        pass


# ──────────────────────────────────────────
# LOGIN COMMAND
# ──────────────────────────────────────────

@click.command()
def login():
    """Login to Insighta via GitHub OAuth."""

    if is_logged_in():
        creds = load_credentials()
        user  = creds.get("user", {})
        print_info(f"Already logged in as @{user.get('username', 'unknown')}")
        print_info("Run 'insighta logout' first to switch accounts.")
        return

    # Generate PKCE pair
    code_verifier, code_challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(32)

    # Start local callback server on port 8484
    PORT = 8484
    server = HTTPServer(("localhost", PORT), CallbackHandler)

    print_info("Starting local callback server...")
    print_info("Opening GitHub login page in your browser...")

    # Build the GitHub auth URL pointing to backend
    auth_url = (
        f"{API_URL}/auth/github"
        f"?source=cli"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )

    # Open browser
    webbrowser.open(auth_url)

    # Run server in a thread so it doesn't block
    server_thread = threading.Thread(target=server.handle_request)
    server_thread.start()

    # Wait for callback with timeout
    print_info("Waiting for GitHub callback...")
    server_thread.join(timeout=120)  # 2 minute timeout

    code  = CallbackHandler.code
    state_returned = CallbackHandler.state

    if not code:
        print_error("Login timed out. Please try again.")
        return

    # Validate state (CSRF protection)
    if state_returned != state:
        print_error("State mismatch. Possible CSRF attack. Aborting.")
        return

    # Exchange code + code_verifier with backend
    with Loader("Completing authentication..."):
        try:
            response = requests.post(
                f"{API_URL}/auth/cli/callback",
                json={
                    "code"         : code,
                    "code_verifier": code_verifier,
                    "state"        : state_returned
                },
                timeout=30
            )
        except requests.exceptions.RequestException as e:
            print_error(f"Connection error: {e}")
            return

    if response.status_code != 200:
        print_error("Authentication failed. Please try again.")
        return

    data = response.json()

    # Save credentials locally
    save_credentials(
        access_token  = data["access_token"],
        refresh_token = data["refresh_token"],
        user          = data["user"]
    )

    username = data["user"].get("username", "unknown")
    print_success(f"Logged in as @{username}")


# ──────────────────────────────────────────
# LOGOUT COMMAND
# ──────────────────────────────────────────

@click.command()
def logout():
    """Logout and clear stored credentials."""

    if not is_logged_in():
        print_error("You are not logged in.")
        return

    refresh_token = get_refresh_token()

    # Tell backend to revoke the refresh token
    if refresh_token:
        with Loader("Logging out..."):
            try:
                requests.post(
                    f"{API_URL}/auth/logout",
                    json={"refresh_token": refresh_token},
                    timeout=10
                )
            except requests.exceptions.RequestException:
                pass  # Even if backend call fails, were gonna clear local credentials

    # Clear local credentials
    clear_credentials()
    print_success("Logged out successfully.")


# ──────────────────────────────────────────
# WHOAMI COMMAND
# ──────────────────────────────────────────

@click.command()
def whoami():
    """Show the currently logged in user."""

    if not is_logged_in():
        print_error("You are not logged in. Run: insighta login")
        return

    with Loader("Fetching your profile..."):
        response = make_request("GET", "/auth/whoami")

    if response.status_code == 200:
        data = response.json()
        print_user(data["data"])
    else:
        print_error("Could not fetch user info.")