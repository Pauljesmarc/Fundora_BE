#!/usr/bin/env python3
"""
Simple HTTP server to serve the HTML form for testing
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

# Set the directory where the HTML file is located
html_dir = Path(__file__).parent
os.chdir(html_dir)

PORT = 8080

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers to allow cross-origin requests
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

if __name__ == "__main__":
    try:
        with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
            print(f"🚀 HTML Form Server starting on http://localhost:{PORT}")
            print(f"📁 Serving files from: {html_dir}")
            print(f"🌐 Open: http://localhost:{PORT}/Company_Information_Form.html")
            print("\n💡 Instructions:")
            print("1. Open the URL above in your browser")
            print("2. Set the auth token in browser console:")
            print("   localStorage.setItem('authToken', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU5MjAyODM2LCJpYXQiOjE3NTkyMDI1MzYsImp0aSI6IjVjYmNmMDhkZjFjNjRjZWRhMTA1ZDUxMWZmZjA4NGMzIiwidXNlcl9pZCI6IjQifQ.UQB1Sibrad9jHaWBHH8ipJpN9HACYdvj2JJXrTxsB2k');")
            print("3. Fill out the form and submit!")
            print("\n🛑 Press Ctrl+C to stop the server")
            
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped.")
    except Exception as e:
        print(f"❌ Error starting server: {e}")