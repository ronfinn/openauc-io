"""Command-line interface for openauc (Phase 1 scaffold).

Only version reporting is wired up so the console-script entry point and CI can
be exercised. Domain commands (import, validate, summarise, plot, archive) are
introduced in later phases; see ``docs/decisions/ADR-0004`` and
``development-log/0001-project-foundation.md``.
"""

from __future__ import annotations

import typer

from openauc import __version__

app = typer.Typer(
    name="openauc",
    help="Import, validate, standardise, visualise and archive AUC data.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def _root() -> None:
    """Import, validate, standardise, visualise and archive AUC data.

    A root callback is registered so the single Phase 1 command keeps proper
    subcommand semantics (``openauc version`` rather than a bare invocation).
    """


@app.command()
def version() -> None:
    """Print the installed openauc version."""
    typer.echo(__version__)


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
