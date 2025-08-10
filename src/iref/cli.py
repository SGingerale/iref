# src/iref/cli.py
from __future__ import annotations
import typer
from typing import Optional
from pathlib import Path

app = typer.Typer(help="Illustration reference tool.")

# ---- queue ---------------------------------------------------------------
@app.command()
def queue(
    root: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True, resolve_path=True, help="Root directory of a profile"),
    preset: Optional[str] = typer.Option(None, "--preset", "-p", help="(stub) Preset name"),
):
    """
    (stub) Queue and classify images under ROOT.
    """
    typer.echo(f"[stub] queue: root={root} preset={preset}")


# ---- config --------------------------------------------------------------
config_app = typer.Typer(help="Manage profiles and settings.")
app.add_typer(config_app, name="config")

@config_app.command("list")
def config_list():
    """(stub) List profiles."""
    typer.echo("[stub] config list -> default")

@config_app.command("set-root")
def config_set_root(
    name: str = typer.Argument(..., help="Profile name"),
    root: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True, resolve_path=True, help="Root directory"),
):
    """(stub) Set ROOT for PROFILE."""
    typer.echo(f"[stub] config set-root: {name} -> {root}")

@config_app.command("activate")
def config_activate(name: str = typer.Argument(..., help="Profile name")):
    """(stub) Activate PROFILE."""
    typer.echo(f"[stub] config activate: {name}")

def main():
    app()

if __name__ == "__main__":
    main()