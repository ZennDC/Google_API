import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
import json

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Define the scope of access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# The port you want to listen on
PORT = 8000

class MyRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('index.html', 'rb') as file:
                self.copyfile(file, self.wfile)
        elif self.path == '/auth_url':
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
            auth_url, _ = flow.authorization_url(prompt='consent')
            response = {'auth_url': auth_url}
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_error(404, "File not found")

    def do_POST(self):
        if self.path == '/submit_code':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            code = data.get('code')
            print("Received code:", code)

            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            flow.fetch_token(code=code)
            creds = flow.credentials

            service = build('gmail', 'v1', credentials=creds)
            results = service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])

            response = {'labels': [label['name'] for label in labels]}
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_error(404, "Endpoint not found")

def main():
    """Create a TCP server"""
    with socketserver.TCPServer(("", PORT), MyRequestHandler) as httpd:
        print("Server running on port", PORT)
        httpd.serve_forever()

if __name__ == '__main__':
    main()
