import http.server
import socketserver
import threading

class ControllableHTTPServer:
    def __init__(self, host="localhost", port=8000):
        self.host = host
        self.port = port
        self.handler = http.server.SimpleHTTPRequestHandler
        self.httpd = socketserver.TCPServer((self.host, self.port), self.handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever)
        self.thread.daemon = True
        self.running = False

    def start(self):
        if not self.running:
            self.thread.start()
            self.running = True
            print(f"Server started on {self.host}:{self.port}")

    def stop(self):
        if self.running:
            self.httpd.shutdown()
            self.thread.join()
            self.httpd.server_close()
            self.running = False
            print("Server stopped")

    def status(self):
        return "running" if self.running else "stopped"

if __name__ == "__main__":
    server = ControllableHTTPServer()

    while True:
        command = input("Enter command (start/stop/status/exit): ").strip().lower()
        if command == "start":
            server.start()
        elif command == "stop":
            server.stop()
        elif command == "status":
            print(f"Server is {server.status()}")
        elif command == "exit":
            if server.running:
                server.stop()
            break
        else:
            print("Unknown command")
