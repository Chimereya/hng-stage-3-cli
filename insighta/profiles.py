import click
import os
from .auth import make_request
from .display import (
    console,
    print_profiles_table,
    print_profile,
    print_pagination,
    print_success,
    print_error,
    print_info,
    Loader
)


# ──────────────────────────────────────────
# PROFILES GROUP
# ──────────────────────────────────────────

@click.group()
def profiles():
    """Manage profiles."""
    pass


# ──────────────────────────────────────────
# LIST COMMAND
# ──────────────────────────────────────────

@profiles.command()
@click.option("--gender",    default=None, help="Filter by gender (male/female)")
@click.option("--country",   default=None, help="Filter by country code (e.g. NG)")
@click.option("--age-group", default=None, help="Filter by age group (child/teenager/adult/senior)")
@click.option("--min-age",   default=None, type=int, help="Minimum age")
@click.option("--max-age",   default=None, type=int, help="Maximum age")
@click.option("--sort-by",   default=None, help="Sort by field (age/created_at/gender_probability)")
@click.option("--order",     default="desc", help="Sort order (asc/desc)")
@click.option("--page",      default=1, type=int, help="Page number")
@click.option("--limit",     default=10, type=int, help="Results per page")
def list(gender, country, age_group, min_age, max_age, sort_by, order, page, limit):
    """List profiles with optional filters."""

    # Build query params — only include non-None values
    params = {"page": page, "limit": limit, "order": order}

    if gender:
        params["gender"]    = gender
    if country:
        params["country_id"] = country
    if age_group:
        params["age_group"] = age_group
    if min_age is not None:
        params["min_age"]   = min_age
    if max_age is not None:
        params["max_age"]   = max_age
    if sort_by:
        params["sort_by"]   = sort_by

    with Loader("Fetching profiles..."):
        response = make_request("GET", "/api/profiles", params=params)

    if response.status_code == 200:
        data     = response.json()
        profiles = data.get("data", [])

        print_profiles_table(profiles)
        print_pagination(
            page        = data.get("page", 1),
            limit       = data.get("limit", 10),
            total       = data.get("total", 0),
            total_pages = data.get("total_pages", 1),
        )
    else:
        error = response.json().get("message", "Failed to fetch profiles")
        print_error(error)


# ──────────────────────────────────────────
# GET COMMAND
# ──────────────────────────────────────────

@profiles.command()
@click.argument("id")
def get(id):
    """Get a single profile by ID."""

    with Loader(f"Fetching profile {id}..."):
        response = make_request("GET", f"/api/profiles/{id}")

    if response.status_code == 200:
        data = response.json()
        print_profile(data["data"])
    else:
        error = response.json().get("message", "Profile not found")
        print_error(error)


# ──────────────────────────────────────────
# SEARCH COMMAND
# ──────────────────────────────────────────

@profiles.command()
@click.argument("query")
@click.option("--page",  default=1,  type=int, help="Page number")
@click.option("--limit", default=10, type=int, help="Results per page")
def search(query, page, limit):
    """Search profiles using natural language."""

    params = {"q": query, "page": page, "limit": limit}

    with Loader(f"Searching for '{query}'..."):
        response = make_request("GET", "/api/profiles/search", params=params)

    if response.status_code == 200:
        data     = response.json()
        profiles = data.get("data", [])

        print_profiles_table(profiles)
        print_pagination(
            page        = data.get("page", 1),
            limit       = data.get("limit", 10),
            total       = data.get("total", 0),
            total_pages = data.get("total_pages", 1),
        )
    else:
        error = response.json().get("message", "Search failed")
        print_error(error)


# ──────────────────────────────────────────
# CREATE COMMAND
# ──────────────────────────────────────────

@profiles.command()
@click.option("--name", required=True, help="Name to create profile for")
def create(name):
    """Create a new profile by name. (Admin only)"""

    with Loader(f"Creating profile for '{name}'..."):
        response = make_request(
            "POST",
            "/api/profiles",
            json={"name": name}
        )

    if response.status_code in (200, 201):
        data = response.json()
        print_success(f"Profile created successfully!")
        print_profile(data["data"])
    elif response.status_code == 403:
        print_error("Admin access required to create profiles.")
    else:
        error = response.json().get("message", "Failed to create profile")
        print_error(error)


# ──────────────────────────────────────────
# DELETE COMMAND
# ──────────────────────────────────────────

@profiles.command()
@click.argument("id")
@click.confirmation_option(prompt="Are you sure you want to delete this profile?")
def delete(id):
    """Delete a profile by ID. (Admin only)"""

    with Loader(f"Deleting profile {id}..."):
        response = make_request("DELETE", f"/api/profiles/{id}")

    if response.status_code == 204:
        print_success("Profile deleted successfully.")
    elif response.status_code == 403:
        print_error("Admin access required to delete profiles.")
    elif response.status_code == 404:
        print_error("Profile not found.")
    else:
        print_error("Failed to delete profile.")


# ──────────────────────────────────────────
# EXPORT COMMAND
# ──────────────────────────────────────────

@profiles.command()
@click.option("--format",    default="csv",  help="Export format (csv)")
@click.option("--gender",    default=None,   help="Filter by gender")
@click.option("--country",   default=None,   help="Filter by country code")
@click.option("--age-group", default=None,   help="Filter by age group")
@click.option("--min-age",   default=None,   type=int, help="Minimum age")
@click.option("--max-age",   default=None,   type=int, help="Maximum age")
def export(format, gender, country, age_group, min_age, max_age):
    """Export profiles as CSV to current directory."""

    params = {"format": format}

    if gender:
        params["gender"]    = gender
    if country:
        params["country_id"] = country
    if age_group:
        params["age_group"] = age_group
    if min_age is not None:
        params["min_age"]   = min_age
    if max_age is not None:
        params["max_age"]   = max_age

    with Loader("Exporting profiles..."):
        response = make_request(
            "GET",
            "/api/profiles/export",
            params=params
        )

    if response.status_code == 200:
        # Get filename from response headers
        content_disposition = response.headers.get(
            "Content-Disposition", ""
        )

        # Extract filename from header
        filename = "profiles_export.csv"
        if "filename=" in content_disposition:
            filename = content_disposition.split("filename=")[-1].strip()

        # Save to current working directory
        filepath = os.path.join(os.getcwd(), filename)
        with open(filepath, "wb") as f:
            f.write(response.content)

        print_success(f"Exported to {filepath}")
    elif response.status_code == 403:
        print_error("Access denied.")
    else:
        error = response.json().get("message", "Export failed")
        print_error(error)