import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
from datetime import datetime

# Configuración del logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token del bot de Telegram (configura tu token aquí)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# URL de la API de ProCyclingStats o fuente de datos
# Nota: Puedes usar web scraping o una API específica
PROCYCLING_API_URL = "https://api.procyclingstats.com/v1/stages"

class ProCyclingAlertBot:
    def __init__(self):
        self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Configura los manejadores de comandos del bot"""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("latest", self.latest_winner_command))
        self.app.add_handler(CommandHandler("today", self.today_stages_command))
        self.app.add_handler(CommandHandler("subscribe", self.subscribe_command))
        self.app.add_handler(CommandHandler("unsubscribe", self.unsubscribe_command))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja el comando /start"""
        welcome_message = (
            "🚴‍♂️ ¡Bienvenido al Bot de Alertas de Ciclismo Profesional!\n\n"
            "Recibe notificaciones sobre los ganadores de etapas en las principales carreras.\n\n"
            "Comandos disponibles:\n"
            "/latest - Ver el último ganador de etapa\n"
            "/today - Ver las etapas de hoy\n"
            "/subscribe - Suscribirse a alertas automáticas\n"
            "/unsubscribe - Desuscribirse de alertas\n"
            "/help - Mostrar ayuda"
        )
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Maneja el comando /help"""
        help_text = (
            "📖 Ayuda del Bot de Ciclismo\n\n"
            "Este bot te mantiene informado sobre los resultados de etapas en ciclismo profesional.\n\n"
            "Comandos:\n"
            "• /start - Iniciar el bot\n"
            "• /latest - Último ganador de etapa\n"
            "• /today - Etapas programadas para hoy\n"
            "• /subscribe - Recibir alertas automáticas\n"
            "• /unsubscribe - Cancelar alertas\n"
            "• /help - Mostrar esta ayuda\n\n"
            "Desarrollado para fans del ciclismo profesional 🚴‍♂️"
        )
        await update.message.reply_text(help_text)
    
    async def latest_winner_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Obtiene y muestra el último ganador de etapa"""
        try:
            winner_data = self.get_latest_stage_winner()
            if winner_data:
                message = self.format_winner_message(winner_data)
                await update.message.reply_text(message, parse_mode='HTML')
            else:
                await update.message.reply_text(
                    "⚠️ No se encontraron resultados recientes. Intenta más tarde."
                )
        except Exception as e:
            logger.error(f"Error al obtener último ganador: {e}")
            await update.message.reply_text(
                "❌ Error al obtener la información. Por favor, intenta más tarde."
            )
    
    async def today_stages_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Muestra las etapas programadas para hoy"""
        try:
            stages = self.get_today_stages()
            if stages:
                message = "📅 <b>Etapas de hoy:</b>\n\n"
                for stage in stages:
                    message += f"🚴‍♂️ {stage['race']} - {stage['stage']}\n"
                    message += f"📍 {stage['route']}\n"
                    message += f"⏰ Hora: {stage['time']}\n\n"
                await update.message.reply_text(message, parse_mode='HTML')
            else:
                await update.message.reply_text(
                    "📭 No hay etapas programadas para hoy."
                )
        except Exception as e:
            logger.error(f"Error al obtener etapas de hoy: {e}")
            await update.message.reply_text(
                "❌ Error al obtener la información. Por favor, intenta más tarde."
            )
    
    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Suscribe al usuario a las alertas automáticas"""
        user_id = update.effective_user.id
        # Aquí deberías guardar el user_id en una base de datos
        await update.message.reply_text(
            "✅ ¡Te has suscrito a las alertas de ganadores de etapa!\n"
            "Recibirás notificaciones cuando se confirmen los resultados."
        )
    
    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Desuscribe al usuario de las alertas automáticas"""
        user_id = update.effective_user.id
        # Aquí deberías eliminar el user_id de la base de datos
        await update.message.reply_text(
            "❌ Te has desuscrito de las alertas.\n"
            "Puedes volver a suscribirte en cualquier momento con /subscribe"
        )
    
    def get_latest_stage_winner(self):
        """Obtiene el último ganador de etapa desde la fuente de datos"""
        # Implementación de ejemplo - adaptar según la fuente de datos real
        # Podrías usar web scraping con BeautifulSoup o una API específica
        
        # Datos de ejemplo
        return {
            'rider': 'Tadej Pogačar',
            'team': 'UAE Team Emirates',
            'race': 'Tour de France',
            'stage': 'Etapa 15',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'distance': '178 km',
            'time': '4h 23m 12s'
        }
    
    def get_today_stages(self):
        """Obtiene las etapas programadas para hoy"""
        # Implementación de ejemplo - adaptar según la fuente de datos real
        
        # Datos de ejemplo
        return [
            {
                'race': 'Vuelta a España',
                'stage': 'Etapa 10',
                'route': 'Madrid - Toledo',
                'time': '13:00 CEST'
            }
        ]
    
    def format_winner_message(self, data):
        """Formatea el mensaje del ganador de etapa"""
        message = (
            f"🏆 <b>¡Ganador de Etapa!</b>\n\n"
            f"🚴‍♂️ <b>Corredor:</b> {data['rider']}\n"
            f"🏁 <b>Equipo:</b> {data['team']}\n"
            f"📍 <b>Carrera:</b> {data['race']}\n"
            f"📊 <b>Etapa:</b> {data['stage']}\n"
            f"📅 <b>Fecha:</b> {data['date']}\n"
            f"📏 <b>Distancia:</b> {data['distance']}\n"
            f"⏱ <b>Tiempo:</b> {data['time']}"
        )
        return message
    
    def run(self):
        """Inicia el bot"""
        logger.info("Iniciando ProCycling Alert Bot...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Función principal"""
    bot = ProCyclingAlertBot()
    bot.run()

if __name__ == '__main__':
    main()
