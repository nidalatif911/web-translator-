"""
Web Translator - Real-Time Voice, Document & Webpage Translation
Universal entry point supporting both the Modern Web Studio and the Native Desktop GUI.
"""

import sys
import os
import socket
import argparse
import webbrowser

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def get_free_port(preferred_port: int = 8000) -> int:
    """Checks if preferred_port is available; if busy, finds the next open port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", preferred_port))
            return preferred_port
        except OSError:
            pass

    for port in range(preferred_port + 1, preferred_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def run_web(port=8000, auto_open=True):
    """Starts the FastAPI Web Server and opens the browser."""
    import uvicorn
    from app.config import APP_NAME, APP_VERSION

    active_port = get_free_port(port)
    if active_port != port:
        print(f"\n[Notice] Port {port} is currently in use. Automatically switched to port {active_port}.")

    url = f"http://localhost:{active_port}"
    print("\n" + "=" * 60)
    print(f"  {APP_NAME} v{APP_VERSION}")
    print(f"  Web application available at: {url}")
    print("=" * 60 + "\n")

    if auto_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    uvicorn.run("server:app", host="0.0.0.0", port=active_port, reload=False)


def run_desktop():
    """Starts the native CustomTkinter desktop GUI."""
    from app.ui import ModernTranslatorApp
    from app.config import APP_NAME

    print(f"\n[{APP_NAME}] Launching desktop application...")
    app = ModernTranslatorApp()
    app.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Web Translator - Real-Time Voice, Document & Webpage Translation")
    parser.add_argument(
        "--mode",
        choices=["web", "desktop"],
        default="web",
        help="Select interface mode: 'web' for the modern web app (default) or 'desktop' for the native GUI."
    )
    parser.add_argument("--port", type=int, default=8000, help="Port for the web server (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open the browser on launch")

    args = parser.parse_args()

    if args.mode == "desktop":
        run_desktop()
    else:
        run_web(port=args.port, auto_open=not args.no_browser)


if __name__ == "__main__":
    main()
