from rich.console import Console
from rich.table import Table
from rich.spinner import Spinner
from rich.live import Live
from rich import box
import time



# Single console instance used across the entire CLI
console = Console()


# ──────────────────────────────────────────
# LOADER
# ──────────────────────────────────────────

class Loader:
    """
    Shows a spinning loader while an operation is running.

    """
    def __init__(self, message: str = "Loading..."):
        self.message = message
        self.live    = Live(
            Spinner("dots", text=f"[cyan]{self.message}[/cyan]"),
            console    = console,
            transient  = True  # Clears the spinner when done
        )

    def __enter__(self):
        self.live.start()
        return self

    def __exit__(self, *args):
        self.live.stop()


# ──────────────────────────────────────────
# PROFILE TABLE
# ──────────────────────────────────────────

def print_profiles_table(profiles: list) -> None:
    """
    Prints a list of profiles as a rich table.
    """
    if not profiles:
        console.print("[yellow]No profiles found.[/yellow]")
        return

    table = Table(
        box = box.ROUNDED,
        show_header = True,
        header_style = "bold cyan",
        border_style = "bright_black",
        row_styles = ["", "dim"],  # Alternating row styles
    )

    # Define columns
    table.add_column("ID", style="dim", max_width=10)
    table.add_column("Name", style="bold white",  min_width=15)
    table.add_column("Gender", style="cyan", min_width=8)
    table.add_column("Age", style="magenta", min_width=5)
    table.add_column("Age Group", style="yellow", min_width=10)
    table.add_column("Country", style="green", min_width=8)
    table.add_column("Country Name",style="green",  min_width=15)
    table.add_column("Created At", style="dim", min_width=12)

    for p in profiles:
        # Truncate ID to first 8 chars for display
        short_id   = str(p.get("id", ""))[:8] + "..."
        created_at = str(p.get("created_at", ""))[:10]  # Just the date

        table.add_row(
            short_id,
            p.get("name", ""),
            p.get("gender", ""),
            str(p.get("age", "")),
            p.get("age_group", ""),
            p.get("country_id", ""),
            p.get("country_name", ""),
            created_at,
        )

    console.print(table)


# ──────────────────────────────────────────
# SINGLE PROFILE
# ──────────────────────────────────────────

def print_profile(profile: dict) -> None:
    """
    Prints a single profile in a detailed view.
    """
    table = Table(
        box          = box.ROUNDED,
        show_header  = False,
        border_style = "bright_black",
        min_width    = 40,
    )

    table.add_column("Field", style="bold cyan",  min_width=20)
    table.add_column("Value", style="bold white", min_width=25)

    table.add_row("ID", str(profile.get("id", "")))
    table.add_row("Name", profile.get("name", ""))
    table.add_row("Gender", profile.get("gender", ""))
    table.add_row("Gender Probability",  str(profile.get("gender_probability", "")))
    table.add_row("Age", str(profile.get("age", "")))
    table.add_row("Age Group",profile.get("age_group", ""))
    table.add_row("Country", profile.get("country_id", ""))
    table.add_row("Country Name", profile.get("country_name", ""))
    table.add_row("Country Probability", str(profile.get("country_probability", "")))
    table.add_row("Created At", str(profile.get("created_at", "")))

    console.print(table)


# ──────────────────────────────────────────
# PAGINATION INFO
# ──────────────────────────────────────────

def print_pagination(page: int, limit: int, total: int, total_pages: int) -> None:
    """
    Prints pagination info below the table.
    """
    console.print(
        f"\n[dim]Page [cyan]{page}[/cyan] of [cyan]{total_pages}[/cyan] "
        f"— [cyan]{total}[/cyan] total results "
        f"([cyan]{limit}[/cyan] per page)[/dim]"
    )


# ──────────────────────────────────────────
# SUCCESS / ERROR MESSAGES
# ──────────────────────────────────────────

def print_success(message: str) -> None:
    console.print(f"[bold green]✓[/bold green] {message}")


def print_error(message: str) -> None:
    console.print(f"[bold red]✗[/bold red] {message}")


def print_info(message: str) -> None:
    console.print(f"[bold cyan]→[/bold cyan] {message}")


# ──────────────────────────────────────────
# USER INFO
# ──────────────────────────────────────────

def print_user(user: dict) -> None:
    """
    Prints the logged in user's info.
    Used by insighta whoami.
    """
    table = Table(
        box = box.ROUNDED,
        show_header  = False,
        border_style = "bright_black",
        min_width = 35,
    )

    table.add_column("Field", style="bold cyan",  min_width=15)
    table.add_column("Value", style="bold white", min_width=20)

    table.add_row("Username", user.get("username", ""))
    table.add_row("Email",    user.get("email", "") or "not set")
    table.add_row("Role",     user.get("role", ""))

    console.print(table)