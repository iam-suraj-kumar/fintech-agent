import os
import socket
import subprocess
import sys


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main() -> None:
    port = find_free_port()
    script_path = os.path.join(os.path.dirname(__file__), "ui", "app.py")
    cmd = [sys.executable, "-m", "streamlit", "run", script_path, "--server.port", str(port)]

    print(f"Starting Streamlit on http://127.0.0.1:{port}")
    os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    main()
