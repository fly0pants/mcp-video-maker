import http.server
import socketserver
import os
import webbrowser
from urllib.parse import urlparse

# 配置
PORT = 8080
HOST = "0.0.0.0"  # Allow connections from any IP
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def do_GET(self):
        # 处理根路径请求
        if self.path == '/':
            self.path = '/index.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

def run_server():
    """运行简单的HTTP服务器"""
    handler = MyHttpRequestHandler
    
    with socketserver.TCPServer((HOST, PORT), handler) as httpd:
        print(f"前端服务器启动在 http://{HOST}:{PORT}")
        print("按Ctrl+C停止服务器")
        
        # 自动打开浏览器 (still using localhost for local access)
        webbrowser.open(f"http://localhost:{PORT}")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止")

if __name__ == "__main__":
    run_server() 