# run_bot.py

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from bot.bot_manager import DisulubincaBot

if __name__ == "__main__":
    try:
        bot = DisulubincaBot()
        bot.iniciar_polling()
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido manualmente por el usuario.")
    except Exception as e:
        print(f"\n❌ Error fatal preparando o ejecutando el bot: {e}")