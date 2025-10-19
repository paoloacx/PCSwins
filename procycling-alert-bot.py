import os
import requests
import logging
from datetime import datetime

# Configuración del logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# URL de la API de ProCyclingStats o fuente de datos
PROCYCLING_API_URL = "https://api.procyclingstats.com/v1/stages"

# Configuración de Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

class ProCyclingAlertBot:
    
    def __init__(self):
        logger.info("ProCyclingAlertBot initialized")
    
    def send_telegram(self, message):
        """Envía un mensaje a Telegram usando requests"""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.error("Telegram token o chat ID no configurados")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=payload)
            response.raise_for_status()
            logger.info("Mensaje enviado a Telegram exitosamente")
            return True
        except requests.RequestException as e:
            logger.error(f"Error al enviar mensaje a Telegram: {e}")
            return False
    
    def get_latest_winner(self):
        """Obtiene el último ganador de ProCyclingStats"""
        try:
            response = requests.get(PROCYCLING_API_URL)
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) > 0:
                latest_stage = data[0]
                winner = latest_stage.get('winner', 'Desconocido')
                stage_name = latest_stage.get('name', 'Etapa desconocida')
                return f"Último ganador: {winner} en {stage_name}"
            else:
                return "No hay datos disponibles"
        except requests.RequestException as e:
            logger.error(f"Error al obtener datos: {e}")
            return f"Error al obtener datos: {e}"
    
    def get_today_stages(self):
        """Obtiene las etapas de hoy"""
        try:
            response = requests.get(PROCYCLING_API_URL)
            response.raise_for_status()
            data = response.json()
            
            today = datetime.now().date()
            today_stages = []
            
            for stage in data:
                stage_date = datetime.strptime(stage.get('date', ''), '%Y-%m-%d').date()
                if stage_date == today:
                    today_stages.append(stage)
            
            if today_stages:
                result = "Etapas de hoy:\n"
                for stage in today_stages:
                    result += f"- {stage.get('name', 'Desconocido')}\n"
                return result
            else:
                return "No hay etapas programadas para hoy"
        except requests.RequestException as e:
            logger.error(f"Error al obtener etapas: {e}")
            return f"Error al obtener etapas: {e}"
    
    def run(self):
        """Ejecuta el bot con requests y envía resultados por Telegram"""
        logger.info("Bot ejecutándose con requests")
        
        # Obtener información
        winner_info = self.get_latest_winner()
        stages_info = self.get_today_stages()
        
        # Construir mensaje completo
        message = f"<b>🚴 ProCycling Alert Bot</b>\n\n"
        message += f"<b>Último ganador:</b>\n{winner_info}\n\n"
        message += f"<b>Etapas de hoy:</b>\n{stages_info}"
        
        # Mostrar en logs
        logger.info(winner_info)
        logger.info(stages_info)
        
        # Enviar siempre por Telegram, tanto si hay ganadores como si no
        self.send_telegram(message)

if __name__ == '__main__':
    bot = ProCyclingAlertBot()
    bot.run()
