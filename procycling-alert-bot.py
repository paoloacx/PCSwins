import os
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime

# Configuración del logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# URL de ProCyclingStats
PROCYCLING_URL = "https://www.procyclingstats.com/calendar/uci/latest-results"

# Configuración de Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

class ProCyclingAlertBot:
    
    def __init__(self):
        logger.info("ProCyclingAlertBot initialized")
    
    def clean_message(self, message):
        """Limpia el mensaje eliminando los símbolos < y >"""
        return message.replace('<', '').replace('>', '')
    
    def send_telegram(self, message):
        """Envía un mensaje a Telegram usando requests"""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.error("Telegram token o chat ID no configurados")
            return False
        
        try:
            # Limpiar el mensaje antes de enviarlo
            cleaned_message = self.clean_message(message)
            
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': cleaned_message,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, json=payload)
            print(response.text)
            response.raise_for_status()
            logger.info("Mensaje enviado a Telegram exitosamente")
            return True
        except requests.RequestException as e:
            logger.error(f"Error al enviar mensaje a Telegram: {e}")
            return False
    
    def scrape_today_winners(self):
        """Scrapea los ganadores de hoy desde ProCyclingStats"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(PROCYCLING_URL, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            today = datetime.now().date()
            today_winners = []
            
            # Buscar las filas de resultados
            rows = soup.find_all('tr')
            
            for row in rows:
                # Buscar fecha en la fila
                date_cell = row.find('td', class_='date')
                if date_cell:
                    try:
                        date_text = date_cell.get_text(strip=True)
                        # Parsear la fecha (formato puede variar)
                        row_date = datetime.strptime(date_text, '%d.%m.%Y').date()
                        
                        if row_date == today:
                            # Extraer nombre de la carrera
                            race_cell = row.find('td', class_='name')
                            race_name = race_cell.get_text(strip=True) if race_cell else 'Desconocida'
                            
                            # Extraer nombre del ganador
                            winner_cell = row.find('td', class_='rider')
                            if not winner_cell:
                                winner_cell = row.find('a', href=lambda x: x and '/rider/' in x)
                            winner_name = winner_cell.get_text(strip=True) if winner_cell else 'Desconocido'
                            
                            today_winners.append({
                                'race': race_name,
                                'winner': winner_name
                            })
                    except (ValueError, AttributeError) as e:
                        logger.debug(f"Error procesando fila: {e}")
                        continue
            
            if today_winners:
                result = "🏆 Ganadores de hoy:\n\n"
                for winner in today_winners:
                    result += f"🚴 {winner['winner']}\n"
                    result += f"📍 {winner['race']}\n\n"
                return result
            else:
                return "No hay ganadores registrados para hoy"
        
        except requests.RequestException as e:
            logger.error(f"Error al obtener datos de ProCyclingStats: {e}")
            return f"Error al obtener datos: {e}"
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return f"Error inesperado: {e}"
    
    def run(self):
        """Ejecuta el bot y envía resultados por Telegram"""
        logger.info("Bot ejecutándose con BeautifulSoup y requests")
        
        # Obtener ganadores de hoy
        winners_info = self.scrape_today_winners()
        
        # Construir mensaje completo
        message = f"🚴 ProCycling Alert Bot\n\n{winners_info}"
        
        # Mostrar en logs
        logger.info(winners_info)
        
        # Enviar por Telegram
        self.send_telegram(message)

if __name__ == '__main__':
    bot = ProCyclingAlertBot()
    bot.run()
