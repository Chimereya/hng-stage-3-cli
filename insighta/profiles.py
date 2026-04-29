import click
import csv
import os
from datetime import datetime
from .auth import make_request, is_logged_in
from .display import (
    console,
    print_success,
    print_error,
    print_info,
    print_profiles_table,
    print_profile,
    print_pagination,
    Loader,
)


@click.group()
def profiles():
    """Manage Insighta profiles."""
    pass


@profiles.command()
@click.option("--gender", help="Filter by gender (male/female)")
@click.option("--country", help="Filter by country code (e.g., NG, US)")
@click.option("--age-group", help="Filter by age group (child, teen, young_adult, adult, senior)")
@click.option("--min-age", type=int, help="Minimum age")
@click.option("--max-age", type=int, help="Maximum age")
@click.option("--sort-by", default="created_at", help="Field to sort by")
@click.option("--order", default="desc", type=click.Choice(["asc", "desc"]), help="Sort order")
@click.option("--page", default=1, type=int, help="Page number")
@click.option("--limit", default=10, type=int, help="Results per page")
def list(gender, country, age_group, min_age, max_age, sort_by, order, page, limit):
    """List profiles with optional filters."""
    if not is_logged_in():
        print_error("You are not logged in. Run: insighta login")
        return

    params = {
        "page": page,
        "limit": limit,
        "sort_by": sort_by,
        "order": order,
    }
    if gender:
        params["gender"] = gender
    if country:
        params["country"] = country
    if age_group:
        params["age_group"] = age_group
    if min_age is not None:
        params["min_age"] = min_age
    if max_age is not None:
        params["max_age"] = max_age

    with Loader("Fetching profiles..."):
        resp = make_request("GET", "/api/profiles", params=params)

    if resp.status_code == 200:
        data = resp.json()
        print_profiles_table(data["data"])
        print_pagination(
            data["page"], data["limit"], data["total"], data["total_pages"]
        )
    else:
        print_error(resp.json().get("message", "Failed to fetch profiles."))


@profiles.command()
@click.argument("profile_id")
def get(profile_id):
    """Get a single profile by ID."""
    if not is_logged_in():
        print_error("You are not logged in. Run: insighta login")
        return

    with Loader("Fetching profile..."):
        resp = make_request("GET", f"/api/profiles/{profile_id}")

    if resp.status_code == 200:
        data = resp.json()
        print_profile(data["data"])
    elif resp.status_code == 404:
        print_error("Profile not found.")
    else:
        print_error(resp.json().get("message", "Failed to fetch profile."))


@profiles.command()
@click.argument("query")
def search(query):
    """Natural language search for profiles."""
    if not is_logged_in():
        print_error("You are not logged in. Run: insighta login")
        return

    with Loader("Searching profiles..."):
        resp = make_request("GET", "/api/profiles/search", params={"q": query})

    if resp.status_code == 200:
        data = resp.json()
        print_profiles_table(data["data"])
        if "page" in data:
            print_pagination(
                data.get("page", 1),
                data.get("limit", 10),
                data.get("total", 0),
                data.get("total_pages", 0),
            )
    else:
        print_error(resp.json().get("message", "Search failed."))


@profiles.command()
@click.option("--name", required=True, help="Name of the profile to create")
def create(name):
    """Create a new profile (admin only)."""
    if not is_logged_in():
        print_error("You are not logged in. Run: insighta login")
        return

    with Loader("Creating profile..."):
        resp = make_request("POST", "/api/profiles", json={"name": name})

    if resp.status_code == 201:
        data = resp.json()
        print_success("Profile created successfully.")
        print_profile(data["data"])
    elif resp.status_code == 403:
        print_error("You do not have permission to create profiles (admin only).")
    else:
        print_error(resp.json().get("message", "Failed to create profile."))


@profiles.command()
@click.option("--format", "fmt", type=click.Choice(["csv"]), default="csv", help="Export format")
@click.option("--gender", help="Filter by gender")
@click.option("--country", help="Filter by country code")
@click.option("--age-group", help="Filter by age group")
def export(fmt, gender, country, age_group):
    """Export profiles to a file (CSV)."""
    if not is_logged_in():
        print_error("You are not logged in. Run: insighta login")
        return

    params = {"format": fmt}
    if gender:
        params["gender"] = gender
    if country:
        params["country"] = country
    if age_group:
        params["age_group"] = age_group

    with Loader("Exporting profiles..."):
        resp = make_request("GET", "/api/profiles/export", params=params)

    if resp.status_code != 200:
        print_error(resp.json().get("message", "Export failed."))
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"profiles_{timestamp}.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        f.write(resp.text)

    print_success(f"Exported to {filename}")