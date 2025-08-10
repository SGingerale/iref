from pathlib import Path
import typer
from .config import set_root, get_root, set_active
# from .queue import run_queue  # 本体入れたら有効化

app = typer.Typer(add_completion=False)
config_app = typer.Typer()
app.add_typer(config_app, name="config")


@config_app.command("set-root")
def config_set_root(
    path: Path = typer.Option(..., "--path", exists=True, file_okay=False, dir_okay=True),
    profile: str = typer.Option("default", "--profile", "-p"),
    activate: bool = typer.Option(True, "--activate/--no-activate"),
):
    """Set the root folder for a profile."""
    set_root(profile, path)
    if activate:
        set_active(profile)
    typer.echo(f"Set root for '{profile}' -> {path}")


@config_app.command("activate")
def config_activate(profile: str):
    """Activate a profile by name."""
    set_active(profile)
    typer.echo(f"Active profile set to '{profile}'")


@app.command()
def queue(
    root: Path = typer.Option(None, "--root", "-r", help="Override root path"),
    profile: str = typer.Option(None, "--profile", "-p", help="Profile name to use"),
):
    """Run the queue on a given root."""
    resolved = root or get_root(profile)
    typer.echo(f"Queue would run on: {resolved}")
    # run_queue(resolved)
