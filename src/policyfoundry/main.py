"""PolicyFoundry CLI application.

Typer-based CLI with three commands:
- ``analyze``: Run the full analysis pipeline with Rich or JSON output.
- ``rules``: Display current firewall rules from an adapter.
- ``config``: Show resolved configuration.

Commands are sync with internal ``asyncio.run()`` (D027). All
``PolicyFoundryError`` subtypes are caught at the command boundary
and rendered as Rich error panels (D030).
"""

from __future__ import annotations

import asyncio
import json as json_module
import logging
import sys
import traceback
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from policyfoundry.adapters.registry import AdapterRegistry
from policyfoundry.adapters.safety import ReadOnlyAdapter
from policyfoundry.config.loader import load_config
from policyfoundry.exceptions import PolicyFoundryError
from policyfoundry.output.json_output import format_json
from policyfoundry.output.rich_output import format_rich
from policyfoundry.pipeline.llm import create_llm_client
from policyfoundry.pipeline.runner import run_pipeline

app = typer.Typer(
    name="policyfoundry",
    help="AI-powered firewall policy analysis and recommendation engine.",
    no_args_is_help=True,
)

console = Console()

# Module-level debug flag toggled by the global callback
_debug = False
_verbose = False


def _render_error(exc: PolicyFoundryError) -> None:
    """Render a PolicyFoundryError as a Rich panel with structured details."""
    error_class = type(exc).__name__
    lines = [f"[bold red]{error_class}[/bold red]: {exc}"]
    if exc.error_code:
        lines.append(f"Error Code: {exc.error_code}")
    if exc.details:
        for key, value in exc.details.items():
            lines.append(f"  {key}: {value}")
    panel = Panel(
        "\n".join(lines),
        title="Error",
        border_style="red",
    )
    console.print(panel)


def _handle_error(exc: Exception) -> None:
    """Handle any exception at the command boundary.

    PolicyFoundryError → structured Rich panel.
    Other exceptions → generic error message.
    With --debug, show full traceback.
    """
    if _debug:
        console.print_exception()

    if isinstance(exc, PolicyFoundryError):
        _render_error(exc)
    else:
        console.print(
            Panel(
                f"[bold red]Unexpected error[/bold red]: {exc}",
                title="Error",
                border_style="red",
            )
        )


@app.callback()
def main_callback(
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Enable debug output and full tracebacks."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Enable verbose logging."),
    ] = False,
) -> None:
    """PolicyFoundry: AI-powered firewall policy analysis."""
    global _debug, _verbose  # noqa: PLW0603
    _debug = debug
    _verbose = verbose

    if debug or verbose:
        log_level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )


@app.command()
def analyze(
    source: Annotated[
        str,
        typer.Option("--source", help="Log source type (local or s3)."),
    ] = "local",
    format: Annotated[
        str,
        typer.Option("--format", help="Output format: rich or json."),
    ] = "rich",
    sg_ids: Annotated[
        Optional[list[str]],
        typer.Option("--sg-ids", help="Security group IDs to analyze."),
    ] = None,
    config_path: Annotated[
        Optional[Path],
        typer.Option("--config", help="Path to YAML config file."),
    ] = None,
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Enable debug output."),
    ] = False,
) -> None:
    """Run the full analysis pipeline on VPC flow logs.

    Loads configuration, creates an LLM client, fetches firewall rules
    via a ReadOnlyAdapter, and runs the analysis pipeline. Output is
    rendered as Rich tables (default) or JSON.
    """
    global _debug  # noqa: PLW0603
    if debug:
        _debug = True

    try:
        # Load config
        overrides = {}
        if config_path:
            overrides["_yaml_file"] = str(config_path)
        cfg = load_config(**overrides)

        # Resolve SG IDs from CLI args or config
        resolved_sg_ids = list(sg_ids) if sg_ids else cfg.targets.security_group_ids
        if not resolved_sg_ids:
            raise PolicyFoundryError(
                "No security group IDs specified. Use --sg-ids or set "
                "POLICYFOUNDRY_TARGETS__SECURITY_GROUP_IDS in your config.",
                error_code="MISSING_SG_IDS",
            )

        # Resolve data dir
        data_dir = str(Path(cfg.output.data_dir).expanduser())

        async def _run() -> dict:
            # Create LLM client
            llm_client = await create_llm_client(cfg.llm)

            # Create adapter wrapped in ReadOnlyAdapter
            adapter = AdapterRegistry.get_adapter(
                "aws_sg",
                security_group_id=resolved_sg_ids[0],
            )
            safe_adapter = ReadOnlyAdapter(adapter)

            # Run pipeline with Rich spinner
            with console.status("[bold blue]Running analysis pipeline...") as status:
                state = await run_pipeline(
                    llm_client=llm_client,
                    adapter=safe_adapter,
                    data_dir=data_dir,
                    sg_ids=resolved_sg_ids,
                )

            # Attach token usage to state
            usage = llm_client.get_usage()
            state["token_usage"] = usage.to_dict()

            return state

        state = asyncio.run(_run())

        # Format output
        if format == "json":
            output = format_json(state)
            typer.echo(output)
        else:
            format_rich(state, console=console)

    except PolicyFoundryError as exc:
        _handle_error(exc)
        raise typer.Exit(code=1)
    except Exception as exc:
        _handle_error(exc)
        raise typer.Exit(code=1)


@app.command()
def rules(
    adapter: Annotated[
        str,
        typer.Option("--adapter", help="Adapter name (e.g. aws_sg)."),
    ] = "aws_sg",
    sg_id: Annotated[
        Optional[str],
        typer.Option("--sg-id", help="Security group ID to query."),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", help="Output format: rich or json."),
    ] = "rich",
) -> None:
    """Display current firewall rules from an adapter.

    Fetches rules via the specified adapter and displays them as a
    Rich table or JSON output.
    """
    try:
        cfg = load_config()

        # Resolve SG ID from CLI arg or config
        resolved_sg_id = sg_id
        if not resolved_sg_id and cfg.targets.security_group_ids:
            resolved_sg_id = cfg.targets.security_group_ids[0]

        if not resolved_sg_id:
            raise PolicyFoundryError(
                "No security group ID specified. Use --sg-id or set "
                "POLICYFOUNDRY_TARGETS__SECURITY_GROUP_IDS in your config.",
                error_code="MISSING_SG_ID",
            )

        fw_adapter = AdapterRegistry.get_adapter(
            adapter,
            security_group_id=resolved_sg_id,
        )

        async def _fetch_rules():
            return await fw_adapter.get_rules()

        rules_list = asyncio.run(_fetch_rules())

        if format == "json":
            data = [r.model_dump() if hasattr(r, "model_dump") else str(r) for r in rules_list]
            typer.echo(json_module.dumps(data, indent=2, default=str))
        else:
            if not rules_list:
                console.print(
                    Panel(
                        "No rules found for the specified security group.",
                        title="Rules",
                        border_style="yellow",
                    )
                )
                return

            table = Table(
                title=f"Firewall Rules — {resolved_sg_id}",
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("Name")
            table.add_column("Direction")
            table.add_column("Action")
            table.add_column("Protocol")
            table.add_column("Source")
            table.add_column("Destination")
            table.add_column("Port Range")

            for rule in rules_list:
                src = ""
                dst = ""
                port_range = ""
                if hasattr(rule, "source") and rule.source:
                    src_parts = []
                    for ep in rule.source:
                        src_parts.append(ep.cidr or ep.security_group_id or "any")
                    src = ", ".join(src_parts)
                if hasattr(rule, "destination") and rule.destination:
                    dst_parts = []
                    for ep in rule.destination:
                        dst_parts.append(ep.cidr or ep.security_group_id or "any")
                    dst = ", ".join(dst_parts)
                if hasattr(rule, "port_range") and rule.port_range:
                    port_range = f"{rule.port_range.from_port}-{rule.port_range.to_port}"

                table.add_row(
                    str(getattr(rule, "name", "")),
                    str(getattr(rule, "direction", "")),
                    str(getattr(rule, "action", "")),
                    str(getattr(rule, "protocol", "")),
                    src,
                    dst,
                    port_range,
                )

            console.print(table)

    except PolicyFoundryError as exc:
        _handle_error(exc)
        raise typer.Exit(code=1)
    except Exception as exc:
        _handle_error(exc)
        raise typer.Exit(code=1)


@app.command()
def config(
    format: Annotated[
        str,
        typer.Option("--format", help="Output format: rich or json."),
    ] = "rich",
) -> None:
    """Show resolved PolicyFoundry configuration.

    Displays the fully resolved configuration from all sources
    (YAML files, environment variables, defaults).
    """
    try:
        cfg = load_config()
        cfg_dict = cfg.model_dump()

        # Redact sensitive values
        if "llm" in cfg_dict and "api_key" in cfg_dict["llm"]:
            key = cfg_dict["llm"]["api_key"]
            if key:
                cfg_dict["llm"]["api_key"] = f"{key[:4]}{'*' * (len(key) - 4)}" if len(key) > 4 else "****"

        if format == "json":
            typer.echo(json_module.dumps(cfg_dict, indent=2, default=str))
        else:
            lines = []
            for section, values in cfg_dict.items():
                lines.append(f"[bold cyan]{section}[/bold cyan]")
                if isinstance(values, dict):
                    for key, val in values.items():
                        lines.append(f"  {key}: {val}")
                else:
                    lines.append(f"  {values}")
                lines.append("")

            panel = Panel(
                "\n".join(lines),
                title="PolicyFoundry Configuration",
                border_style="blue",
            )
            console.print(panel)

    except PolicyFoundryError as exc:
        _handle_error(exc)
        raise typer.Exit(code=1)
    except Exception as exc:
        _handle_error(exc)
        raise typer.Exit(code=1)
