# src/bot/notifications.py

import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ExtBot

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    async def notificar_nuevo_registro_a_supervisores(bot: ExtBot, supervisores_telegram_ids: list[int], usuario_data: dict) -> None:
        """
        [PUSH PROACTIVO]
        Envía una alerta con botones Inline a los supervisores cuando un vendedor solicita registro.
        """
        telegram_id = usuario_data.get("telegram_id")
        nombre = usuario_data.get("nombre")
        ruta = usuario_data.get("ruta")

        texto = (
            f"🔔 **NUEVA SOLICITUD DE ACCESO**\n\n"
            f"👤 **Vendedor:** {nombre}\n"
            f"📍 **Ruta Solicitada:** Ruta {ruta}\n"
            f"🆔 **Telegram ID:** `{telegram_id}`\n\n"
            f"¿Deseas autorizar el acceso a este vendedor?"
        )

        # Botones Inline para aprobación directa en Telegram
        keyboard = [
            [
                InlineKeyboardButton("✅ Aprobar", callback_data=f"aprobar_usr:{telegram_id}:{ruta}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar_usr:{telegram_id}:{ruta}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        for sup_id in supervisores_telegram_ids:
            try:
                await bot.send_message(
                    chat_id=sup_id,
                    text=texto,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"❌ Error enviando notificación push al supervisor {sup_id}: {e}")

    @staticmethod
    async def notificar_resultado_autorizacion(bot: ExtBot, vendedor_telegram_id: int, ruta: int, aprobado: bool) -> None:
        """
        [PUSH PROACTIVO]
        Notifica directamente al vendedor cuando su solicitud fue APROBADA o RECHAZADA.
        """
        if aprobado:
            texto = (
                f"🎉 **¡TU CUENTA HA SIDO APROBADA!**\n\n"
                f"Ya has sido autorizado para gestionar la **Ruta {ruta}**.\n"
                f"Usa los botones del menú o envía `/start` para comenzar a enviar tus reportes."
            )
        else:
            texto = (
                f"🚫 **SOLICITUD RECHAZADA**\n\n"
                f"Tu solicitud para la **Ruta {ruta}** no ha sido aprobada por la supervisión.\n"
                f"Comunícate con tu supervisor si consideras que es un error."
            )

        try:
            await bot.send_message(
                chat_id=vendedor_telegram_id,
                text=texto,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"❌ Error notificando al vendedor {vendedor_telegram_id}: {e}")