import json
import logging
import os
import time

from django.core.management.base import BaseCommand, CommandError
from rest_framework.test import APIRequestFactory
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from apps.contrib.models import Client
from apps.gidd.cache import GiddExportCache, external_storage
from apps.gidd.models import StatusLog
from apps.gidd.views import (
    DisaggregationViewSet,
    DisasterViewSet,
    DisplacementDataViewSet,
)
from helix.caches import external_api_cache

logger = logging.getLogger(__name__)

factory = APIRequestFactory()

ALL_KEYS = [
    GiddExportCache.Key.DISASTER_EXPORT,
    GiddExportCache.Key.DISPLACEMENT_EXPORT,
    GiddExportCache.Key.DISAGGREGATION_EXPORT,
    GiddExportCache.Key.DISAGGREGATION_EXPORT_GEOJSON,
]

VIEW_MAP = {
    GiddExportCache.Key.DISASTER_EXPORT: (
        DisasterViewSet.as_view({"get": "export"}),
        "/api/gidd/disasters/disaster-export/",
    ),
    GiddExportCache.Key.DISPLACEMENT_EXPORT: (
        DisplacementDataViewSet.as_view({"get": "export"}),
        "/api/gidd/displacements/displacement-export/",
    ),
    GiddExportCache.Key.DISAGGREGATION_EXPORT: (
        DisaggregationViewSet.as_view({"get": "export_disaggregated"}),
        "/api/gidd/disaggregations/disaggregated-export/",
    ),
    GiddExportCache.Key.DISAGGREGATION_EXPORT_GEOJSON: (
        DisaggregationViewSet.as_view({"get": "export_disaggregated_geojson"}),
        "/api/gidd/disaggregations/disaggregated-geojson/",
    ),
}

STATUS_LOG_DATE_FORMAT = "%Y-%m-%d-%H-%M-%S"


class Command(BaseCommand):
    help = "GIDD cache helper: warmup, clear, and inspect status logs."

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="subcommand", required=True)

        warmup = subparsers.add_parser("warmup", help="Warm GIDD export cache.")
        warmup.add_argument(
            "--client-id",
            type=str,
            required=True,
            help="Active client_id required to authorize the cache warmup. Use the 'clients' subcommand to list options.",
        )
        warmup.add_argument(
            "--key",
            type=str,
            choices=[k.value for k in ALL_KEYS],
            help="Specific export key to warm. If omitted, all exports are warmed.",
        )
        warmup.add_argument(
            "--filters",
            type=str,
            default="{}",
            help='JSON string of query params, e.g. \'{"iso3__in": "AFG", "start_year": "2023"}\'',
        )

        clear = subparsers.add_parser("clear", help="Clear cached GIDD exports from external storage.")
        clear.add_argument(
            "--key",
            type=str,
            choices=[k.value for k in ALL_KEYS],
            help="Scope deletion to a specific export key.",
        )
        clear.add_argument(
            "--status-log-id",
            type=int,
            help="Scope deletion to the cache path for a specific StatusLog id.",
        )
        clear.add_argument("--dry-run", action="store_true", help="List paths without deleting.")
        clear.add_argument("--yes", action="store_true", help="Skip confirmation prompt.")

        status_logs = subparsers.add_parser("status-logs", help="List recent StatusLog entries.")
        status_logs.add_argument("--limit", type=int, default=5, help="Number of recent entries to show (default 5).")

        subparsers.add_parser("clients", help="List active GIDD client_ids registered in cache.")

    def handle(self, *args, **options):
        self.console = Console(file=self.stdout, force_terminal=options.get("force_color"), no_color=options.get("no_color"))
        self.err_console = Console(
            file=self.stderr, force_terminal=options.get("force_color"), no_color=options.get("no_color")
        )
        sub = options["subcommand"]
        if sub == "warmup":
            return self._handle_warmup(options)
        if sub == "clear":
            return self._handle_clear(options)
        if sub == "status-logs":
            return self._handle_status_logs(options)
        if sub == "clients":
            return self._handle_clients(options)

    def _handle_warmup(self, options):
        try:
            query_params = json.loads(options["filters"])
        except json.JSONDecodeError as e:
            self.err_console.print(f"[bold red]Invalid JSON for --filters:[/bold red] {e}")
            return

        client_id = options["client_id"]
        active_ids = external_api_cache.get("client_ids", []) or []
        if client_id not in active_ids:
            raise CommandError(
                f"client_id '{client_id}' is not active. Use `gidd_helper clients` to list active client_ids."
            )
        query_params["client_id"] = client_id

        key_value = options["key"]
        keys = [GiddExportCache.Key(key_value)] if key_value else ALL_KEYS

        table = Table(title="GIDD Cache Warmup", show_lines=False)
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Status", style="bold")
        table.add_column("Time", justify="right")
        table.add_column("Detail")

        for key in keys:
            view, url = VIEW_MAP[key]
            self.console.print(f"[dim]Warming[/dim] [cyan]{key.value}[/cyan]...")
            start = time.time()
            try:
                request = factory.get(url, query_params)
                response = view(request)
                elapsed = time.time() - start
                table.add_row(key.value, "[green]OK[/green]", f"{elapsed:.1f}s", f"-> {response.status_code}")
            except Exception as e:
                elapsed = time.time() - start
                table.add_row(key.value, "[red]FAIL[/red]", f"{elapsed:.1f}s", str(e))
                logger.exception(f"Failed to warm cache for {key.value}")

        self.console.print(table)

    def _handle_clear(self, options):
        key_value = options["key"]
        status_log_id = options["status_log_id"]

        date_segment = None
        if status_log_id is not None:
            try:
                log = StatusLog.objects.get(id=status_log_id)
            except StatusLog.DoesNotExist:
                raise CommandError(f"StatusLog id={status_log_id} does not exist.")
            if not log.completed_at:
                raise CommandError(f"StatusLog id={status_log_id} has no completed_at.")
            date_segment = log.completed_at.strftime(STATUS_LOG_DATE_FORMAT)

        paths = list(self._collect_paths(date_segment, key_value))
        if not paths:
            self.console.print("[yellow]No cached files found for the given scope.[/yellow]")
            return

        self.console.print(f"[bold]Found {len(paths)} cached path(s):[/bold]")
        for p in paths:
            self.console.print(f"  [dim]{p}[/dim]")

        if options["dry_run"]:
            self.console.print("[yellow]Dry run — nothing deleted.[/yellow]")
            return

        if not options["yes"]:
            if not Confirm.ask(f"Delete {len(paths)} path(s)?", default=False, console=self.console):
                self.console.print("[yellow]Aborted.[/yellow]")
                return

        deleted = 0
        for p in paths:
            try:
                external_storage.delete(p)
                deleted += 1
            except Exception as e:
                self.err_console.print(f"[red]Failed to delete {p}:[/red] {e}")
        self.console.print(f"[green]Deleted {deleted}/{len(paths)} path(s).[/green]")

    def _collect_paths(self, date_segment, key_value):
        base = GiddExportCache.FILE_DESTINATION_PREFIX
        if date_segment and key_value:
            yield from self._walk(os.path.join(base, date_segment, key_value))
            return
        if date_segment:
            yield from self._walk(os.path.join(base, date_segment))
            return
        if key_value:
            dirs, _ = external_storage.listdir(base)
            for d in dirs:
                yield from self._walk(os.path.join(base, d, key_value))
            return
        yield from self._walk(base)

    def _walk(self, prefix):
        try:
            dirs, files = external_storage.listdir(prefix)
        except Exception:
            return
        for f in files:
            yield os.path.join(prefix, f)
        for d in dirs:
            yield from self._walk(os.path.join(prefix, d))

    def _handle_status_logs(self, options):
        limit = options["limit"]
        logs = list(StatusLog.objects.order_by("-completed_at", "-triggered_at")[:limit])
        if not logs:
            self.console.print("[yellow]No StatusLog entries found.[/yellow]")
            return

        latest_success_id = (
            StatusLog.objects.filter(status=StatusLog.Status.SUCCESS, completed_at__isnull=False)
            .order_by("-completed_at")
            .values_list("id", flat=True)
            .first()
        )

        table = Table(title=f"Recent StatusLog (last {len(logs)})", show_lines=False)
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Status")
        table.add_column("Triggered At", style="dim")
        table.add_column("Completed At", style="dim")
        table.add_column("Triggered By")
        table.add_column("Current", style="bold green")

        status_color = {
            StatusLog.Status.SUCCESS.value: "green",
            StatusLog.Status.PENDING.value: "yellow",
            StatusLog.Status.FAILED.value: "red",
        }
        for log in logs:
            status_name = StatusLog.Status(log.status).name if log.status is not None else "NA"
            color = status_color.get(log.status, "white")
            triggered_at = log.triggered_at.isoformat() if log.triggered_at else "NA"
            completed_at = log.completed_at.isoformat() if log.completed_at else "NA"
            triggered_by = getattr(log.triggered_by, "username", "") or ""
            marker = "<- current" if log.id == latest_success_id else ""
            table.add_row(
                str(log.id),
                f"[{color}]{status_name}[/{color}]",
                triggered_at,
                completed_at,
                triggered_by,
                marker,
            )
        self.console.print(table)

    def _handle_clients(self, options):
        active_ids = external_api_cache.get("client_ids", []) or []
        if not active_ids:
            self.console.print("[yellow]No active client_ids found in cache.[/yellow]")
            return

        clients_by_code = {c.code: c for c in Client.objects.filter(code__in=active_ids)}

        table = Table(title=f"Active GIDD Clients ({len(active_ids)})", show_lines=False)
        table.add_column("Code", style="cyan", no_wrap=True)
        table.add_column("Name")
        table.add_column("Active in DB", justify="center")

        for code in active_ids:
            client = clients_by_code.get(code)
            name = client.name if client else "[red](not in DB)[/red]"
            if client and client.is_active:
                active_db = "[green]yes[/green]"
            else:
                active_db = "[red]no[/red]"
            table.add_row(code, name, active_db)
        self.console.print(table)
