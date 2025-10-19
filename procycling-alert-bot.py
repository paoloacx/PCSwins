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
PROCYCLING_URL = "https://www.procyclingstats.com"

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
            cleaned_message = self.clean_message(message)
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': cleaned_message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("Mensaje enviado exitosamente a Telegram")
                return True
            else:
                logger.error(f"Error al enviar mensaje: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error enviando mensaje a Telegram: {e}")
            return False
    
    def scrape_today_winners(self):
        """Extrae los ganadores del día desde la home de ProCyclingStats"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(PROCYCLING_URL, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            today_winners = []
            
            # Buscar el bloque con el texto "Results today"
            results_today_header = None
            for header in soup.find_all(['h3', 'h2', 'h4']):
                if 'Results today' in header.get_text():
                    results_today_header = header
                    break
            
            if not results_today_header:
                logger.warning("No se encontró el bloque 'Results today'")
                return None
            
            logger.info("Bloque 'Results today' encontrado")
            
            # Recorrer los elementos hijos hasta encontrar el siguiente encabezado
            current_element = results_today_header.find_next_sibling()
            
            while current_element:
                # Si encontramos otro encabezado, terminamos
                if current_element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    break
                
                # Buscar elementos li o div que contengan información de ganadores
                items = []
                if current_element.name == 'ul':
                    items = current_element.find_all('li')
                elif current_element.name == 'div':
                    items = current_element.find_all(['li', 'div'], recursive=True)
                else:
                    items = [current_element] if current_element.name in ['li', 'div'] else []
                
                for item in items:
                    # Buscar enlaces de ciclistas (ganadores)
                    winner_link = item.find('a', href=lambda x: x and '/rider/' in x)
                    race_link = item.find('a', href=lambda x: x and '/race/' in x)
                    
                    if winner_link:
                        winner_name = winner_link.get_text(strip=True)
                        race_name = race_link.get_text(strip=True) if race_link else 'Desconocida'
                        
                        today_winners.append({
                            'race': race_name,
                            'winner': winner_name
                        })
                        logger.info(f"Ganador encontrado: {winner_name} - {race_name}")
                
                current_element = current_element.find_next_sibling()
            
            # Solo retornar mensaje si hay ganadores
            if today_winners:
                result = "🏆 Ganadores de hoy:\n\n"
                for winner in today_winners:
                    result += f"🚴 {winner['winner']}\n"
                    result += f"📍 {winner['race']}\n\n"
                return result
            else:
                # Si no hay ganadores, retornar None para no enviar mensaje
                logger.info("No hay ganadores registrados para hoy")
                return None
        
        except requests.RequestException as e:
            logger.error(f"Error al obtener datos de ProCyclingStats: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return None
    
    def run(self):
        """Ejecuta el bot y envía resultados por Telegram solo si hay ganadores"""
        logger.info("Bot ejecutándose con BeautifulSoup y requests")
        
        # Obtener ganadores de hoy
        winners_info = self.scrape_today_winners()
        
        # Solo enviar mensaje si hay ganadores
        if winners_info:
            # Construir mensaje completo
            message = f"🚴 ProCycling Alert Bot\n\n{winners_info}"
            
            # Mostrar en logs
            logger.info(winners_info)
            
            # Enviar por Telegram
            self.send_telegram(message)
        else:
            logger.info("No se envió mensaje porque no hay ganadores nuevos")

if __name__ == '__main__':
    bot = ProCyclingAlertBot()
    bot.run()
