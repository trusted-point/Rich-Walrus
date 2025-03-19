import asyncio
from collections import deque
import asciichartpy as acp
from pyfiglet import figlet_format
from typing import Callable

from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from rich.align import Align
from rich import box

from src.aio_http_client import AioHttpCalls
from src.metrics_parser import StorageMetrics
from src.formater import covert_seconds_to_dhm
from utils.logger import logger


class StorageDashboard:
    def __init__(
        self,
        refresh_per_second: int,
        session: AioHttpCalls,
        refresh_metrics_rate: int,
        refresh_node_rpc_rate: int,
        graph_size: int,
    ):
        self.session = session
        self.rich_logger = None
        for handler in logger.handlers:
            if "RichPanelLogHandler" in str(handler):
                self.rich_logger = handler
                break

        self.layout = Layout()
        self.console = Console()

        self.layout.split_column(
            Layout(name="header", ratio=1),
            Layout(name="main", ratio=3),
            Layout(name="events", ratio=3),
        )

        self.layout["header"].split_row(
            Layout(name="Status", ratio=2),
            Layout(name="Shards", ratio=1),
            Layout(name="Checkpoint Lag", ratio=3),
            Layout(name="Blob_Recover_Backlog_In_Progress", ratio=3),
            Layout(name="Total Persisted Events", ratio=3),
            Layout(name="Total Downloaded Checkpoints", ratio=3),
        )

        self.layout["main"].split_row(
            Layout(name="Latest Downloaded Checkpoint", ratio=1),
            Layout(name="Blob_Recover_Backlog_Queued", ratio=1),
            Layout(name="Confirmations Issued", ratio=1),
        )

        self.layout["events"].split_row(
            Layout(name="Persisted Events", ratio=1),
            Layout(name="Pending Events", ratio=1),
            Layout(name="Highest Finished Event", ratio=1),
        )

        self.refresh_per_second = refresh_per_second
        self.refresh_metrics_rate = refresh_metrics_rate
        self.refresh_node_rpc_rate = refresh_node_rpc_rate
        self.graph_size = graph_size

        self.metrics = None

        self.chain = 'N/A'
        self.version = 'N/A'
        self.latest_downloaded_checkpoint_deque = deque(maxlen=self.graph_size)
        self.confirmations_issued_total_deque = deque(maxlen=self.graph_size)
        self.checkpoint_downloader_lag_deque = deque(maxlen=self.graph_size)
        self.persisted_events_deque = deque(maxlen=self.graph_size)
        self.pending_events_deque = deque(maxlen=self.graph_size)
        self.highest_finished_event_deque = deque(maxlen=self.graph_size)
        self.recover_blob_backlog_queued_deque = deque(maxlen=self.graph_size)


        self.status = 'N/A'
        self.epoch = 'N/A'
        self.shards_owned = 'N/A'
        self.shards_ready = 'N/A'
        self.shards_inTransfer = 'N/A'
        self.shards_inRecovery = 'N/A'
        self.shards_unknown = 'N/A'
        self.workers_num = 'N/A'

        self.uptime = None
        self.persisted_events = None
        self.pending_events = None
        self.highest_finished_event = None
        self.confirmations_issued_total = None
        self.total_downloaded_checkpoints = None
        self.latest_downloaded_checkpoint = None
        self.recover_blob_backlog_in_progress = None
        self.checkpoint_downloader_lag = None

    async def update_data(
        self, update_func: Callable, refresh_interval: int, last_update_time_attr: str
    ) -> None:
        if (
            not hasattr(self, last_update_time_attr)
            or (asyncio.get_event_loop().time() - getattr(self, last_update_time_attr))
            >= refresh_interval
        ):
            await update_func()
            setattr(self, last_update_time_attr, asyncio.get_event_loop().time())

    async def batch_update_data(self):

        await asyncio.gather(
            self.update_data(
                self.update_metrics, self.refresh_metrics_rate, "_last_metrics_update"
            ),
            self.update_data(
                self.update_node_status, self.refresh_node_rpc_rate, "_last_metrics_update"
            )
        )

    def ascii_number(self, number: int):
        return figlet_format(text=str(number), font='small')

    async def update_node_status(self):

        try:
            health = await self.session.get_storage_status()
            if health:
                logger.info(f"Fetched node status. Parsing ...")
                self.status = health['success']['data']['nodeStatus']
                self.epoch = str(health['success']['data']['epoch'])
                self.shards_owned = str(health['success']['data']['shardSummary']['owned'])
                self.shards_ready = str(health['success']['data']['shardSummary']['ownedShardStatus']['ready'])
                self.shards_inTransfer = str(health['success']['data']['shardSummary']['ownedShardStatus']['inTransfer'])
                self.shards_inRecovery = str(health['success']['data']['shardSummary']['ownedShardStatus']['inRecovery'])
                self.shards_unknown = str(health['success']['data']['shardSummary']['ownedShardStatus']['unknown'])
            else:
                logger.error(f"Failed to update node status")

        except Exception as e:
            logger.error(f"An error occurred while updating node status {e}")

    async def update_metrics(self):
        try:
            metrics = await self.session.get_storage_metrics()
            if metrics:
                logger.info(f"Fetched node metrics. Parsing ...")
                self.metrics = metrics
                self.parse_metrics()
                return

            else:
                logger.error(f"Failed to update node metrics")

        except Exception as e:
            logger.error(f"An error occurred while updating node metrics: {e}")


    def parse_metrics(self):

        self.chain = str(StorageMetrics.get_chain_identifier(self.metrics)) or 'N/A'
        self.version = str(StorageMetrics.get_walrus_build_info(self.metrics)) or 'N/A'
        self.uptime = StorageMetrics.get_uptime(self.metrics) or 'N/A'
        self.workers_num = str(StorageMetrics.get_checkpoint_downloader_num_workers(self.metrics)) or 'N/A'
        
        
        self.total_downloaded_checkpoints = StorageMetrics.get_total_downloaded_checkpoints(self.metrics)

        pending_events = StorageMetrics.get_event_cursor_progress(self.metrics, state='pending')
        if pending_events is not None:
            self.pending_events = str(pending_events)
            self.pending_events_deque.append(pending_events)
        else:
            logger.warning("walrus_event_cursor_progress [pending] not presented")

        persisted_events = StorageMetrics.get_event_cursor_progress(self.metrics, state='persisted')
        if persisted_events is not None:
            self.persisted_events = persisted_events
            self.persisted_events_deque.append(persisted_events)
        else:
            logger.warning("walrus_event_cursor_progress [persisted] not presented")

        highest_finished_event = StorageMetrics.get_event_cursor_progress(self.metrics, state='highest_finished')
        if highest_finished_event is not None:
            self.highest_finished_event_deque.append(highest_finished_event)
            self.highest_finished_event = str(highest_finished_event)
        else:
            logger.warning("walrus_event_cursor_progress [highest_finished] not presented")

        confirmations_issued_total = StorageMetrics.get_confirmations_issued_total(self.metrics)
        if confirmations_issued_total is not None:
            self.confirmations_issued_total_deque.append(confirmations_issued_total)
            self.confirmations_issued_total = str(confirmations_issued_total)
        else:
            logger.warning("walrus_storage_confirmations_issued_total not presented")

        latest_downloaded_checkpoint = StorageMetrics.get_latest_downloaded_checkpoint(self.metrics)
        if latest_downloaded_checkpoint is not None:
            self.latest_downloaded_checkpoint_deque.append(latest_downloaded_checkpoint)
            self.latest_downloaded_checkpoint = str(latest_downloaded_checkpoint)
        else:
            logger.warning("event_processor_latest_downloaded_checkpoint not presented")

        checkpoint_downloader_lag = StorageMetrics.get_checkpoint_downloader_lag(self.metrics)
        if checkpoint_downloader_lag is not None:
            self.checkpoint_downloader_lag_deque.append(checkpoint_downloader_lag)
            self.checkpoint_downloader_lag = checkpoint_downloader_lag
        else:
            logger.warning("checkpoint_downloader_checkpoint_lag not presented")

        blob_backlog_in_progress = StorageMetrics.get_walrus_recover_blob_backlog(self.metrics, 'in-progress')
        if blob_backlog_in_progress is not None:
            self.recover_blob_backlog_in_progress = blob_backlog_in_progress
        else:
            logger.warning("walrus_recover_blob_backlog [in-progress] not presented. Setting zero")
            self.recover_blob_backlog_in_progress = 0

        blob_backlog_in_queued = StorageMetrics.get_walrus_recover_blob_backlog(self.metrics, 'queued')
        if blob_backlog_in_queued is not None:
            self.recover_blob_backlog_queued_deque.append(blob_backlog_in_queued)
        else:
            logger.warning("walrus_recover_blob_backlog [queued] not presented. Setting zero")
            self.recover_blob_backlog_queued.append(0)

    def create_shards_panel(self):

        owned_color = "cyan"
        ready_color = "green"
        unknown_color = "yellow"
        in_recovery_color = "yellow"
        in_transfer_color = "yellow"

        content = ""
        content += f"[bold {owned_color}]OWNED:[/bold {owned_color}] [bold]{self.shards_owned}[/bold]\n"
        content += f"[bold {ready_color}]READY:[/bold {ready_color}] [bold]{self.shards_ready}[/bold]\n"
        content += f"[bold {unknown_color}]UNKNOWN:[/bold {unknown_color}] [bold]{self.shards_unknown}[/bold]\n"
        content += f"[bold {in_recovery_color}]inRECOVERY:[/bold {in_recovery_color}] [bold]{self.shards_inRecovery}[/bold]\n"
        content += f"[bold {in_transfer_color}]inTRANSFER:[/bold {in_transfer_color}] [bold]{self.shards_inTransfer}[/bold]"

        return Panel(content, expand=True, title="[bold]SHARDS[/bold]", border_style="cyan")

    def create_checkpoint_lag_panel(self):
        value = self.ascii_number(self.checkpoint_downloader_lag) if isinstance(self.checkpoint_downloader_lag, int) else str(self.checkpoint_downloader_lag)
        color = "red" if isinstance(self.checkpoint_downloader_lag, int) and self.checkpoint_downloader_lag > 0 else "green"

        text = Text(value, style=Style(bold=True, underline=False, color=color))
        centered_text = Align.center(text, vertical="middle")
        return Panel(centered_text, expand=True, title="[bold] CHECKPOINTS LAG[/bold]", border_style=color)

    def create_in_progress_recover_blob_backlog_panel(self):
        value = self.ascii_number(self.recover_blob_backlog_in_progress) if isinstance(self.recover_blob_backlog_in_progress, int) else str(self.recover_blob_backlog_in_progress)
        color = "yellow" if isinstance(self.recover_blob_backlog_in_progress, int) and self.recover_blob_backlog_in_progress > 0 else "green"
        text = Text(value, style=Style(bold=True, underline=False, color=color))
        centered_text = Align.center(text, vertical="middle")
        return Panel(centered_text, expand=True, title="[bold] BLOBS RECOVER (in progress)[/bold]", border_style=color)

    def create_total_persisted_events_panel(self):
        value = self.ascii_number(self.persisted_events) if isinstance(self.persisted_events, int) else str(self.persisted_events)
        color = "green"
        text = Text(value, style=Style(bold=True, underline=False, color=color))
        centered_text = Align.center(text, vertical="middle")
        return Panel(centered_text, expand=True, title="[bold] PERSISTED EVENTS[/bold]", border_style=color)

    def create_total_downloaded_checkpoints_panel(self):
        value = self.ascii_number(self.total_downloaded_checkpoints) if isinstance(self.total_downloaded_checkpoints, int) else str(self.total_downloaded_checkpoints)
        color = "cyan"
        text = Text(value, style=Style(bold=True, underline=False, color=color))
        centered_text = Align.center(text, vertical="middle")
        return Panel(centered_text, expand=True, title="[bold] TOTAL DOWNLOADED CHECKPOINTS[/bold]", border_style=color)


    def create_status_panel(self):
        try:
            if self.uptime:
                _uptime = covert_seconds_to_dhm(seconds=self.uptime)
            else:
                _uptime = 'N/A'
        except Exception as e:
            logger.error(f"An unexpected error occurred while converting seconds to dhm format: {e}")
            _uptime = 'N/A'

        status_color = "green" if self.status == "Active" else "red"
        version_color = "cyan"
        epoch_color = "green"
        uptime_color = "cyan"
        workser_color = "green"

        content = ""
        content += f"[bold {status_color}]STATUS:[/bold {status_color}] [bold]{self.status}[/bold]\n"
        content += f"[bold {version_color}]VERSION:[/bold {version_color}] [bold]{self.version}[/bold]\n"
        content += f"[bold {epoch_color}]EPOCH:[/bold {epoch_color}] [bold]{self.epoch}[/bold]\n"
        content += f"[bold {uptime_color}]UPTIME:[/bold {uptime_color}] [bold]{_uptime}[/bold]\n"
        content += f"[bold {workser_color}]WORKERS:[/bold {workser_color}] [bold]{self.workers_num}[/bold]"

        return Panel(content, expand=True, title="[bold]NODE INFO[/bold]", border_style="cyan")

    def create_latest_downloaded_checkpoint_graph_panel(self):
        graph = acp.plot(self.latest_downloaded_checkpoint_deque, {'height': 10, 'format': '{:8.0f}'})
        return Panel(graph, expand=False, title="[bold][green]Latest Checkpoint[/bold][/green]", title_align="left", box=box.SIMPLE)

    # def create_checkpoint_downloader_lag_graph_panel(self):
    #     graph = acp.plot(self.checkpoint_downloader_lag_deque, {'height': 10, 'format': '{:8.0f}'})
    #     return Panel(graph, expand=False, title="[bold][red]Checkpoints Lag[/bold][/red]", title_align="left", box=box.SIMPLE)
        
    def create_confirmations_issued_total_graph_panel(self):
        graph = acp.plot(self.confirmations_issued_total_deque, {'height': 10, 'format': '{:8.0f}'})
        return Panel(graph, expand=False, title="[bold][cyan]Confirmations[/bold][/cyan]", title_align="left", box=box.SIMPLE)

    def create_persisted_events_graph_panel(self):
        graph = acp.plot(self.persisted_events_deque, {'height': 10, 'format': '{:8.0f}'})
        return Panel(graph, expand=False, title="[bold][green]Persisted Events[/bold][/green]",title_align="left", box=box.SIMPLE)
    
    def create_highest_finished_event_graph_panel(self):
        graph = acp.plot(self.highest_finished_event_deque, {'height': 10, 'format': '{:8.0f}'})
        return Panel(graph, expand=False, title="[bold][cyan]Highest Finished Event[/bold][/cyan]", title_align="left", box=box.SIMPLE)
    
    def create_pending_events_graph_panel(self):
        graph = acp.plot(self.pending_events_deque, {'height': 10, 'format': '{:8.0f}'})
        return Panel(graph, expand=False, title="[bold][red]Pending Events[/bold][/red]", title_align="left", box=box.SIMPLE)

    # def create_in_progress_recover_blob_backlog_panel(self):
    #     graph = acp.plot(self.recover_blob_backlog_in_progress_deque, {'height': 10, 'format': '{:8.0f}'})
    #     return Panel(graph, expand=False, title="[bold][yellow]Blobs Recover In Progress[/bold][/yellow]", title_align="left", box=box.SIMPLE)
    
    def create_queued_recover_blob_backlog_graph_panel(self):
        graph = acp.plot(self.recover_blob_backlog_queued_deque, {'height': 10, 'format': '{:8.0f}'})
        return Panel(graph, expand=False, title="[bold][yellow]Blobs Recover Queued[/bold][/yellow]", title_align="left", box=box.SIMPLE)
    
    async def start(self):
        try:
            with Live(
                self.layout,
                refresh_per_second=self.refresh_per_second,
                auto_refresh=False,
                screen=True,
            ) as live:

                while True:
                    await self.batch_update_data()
                    # log_renderable = self.rich_logger.get_logs()
                    # log_panel = Panel(Text.from_ansi(log_renderable), expand=True, title="[bold]App Logs[/bold]", title_align="center", border_style="black")
                    # self.layout["logs"].update(log_panel)

                    status_panel = self.create_status_panel()
                    shards_panel = self.create_shards_panel()
                    checkpoint_lag_panel = self.create_checkpoint_lag_panel()
                    total_persisted_events_panel = self.create_total_persisted_events_panel()
                    total_downloaded_checkpoints_panel = self.create_total_downloaded_checkpoints_panel()
                    latest_downloaded_checkpoint_graph_panel = self.create_latest_downloaded_checkpoint_graph_panel()
                    # checkpoint_downloader_lag_graph_panel = self.create_checkpoint_downloader_lag_graph_panel()
                    confirmations_issued_total_graph_panel = self.create_confirmations_issued_total_graph_panel()
                    persisted_events_graph_panel = self.create_persisted_events_graph_panel()
                    pending_events_graph_panel = self.create_pending_events_graph_panel()
                    highest_finished_event_graph_panel = self.create_highest_finished_event_graph_panel()
                    recover_blob_backlog_queued_graph_panel = self.create_queued_recover_blob_backlog_graph_panel()
                    recover_blob_backlog_in_progress_panel = self.create_in_progress_recover_blob_backlog_panel()

                    self.layout["header"]["Status"].update(status_panel)
                    self.layout["header"]["Shards"].update(shards_panel)
                    self.layout["header"]["Checkpoint Lag"].update(checkpoint_lag_panel)
                    self.layout["header"]["Blob_Recover_Backlog_In_Progress"].update(recover_blob_backlog_in_progress_panel)
                    self.layout["header"]["Total Persisted Events"].update(total_persisted_events_panel)
                    self.layout["header"]["Total Downloaded Checkpoints"].update(total_downloaded_checkpoints_panel)

                    self.layout["main"]["Latest Downloaded Checkpoint"].update(latest_downloaded_checkpoint_graph_panel)
                    self.layout["main"]["Blob_Recover_Backlog_Queued"].update(recover_blob_backlog_queued_graph_panel)
                    self.layout["main"]["Confirmations Issued"].update(confirmations_issued_total_graph_panel)

                    self.layout["events"]["Persisted Events"].update(persisted_events_graph_panel)
                    self.layout["events"]["Pending Events"].update(pending_events_graph_panel)
                    self.layout["events"]["Highest Finished Event"].update(highest_finished_event_graph_panel)

                    live.refresh()
                    await asyncio.sleep(1 / self.refresh_per_second)

        finally:
            self.console.clear()