import http.server
import socketserver

PORT = 4444  # You can choose any port number you like

class RedirectHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # URL to redirect to
        target_url = "http://example.com"  # Replace with your target website URL
        self.send_response(302)  # HTTP 301 Moved Permanently, 302 Temporary
        self.send_header('Location', target_url)
        self.end_headers()

with socketserver.TCPServer(("", PORT), RedirectHandler) as httpd:
    print(f"Serving at port {PORT}")
    httpd.serve_forever()
