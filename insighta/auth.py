import click
import requests
import threading
import webbrowser
import hashlib
import base64
import secrets
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode

from .config import (
    API_URL,
    save_credentials,
    clear_credentials,
    load_credentials,
    get_access_token,
    get_refresh_token,
    update_tokens,
    is_logged_in,
)
from .display import (
    console,
    print_success,
    print_error,
    print_info,
    print_user,
    Loader,
)


# ──────────────────────────────────────────
# PKCE HELPERS
# ──────────────────────────────────────────

def generate_pkce_pair():
    """Generate a code_verifier and code_challenge pair (PKCE S256)."""
    import string
    allowed_chars = string.ascii_letters + string.digits + '._~-'
    code_verifier = ''.join(secrets.choice(allowed_chars) for _ in range(43))
    code_challenge = (
        base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        )
        .rstrip(b"=")
        .decode()
    )
    return code_verifier, code_challenge


# ──────────────────────────────────────────
# TOKEN EXCHANGE
# ──────────────────────────────────────────

def exchange_code_for_tokens(code: str, code_verifier: str) -> dict | None:
    """Exchange authorization code for access tokens using PKCE."""
    try:
        response = requests.post(
            f"{API_URL}/auth/token",
            json={
                "code": code,
                "code_verifier": code_verifier,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.RequestException:
        return None
    """Try to refresh the access token using the stored refresh token."""
    refresh_token = get_refresh_token()
    if not refresh_token:
        return False

    try:
        response = requests.post(
            f"{API_URL}/auth/refresh",
            json={"refresh_token": refresh_token},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            update_tokens(data["access_token"], data["refresh_token"])
            return True
        return False
    except requests.exceptions.RequestException:
        return False


# ──────────────────────────────────────────
# AUTHENTICATED REQUEST
# ──────────────────────────────────────────

def make_request(method: str, endpoint: str, **kwargs) -> requests.Response:
    """
    Make an authenticated request to the backend.
    Automatically refreshes the token on 401 and retries once.
    Exits with a helpful message if refresh also fails.
    """
    access_token = get_access_token()

    if not access_token:
        print_error("You are not logged in. Run: insighta login")
        raise SystemExit(1)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-API-Version": "1",
        **kwargs.pop("headers", {}),
    }

    response = requests.request(
        method,
        f"{API_URL}{endpoint}",
        headers=headers,
        **kwargs,
    )

    # Token expired — try to refresh and retry once
    if response.status_code == 401:
        print_info("Session expired, refreshing token...")
        if refresh_access_token():
            headers["Authorization"] = f"Bearer {get_access_token()}"
            response = requests.request(
                method,
                f"{API_URL}{endpoint}",
                headers=headers,
                **kwargs,
            )
        else:
            print_error("Session expired. Please run: insighta login")
            raise SystemExit(1)

    return response


# ──────────────────────────────────────────
# LOCAL CALLBACK SERVER (thread‑safe)
# ──────────────────────────────────────────

class CallbackResult:
    """Thread‑safe container for OAuth callback data."""
    def __init__(self):
        self.lock = threading.Lock()
        self.access_token = None
        self.refresh_token = None
        self.state = None
        self.user = {}
        self.received = False


class CallbackHandler(BaseHTTPRequestHandler):
    """
    Temporary local HTTP server that catches the GitHub OAuth callback
    and extracts the tokens forwarded by the backend in the redirect URL.
    """
    # These class attributes will be set before server start
    result: CallbackResult = None
    expected_state: str = None

    def do_GET(self):
        parsed = urlparse(self.path)

        # Only process /callback; ignore other requests
        if parsed.path != "/callback":
            self.send_response(204)
            self.end_headers()
            return

        params = parse_qs(parsed.query)

        with CallbackHandler.result.lock:
            CallbackHandler.result.state = params.get("state", [None])[0]
            CallbackHandler.result.access_token = params.get("access_token", [None])[0]
            CallbackHandler.result.refresh_token = params.get("refresh_token", [None])[0]
            CallbackHandler.result.user = {
                "username": params.get("username", [None])[0],
                "email": params.get("email", [None])[0],
                "role": params.get("role", [None])[0],
                "avatar_url": params.get("avatar_url", [None])[0],
            }
            CallbackHandler.result.received = True

        # Send a nice response to the browser
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"""<html><body style="font-family:sans-serif;text-align:center;padding:60px;">
                   <h2>&#10003; Authentication Successful!</h2>
                   <p>You can close this tab and return to your terminal.</p>
               </body></html>"""
        )

    def log_message(self, format, *args):
        pass  # Suppress server logs


# ──────────────────────────────────────────
# LOGIN COMMAND
# ──────────────────────────────────────────

@click.command()
def login():
    """Login to Insighta via GitHub OAuth."""
    if is_logged_in():
        creds = load_credentials()
        username = creds.get("user", {}).get("username", "unknown")
        print_info(f"Already logged in as @{username}")
        print_info("Run 'insighta logout' first to switch accounts.")
        return

    # Generate PKCE + state
    code_verifier, code_challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(32)

    # Prepare thread‑safe result container
    result = CallbackResult()
    CallbackHandler.result = result

    PORT = 8484
    server = HTTPServer(("localhost", PORT), CallbackHandler)
    server.socket.settimeout(1.0)  # Low timeout so we can check for shutdown frequently
    server.timeout = 1.0

    # Build the auth URL (backend must support source=cli and PKCE)
    query_params = {
        "source": "cli",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{API_URL}/auth/github?{urlencode(query_params)}"

    # Try to open in browser; if fails, print the URL clearly
    opened = webbrowser.open(auth_url)
    if not opened:
        print_info("Could not open browser automatically.")
        console.print(
            "\n[bold yellow]Please open the following URL in your browser:[/bold yellow]\n"
            f"[bold cyan]{auth_url}[/bold cyan]\n"
        )
    else:
        console.print(
            "\n[bold cyan]A browser window should have opened.[/bold cyan]\n"
            "If not, open this URL manually:\n"
            f"[dim]{auth_url}[/dim]\n"
        )

    console.print("[yellow]Waiting for authentication (press Enter to cancel)...[/yellow]")
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        # Wait for a callback or user cancellation
        while not result.received:
            if not server_thread.is_alive():
                break
            # Check if user pressed Enter (non-blocking)
            import sys, select
            if sys.stdin in select.select([sys.stdin], [], [], 0.5)[0]:
                sys.stdin.readline()  # discard the Enter
                print_info("Cancelled by user.")
                return
    except KeyboardInterrupt:
        print_info("\nCancelled by user.")
        return
    finally:
        server.shutdown()
        server_thread.join(timeout=5)

    if not result.received or not result.access_token:
        print_error("Login did not complete. Please try again.")
        return

    # Validate state (CSRF protection)
    if result.state != state:
        print_error("State mismatch – possible CSRF attack. Aborting login.")
        return

    # Persist credentials
    save_credentials(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        user=result.user,
    )

    username = result.user.get("username", "unknown")
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

    if refresh_token:
        with Loader("Logging out..."):
            try:
                requests.post(
                    f"{API_URL}/auth/logout",
                    json={"refresh_token": refresh_token},
                    timeout=10,
                )
            except requests.exceptions.RequestException:
                pass  # Clear locally even if backend call fails

    clear_credentials()
    print_success("Logged out successfully.")


# ──────────────────────────────────────────
# WHOAMI COMMAND
# ──────────────────────────────────────────

@click.command()
def whoami():
    """Show the currently logged-in user."""
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