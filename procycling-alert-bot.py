import os
import requests
import json
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

# Archivo para guardar los ganadores ya notificados
SENT_WINNERS_FILE = 'sent_winners.json'

class ProCyclingAlertBot:
    
    def __init__(self):
        logger.info("ProCyclingAlertBot initialized")
        self.sent_winners = self.load_sent_winners()
        
    def load_sent_winners(self):
        """Carga los ganadores ya notificados desde el archivo"""
        try:
            if os.path.exists(SENT_WINNERS_FILE):
                with open(SENT_WINNERS_FILE, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error al cargar ganadores notificados: {e}")
            return {}

    def save_sent_winners(self):
        """Guarda los ganadores notificados en el archivo"""
        try:
            with open(SENT_WINNERS_FILE, 'w') as f:
                json.dump(self.sent_winners, f)
        except Exception as e:
            logger.error(f"Error al guardar ganadores notificados: {e}")

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
            logger.error(f"Error al enviar mensaje a Telegram: {e}")
            return False

    def scrape_today_winners(self):
        """Extrae los ganadores y el podio del día desde ProCyclingStats"""
        try:
            response = requests.get(PROCYCLING_URL, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            today_winners = []
            
            # Buscar el encabezado 'Results today'
            results_header = soup.find('h3', string='Results today')
            
            if not results_header:
                logger.info("No se encontró el encabezado 'Results today'")
                return None
            
            logger.info("Encabezado 'Results today' encontrado")
            
            # Buscar el elemento ul que sigue al encabezado
            current_element = results_header.find_next_sibling()
            
            # Extraer todos los ganadores y podios
            while current_element:
                # Si encontramos otro encabezado h3, terminamos
                if current_element.name == 'h3':
                    break
                
                # Buscar enlaces dentro del elemento actual
                if current_element.name == 'ul':
                    list_items = current_element.find_all('li')
                    
                    for item in list_items:
                        # Buscar todos los enlaces en el item (ganador, 2º, 3º, carrera)
                        links = item.find_all('a', href=True)
                        if len(links) >= 3:  # Al menos ganador, 2º, 3º
                            winner_name = links[0].get_text(strip=True)
                            second_name = links[1].get_text(strip=True)
                            third_name = links[2].get_text(strip=True)
                            race_name = links[-1].get_text(strip=True) if len(links) > 3 else 'Desconocida'
                            
                            today_winners.append({
                                'race': race_name,
                                'winner': winner_name,
                                'second': second_name,
                                'third': third_name
                            })
                            logger.info(f"Podio encontrado: {winner_name}, {second_name}, {third_name} - {race_name}")
                
                current_element = current_element.find_next_sibling()
            
            # Solo retornar mensaje si hay ganadores
            if today_winners:
                return today_winners
            else:
                logger.info("No hay ganadores registrados para hoy")
                return None
            
        except requests.RequestException as e:
            logger.error(f"Error al obtener datos de ProCyclingStats: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return None

    def run(self):
        """Ejecuta el bot y envía resultados por Telegram solo si hay nuevos ganadores"""
        logger.info("Bot ejecutándose con BeautifulSoup y requests")
        
        # Obtener ganadores de hoy
        winners_info = self.scrape_today_winners()
        
        # Solo enviar mensaje si hay ganadores y no han sido notificados
        if winners_info:
            new_winners = []
            for winner in winners_info:
                winner_key = f"{winner['race']}-{winner['winner']}"
                if winner_key not in self.sent_winners:
                    new_winners.append(winner)
                    self.sent_winners[winner_key] = True
            
            if new_winners:
                # Construir mensaje completo
                message = "🚴 ProCycling Alert Bot\n\n"
                for winner in new_winners:
                    message += f"🏆 {winner['race']}\n"
                    message += f"🥇 {winner['winner']}\n"
                    message += f"🥈 {winner['second']}\n"
                    message += f"🥉 {winner['third']}\n\n"
                
                # Mostrar en logs
                logger.info(message)
                
                # Enviar por Telegram
                self.send_telegram(message)
                
                # Guardar los ganadores notificados
                self.save_sent_winners()
            else:
                logger.info("No hay nuevos ganadores para notificar")
        else:
            logger.info("No se envió mensaje porque no hay ganadores nuevos")

if __name__ == '__main__':
    bot = ProCyclingAlertBot()
    bot.run()