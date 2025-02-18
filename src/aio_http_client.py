from typing import Optional, Literal
import aiohttp
import traceback
from utils.logger import logger

class AioHttpCalls:

    def __init__(
        self,
        storage_rpc: Optional[str] = None,
        storage_metrics: Optional[str] = None,
        session: Optional[str] = None,
        timeout: int = 3,
    ):

        self.timeout = timeout
        self.session = session
        self._manage_session = session is None # Indicates if this class should manage the session lifecycle.  

        self.storage_rpc = storage_rpc
        self.storage_metrics = storage_metrics

    async def __aenter__(self):
        if not self.session:
            logger.debug(f"Creating aiohttp session")
            self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self._manage_session and self.session:
            logger.debug(f"Closing aiohttp session")
            await self.session.close()

    async def handle_rpc_request(self, url, callback):
        try:
            logger.debug(f"Requesting {url}")
            async with self.session.get(url, timeout=self.timeout, ssl=False) as response:
                if response.status == 200:
                    return await callback(response.json())
                else:
                    logger.error(
                        f"Request to {url} failed with status code {response.status}"
                    )
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Issue with making request to {url}: {e}")
        except TimeoutError as e:
            logger.error(f"Issue with making request to {url}. TimeoutError: {e}")
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while making request to {url}: {e}"
            )
            traceback.print_exc()

    async def handle_metrics_request(self, url, callback):
        try:
            logger.debug(f"Requesting {url}")
            async with self.session.get(url, timeout=self.timeout) as response:
                if response.status == 200:
                    return await callback(response.text())
                else:
                    logger.error(
                        f"Request to {url} failed with status code {response.status}"
                    )
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Issue with making request to {url}: {e}")
        except TimeoutError as e:
            logger.error(f"Issue with making request to {url}. TimeoutError: {e}")
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while making request to {url}: {e}"
            )
            traceback.print_exc()

    async def get_storage_metrics(self) -> str:
        
        async def process_response(response):
            data = await response
            return data

        return await self.handle_metrics_request(self.storage_metrics, process_response)

    async def get_storage_status(self) -> str:
        
        async def process_response(response):
            data = await response
            return data

        return await self.handle_rpc_request(f"{self.storage_rpc}/v1/health", process_response)
    