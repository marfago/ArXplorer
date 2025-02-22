import signal
import sys
import threading
import time

import dspy  # DSPy has a weird bound to the main thread. Assertions will not work if the module is imported in a thread
from waitress.server import create_server

from arxplorer.agent.orchestrator import Orchestrator
from arxplorer.common.common import configure_logging, instrument_telemetry
from arxplorer.configuration import ConfigurationManager
from arxplorer.persitence.database import DbOperations
from arxplorer.ui.dash_app import app

assert dspy is not None


class ArXplorerServer:
    def __init__(self, host="0.0.0.0", port=6007):
        self._shutdown_event = threading.Event()
        self.host = host
        self.port = port
        self._waitress_server = create_server(app.server, host=self.host, port=self.port)
        self._orchestrator = Orchestrator()

    def signal_handler(self, sig, frame):
        print("\nCtrl+C detected.\nInitiating graceful shutdown. It may take a while....")
        self._shutdown_event.set()
        self._orchestrator.stop()
        self._waitress_server.close()

    def dash_server(self):
        self._waitress_server.run()

    def background_server(self):
        self._orchestrator.start()

    def start(self):
        instrument_telemetry()
        configure_logging(level=ConfigurationManager.get_log_level())

        if not ConfigurationManager.is_any_key_available():
            print(
                """\nNo api keys found.\nPlease refer to https://github.com/marfago/ArXplorer/blob/main/README.md#installation."""
            )
            sys.exit(-1)

        signal.signal(signal.SIGINT, self.signal_handler)

        DbOperations.create_or_update_tables()
        dash_thread = threading.Thread(target=self.dash_server)
        background_thread = threading.Thread(target=self.background_server)

        dash_thread.start()
        background_thread.start()

        print(f"Server started and serving at {self.host}:{self.port}")

        while True:
            if not dash_thread.is_alive() and not background_thread.is_alive():
                break
            time.sleep(0.5)

        print("All servers stopped. Exiting.")
        sys.exit(0)


def main():
    print("Starting server")
    ArXplorerServer().start()
    print("Server stopped")


if __name__ == "__main__":
    main()
