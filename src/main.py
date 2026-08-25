# run_bot.py

import sys
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from bot.bot_manager import DisulubincaBot


# Servidor web mínimo para cumplir el Port Binding de Render.
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"INCABOT OK")

    def log_message(self, format, *args):
        pass


def start_health_check_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

if __name__ == "__main__":
    try:
        Thread(target=start_health_check_server, daemon=True).start()

        bot = DisulubincaBot()
        bot.iniciar_polling()
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido manualmente por el usuario.")
    except Exception as e:
        print(f"\n❌ Error fatal preparando o ejecutando el bot: {e}")