import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
import json

# The port you want to listen on
PORT = 8000

class MyRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Serve the HTML file
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('index.html', 'rb') as file:
                self.copyfile(file, self.wfile)

        # Handle callback and extract the code
        elif self.path.startswith('/submit_code'):
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            code = query_params.get('code', [''])[0]

            # You can do something with the code here, for example, print it
            print("Received code:", code)

            # Respond with a success message
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Code received successfully", "code": code}).encode())

# Create a TCP server
with socketserver.TCPServer(("", PORT), MyRequestHandler) as httpd:
    print("Server running on port", PORT)
    # Serve requests indefinitely
    httpd.serve_forever()
