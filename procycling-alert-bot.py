import os
import requests
from bs4 import BeautifulSoup
import logging
import json
import hashlib

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

# Archivo para evitar duplicados
CACHE_FILE = '/tmp/procycling_sent_results.json'

class ProCyclingAlertBot:

    def __init__(self):
        logger.info("ProCyclingAlertBot initialized")
        self.sent_results = self.load_sent_results()

    def load_sent_results(self):
        """Carga los resultados ya enviados desde el archivo de caché"""
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r') as f:
                    return set(json.load(f))
            return set()
        except Exception as e:
            logger.warning(f"No se pudo cargar el caché: {e}")
            return set()

    def save_sent_results(self):
        """Guarda los resultados enviados en el archivo de caché"""
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(list(self.sent_results), f)
        except Exception as e:
            logger.error(f"No se pudo guardar el caché: {e}")

    def generate_result_hash(self, race, winner):
        """Genera un hash único para un resultado de carrera"""
        result_str = f"{race}:{winner}"
        return hashlib.md5(result_str.encode()).hexdigest()

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
                'text': cleaned_message
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
        """Extrae los ganadores del día desde ProCyclingStats con lógica robusta"""
        try:
            response = requests.get(PROCYCLING_URL, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            today_winners = []
            
            # Buscar el encabezado 'Results today'
            results_header = soup.find('h3', string='Results today')
            
            if not results_header:
                logger.info("No se encontró el encabezado 'Results today'")
                return None, []
            
            logger.info("Encabezado 'Results today' encontrado")
            
            # Buscar el elemento ul que sigue al encabezado
            current_element = results_header.find_next_sibling()
            
            # Extraer todos los ganadores hasta encontrar el siguiente encabezado o fin de sección
            while current_element:
                # Si encontramos otro encabezado h3, terminamos
                if current_element.name == 'h3':
                    break
                
                # Buscar enlaces dentro del elemento actual
                if current_element.name == 'ul':
                    list_items = current_element.find_all('li')

                    for item in list_items:
                        all_links = item.find_all('a', href=True)

                        # Necesitamos al menos 2 enlaces: carrera y ganador
                        if len(all_links) >= 2:
                            # El PRIMER enlace es la CARRERA
                            race_link = all_links[0]
                            # El SEGUNDO enlace es el GANADOR
                            winner_link = all_links[1]

                            race_name = race_link.get_text(strip=True)
                            winner_name = winner_link.get_text(strip=True)

                            # Solo agregar si ambos tienen contenido
                            if race_name and winner_name:
                                result_hash = self.generate_result_hash(race_name, winner_name)

                                # Solo agregar si no se ha enviado antes
                                if result_hash not in self.sent_results:
                                    today_winners.append({
                                        'race': race_name,
                                        'winner': winner_name,
                                        'hash': result_hash
                                    })
                                    logger.info(f"Ganador encontrado: {winner_name} - {race_name}")
                                else:
                                    logger.info(f"Resultado ya enviado (omitido): {winner_name} - {race_name}")
                
                current_element = current_element.find_next_sibling()
            
            # Solo retornar mensaje si hay ganadores nuevos
            if today_winners:
                result = "🏆 Resultados de hoy:\n\n"
                for winner in today_winners:
                    result += f"🚴 {winner['winner']}\n"
                    result += f"   {winner['race']}\n\n"
                return result, today_winners
            else:
                # Si no hay ganadores nuevos, retornar None
                logger.info("No hay ganadores nuevos para enviar")
                return None, []
        
        except requests.RequestException as e:
            logger.error(f"Error al obtener datos de ProCyclingStats: {e}")
            return None, []
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return None, []
    
    def run(self):
        """Ejecuta el bot y envía resultados por Telegram solo si hay ganadores nuevos"""
        logger.info("Bot ejecutándose con BeautifulSoup y requests")

        # Obtener ganadores de hoy
        winners_info, winners_list = self.scrape_today_winners()

        # Solo enviar mensaje si hay ganadores nuevos
        if winners_info and winners_list:
            # Mostrar en logs
            logger.info(winners_info)

            # Enviar por Telegram
            if self.send_telegram(winners_info):
                # Marcar resultados como enviados
                for winner in winners_list:
                    self.sent_results.add(winner['hash'])

                # Guardar el caché actualizado
                self.save_sent_results()
                logger.info(f"{len(winners_list)} nuevo(s) resultado(s) enviado(s) y guardado(s) en caché")
        else:
            logger.info("No se envió mensaje porque no hay ganadores nuevos")

if __name__ == '__main__':
    bot = ProCyclingAlertBot()
    bot.run()
