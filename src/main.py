import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from bot.bot_manager import DisulubincaBot

if __name__ == "__main__":
    # Instanciamos el manager del bot de Telegram
    bot = DisulubincaBot()
    
    # Encendemos el polling (escucha activa en segundo plano)
    bot.iniciar_polling()