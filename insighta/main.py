import click
from .auth import login, logout, whoami
from .profiles import profiles


@click.group()
@click.version_option(version="1.0.0", prog_name="insighta")
def cli():
    """
    Insighta Labs+ CLI

    A command line tool for interacting with the
    Insighta Profile Intelligence System.

    Examples:

    \b
    insighta login
    insighta whoami
    insighta profiles list
    insighta profiles list --gender male --country NG
    insighta profiles search "young males from nigeria"
    insighta profiles create --name "Harriet Tubman"
    insighta profiles export --format csv
    insighta profiles upload ./my_profiles.csv
    """
    pass


# WERE GONNA REGISTER ALL COMMANDS HERE
# Auth commands
cli.add_command(login)
cli.add_command(logout)
cli.add_command(whoami)

# Profile commands
cli.add_command(profiles)