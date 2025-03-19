import re
from typing import Literal, Optional

class StorageMetrics:
    @staticmethod
    def _get_value(metrics: str, pattern: str) -> Optional[int]:
        match = re.search(pattern, metrics)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def get_walrus_epoch(metrics: str) -> Optional[int]:
        pattern = r"walrus_current_epoch\s+(\d+)"
        return StorageMetrics._get_value(metrics, pattern)

    @staticmethod
    def get_latest_downloaded_checkpoint(metrics: str) -> Optional[int]:
        pattern = r"event_processor_latest_downloaded_checkpoint\s+(\d+)"
        return StorageMetrics._get_value(metrics, pattern)

    @staticmethod
    def get_walrus_shards_owned(metrics: str) -> Optional[int]:
        pattern = r"walrus_shards_owned\s+(\d+)"
        return StorageMetrics._get_value(metrics, pattern)

    @staticmethod
    def get_checkpoint_downloader_lag(metrics: str) -> Optional[int]:
        pattern = r"checkpoint_downloader_checkpoint_lag\s+(\d+)"
        return StorageMetrics._get_value(metrics, pattern)

    @staticmethod
    def get_uptime(metrics: str) -> Optional[int]:
        pattern = r"uptime\{[^}]*\}\s+(\d+)"
        return StorageMetrics._get_value(metrics, pattern)

    @staticmethod
    def get_chain_identifier(metrics: str) -> Optional[str]:
        pattern = r'chain_identifier="([^"]+)"'
        match = re.search(pattern, metrics)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def get_walrus_build_info(metrics: str) -> Optional[str]:
        pattern = r'walrus_build_info\{version="([^"]+)"\}'
        match = re.search(pattern, metrics)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def get_event_cursor_progress(metrics: str, state: Literal["persisted", "pending", "highest_finished"]) -> Optional[int]:
        pattern = rf'walrus_event_cursor_progress\{{state="{state}"\}}\s+(\d+)'
        return StorageMetrics._get_value(metrics, pattern)

    @staticmethod
    def get_checkpoint_downloader_num_workers(metrics: str) -> Optional[int]:
        pattern = r"checkpoint_downloader_num_workers\s+(\d+)"
        return StorageMetrics._get_value(metrics, pattern)

    @staticmethod
    def get_confirmations_issued_total(metrics: str) -> Optional[int]:
        pattern = r"walrus_storage_confirmations_issued_total\s+(\d+)"
        return StorageMetrics._get_value(metrics, pattern)

    @staticmethod
    def get_total_downloaded_checkpoints(metrics: str) -> Optional[int]:
        pattern = r"event_processor_total_downloaded_checkpoints\s+(\d+)"
        return StorageMetrics._get_value(metrics, pattern)

    @staticmethod
    def get_walrus_recover_blob_backlog(metrics: str, state: Literal["queued", "in-progress",]) -> Optional[int]:
        pattern = rf'walrus_recover_blob_backlog\{{state="{state}"\}}\s+(\d+)'

        return StorageMetrics._get_value(metrics, pattern)
    