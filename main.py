import asyncio
from utils.args import args
from utils.logger import logger
from src.storage_dashboard import StorageDashboard
from src.aio_http_client import AioHttpCalls

async def run_dashboard(dashboard: StorageDashboard):
    await dashboard.start()

async def main():
    logger.info("Starting Dashboard...")

    async with AioHttpCalls(storage_metrics=args.storage_metrics_url, storage_rpc=args.storage_rpc_url) as session:
        dashboard = StorageDashboard(
            session=session,
            refresh_metrics_rate=args.storage_refresh_metrics_rate,
            refresh_node_rpc_rate=args.storage_refresh_rpc_rate,
            refresh_per_second=args.dashboard_refresh_per_second,
            graph_size=args.dashboard_graph_size
            )

        try:
            await run_dashboard(dashboard)
        except asyncio.CancelledError:
            logger.info("Dashboard cancelled.")
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Exiting gracefully.")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            logger.info("Goodbye!")

if __name__ ==  "__main__":
    asyncio.run(main())