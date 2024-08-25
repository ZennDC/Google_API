import http.server
import socketserver
import os

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def list_directory(self, path):
        try:
            files = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        files.sort()
        response = "<html><body><h1>Directory listing</h1><ul>"
        for file in files:
            fullpath = os.path.join(path, file)
            displayname = linkname = file
            if os.path.isdir(fullpath):
                displayname = f"{file}/"
                linkname = f"{file}/"
            response += f'<li><a href="{linkname}">{displayname}</a></li>'
        response += "</ul></body></html>"
        
        encoded = response.encode('utf-8', 'surrogateescape')
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)
        return None

PORT = 8000

with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
    print(f"Serving HTTP on port {PORT}")
    httpd.serve_forever()
