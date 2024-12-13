import asyncio
import argparse
import asyncio
import ipaddress
import sys

from bot.bot_main import start_bot
from api.api_main import run_uvicorn_from_async


def validate_port(port_str):
    try:
        port = int(port_str)
        if 1 <= port <= 65535:
            return port
        else:
            raise argparse.ArgumentTypeError(f"Port number must be between 1 and 65535, got {port}.")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Port must be an integer, got '{port_str}'.")


def validate_host(host_str):
    try:
        ipaddress.ip_address(host_str)
        return host_str
    except ValueError:
        raise argparse.ArgumentTypeError(f"Host '{host_str}' is not a valid IP address.")



def parse_arguments():
    parser = argparse.ArgumentParser(description="Asynchronous App with Optional Host and Port Parameters.")

    parser.add_argument(
        '--host',
        type=validate_host,
        default='127.0.0.1',
        help='Host address'
    )

    parser.add_argument(
        '--port',
        type=validate_port,
        default=8000,
        help='Port number'
    )

    return parser.parse_args()


async def main(args):
    await asyncio.gather(
        run_uvicorn_from_async(args.host, args.port),
        start_bot(),
    )

if __name__ == "__main__":
    args = parse_arguments()
    asyncio.run(main(args))
