import argparse

def validate_log_level(value: str) -> str:
    levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if value.upper() in levels:
        return value.upper()
    else:
        raise argparse.ArgumentTypeError(f"Invalid log level: {value}")

def parse_args():
    parser = argparse.ArgumentParser(
        description="Global arguments for the application",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--logs-lvl",
        default="DEBUG",
        type=validate_log_level,
        help="Set the logging level [DEBUG, INFO, WARNING, ERROR]",
    )
    parser.add_argument(
        "--logs-path",
        type=str,
        help="Path to the log file. If not provided, logs will not be stored",
        required=False,
    )

    parser.add_argument(
        "--dashboard-refresh-per-second",
        type=float,
        help="Refresh rate of the table per second",
        required=False,
        default=5,
    )

    parser.add_argument(
        "--dashboard-graph-size",
        type=int,
        help="Edit size of graphs in case they are borken due too small screen size",
        required=False,
        default=60,
    )

    parser.add_argument(
        "--storage-metrics-url",
        type=str,
        help="Storage node prometheus metrics url",
        required=False,
        default="http://127.0.0.1:9184/metrics"
    )

    parser.add_argument(
        "--storage-rpc-url",
        type=str,
        help="Storage node RPC metrics url",
        required=False,
        default="http://127.0.0.1:9185"
    )

    parser.add_argument(
        "--storage-refresh-metrics-rate",
        type=float,
        help="Refresh metrics every N second",
        required=False,
        default=2,
    )

    parser.add_argument(
        "--storage-refresh-rpc-rate",
        type=float,
        help="Refresh rpc status every N second (/v1/health)",
        required=False,
        default=20,
    )



    args = parser.parse_args()

    return args


args = parse_args()