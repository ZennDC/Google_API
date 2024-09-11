import http.server
import socketserver
from urllib.parse import urlparse, parse_qs

# The port you want to listen on
PORT = 8000

# The URL of the website you want to redirect users to
REDIRECT_URL = "http://example.com"

class MyRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Redirect all GET requests to the specified URL
        if self.path == '/':
            self.send_response(302)
            self.send_header('Location', REDIRECT_URL)
            self.end_headers()
        # Handle callback and extract the code
        elif self.path.startswith('/callback'):
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            code = query_params.get('code', [''])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write("Code received successfully: {}".format(code).encode())

# Create a TCP server
with socketserver.TCPServer(("", PORT), MyRequestHandler) as httpd:
    print("Server running on port", PORT)
    # Serve requests indefinitely
    httpd.serve_forever()
