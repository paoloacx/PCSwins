import os
import re
import requests
from bs4 import BeautifulSoup
import logging
import json
import hashlib
import time

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

# Headers para evitar bloqueos
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

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
                'text': cleaned_message,
                'parse_mode': 'Markdown'
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

    def scrape_race_podium(self, race_url):
        """Extrae el podio (top 3) y ubicación de una carrera específica"""
        try:
            logger.info(f"Scrapeando podio de: {race_url}")
            response = requests.get(race_url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            podium = []
            location = ""

            # Buscar la ubicación de la carrera
            # Intentar encontrar el elemento que contiene la ubicación
            location_elem = soup.find('span', class_='flag')
            if location_elem and location_elem.parent:
                location = location_elem.parent.get_text(strip=True)

            # Si no se encuentra, buscar en otros lugares comunes
            if not location:
                infolist = soup.find('ul', class_='infolist')
                if infolist:
                    for li in infolist.find_all('li'):
                        text = li.get_text(strip=True)
                        if '-' in text and 'km' in text.lower():
                            location = text
                            break

            # Buscar la tabla de resultados
            results_table = soup.find('table', class_='results')
            if not results_table:
                # Intentar otras variantes
                results_table = soup.find('tbody')

            if results_table:
                rows = results_table.find_all('tr')[:3]  # Top 3

                for idx, row in enumerate(rows, 1):
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        # Buscar el nombre del ciclista
                        rider_link = row.find('a', href=lambda x: x and '/rider/' in x)
                        rider_name = rider_link.get_text(strip=True) if rider_link else ""

                        # Buscar el tiempo (usualmente en la última columna)
                        time_col = cols[-1].get_text(strip=True)

                        if rider_name:
                            podium.append({
                                'position': idx,
                                'rider': rider_name,
                                'time': time_col if time_col else "-"
                            })
                            logger.info(f"Podio {idx}º: {rider_name} - {time_col}")

            return location, podium

        except Exception as e:
            logger.error(f"Error al scrapear podio de {race_url}: {e}")
            return "", []

    def scrape_today_winners(self):
        """Extrae las carreras del día con sus podios completos desde ProCyclingStats"""
        try:
            logger.info(f"Conectando a {PROCYCLING_URL}...")
            response = requests.get(PROCYCLING_URL, headers=HEADERS, timeout=10)
            logger.info(f"Status code: {response.status_code}")
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            today_races = []

            # Buscar el encabezado 'Results today'
            results_header = soup.find('h3', string='Results today')

            if not results_header:
                logger.warning("No se encontró el encabezado 'Results today'")
                # Mostrar algunos encabezados h3 encontrados para debugging
                all_h3 = soup.find_all('h3')
                if all_h3:
                    logger.info(f"Encabezados h3 encontrados: {[h.get_text(strip=True) for h in all_h3[:5]]}")
                return None, []

            logger.info("✅ Encabezado 'Results today' encontrado")

            # Buscar el elemento ul que sigue al encabezado
            current_element = results_header.find_next_sibling()

            # DEBUG: Mostrar qué elementos siguen al h3
            debug_element = results_header.find_next_sibling()
            elements_found = []
            for i in range(5):
                if debug_element:
                    elements_found.append(f"{debug_element.name}")
                    debug_element = debug_element.find_next_sibling()
            logger.info(f"Elementos después de h3: {elements_found}")

            # Extraer todas las carreras hasta encontrar el siguiente encabezado o fin de sección
            races_checked = 0
            while current_element:
                # Si encontramos otro encabezado h3, terminamos
                if current_element.name == 'h3':
                    logger.info(f"Encontrado siguiente h3, terminando. Carreras revisadas: {races_checked}")
                    break

                # Buscar enlaces dentro del elemento actual
                if current_element.name == 'ul':
                    list_items = current_element.find_all('li')
                    logger.info(f"Encontrado UL con {len(list_items)} items")

                    for item in list_items:
                        all_links = item.find_all('a', href=True)
                        # Mostrar TODOS los enlaces para debug
                        all_texts = [a.get_text(strip=True) for a in all_links]
                        logger.info(f"  LI tiene {len(all_links)} enlaces: {all_texts}")

                        # DEBUG: Mostrar todo el texto del LI para encontrar los tiempos
                        full_text = item.get_text(separator='|', strip=True)
                        logger.info(f"  Texto completo del LI: {full_text}")

                        races_checked += 1

                        # Extraer enlaces con texto (ignorar vacíos como iconos/banderas)
                        links_with_text = []
                        for link in all_links:
                            text = link.get_text(strip=True)
                            if text:
                                links_with_text.append({'text': text, 'href': link.get('href', '')})

                        # Necesitamos al menos 2 enlaces: carrera y ganador
                        if len(links_with_text) >= 2:
                            race_info = links_with_text[0]['text']  # Primer enlace = carrera + ubicación

                            # Intentar separar nombre de carrera y ubicación
                            # Buscar patrón donde termina con (CC), (WC), etc. seguido de ubicación
                            race_name = race_info
                            location = ""

                            # Buscar patrones comunes de fin de nombre de carrera
                            match = re.search(r'(\([A-Z]{2,3}\))([A-Z])', race_info)
                            if match:
                                split_pos = match.start(2)
                                race_name = race_info[:split_pos]
                                location = race_info[split_pos:]

                            # Extraer podio con tiempos del texto completo
                            # Formato: Carrera|Ubicación|1|Nombre1|Tiempo1|2|Nombre2|Tiempo2|3|Nombre3|Tiempo3|...
                            full_text = item.get_text(separator='|', strip=True)
                            parts = full_text.split('|')

                            podium = []
                            # Buscar patrón: número de posición seguido de nombre y tiempo
                            i = 0
                            while i < len(parts):
                                if parts[i] in ['1', '2', '3']:
                                    pos = parts[i]
                                    if i + 1 < len(parts):
                                        rider = parts[i + 1]
                                        time = parts[i + 2] if i + 2 < len(parts) else ""
                                        # Ignorar si es "view results" o similar
                                        if rider.lower() not in ['view  results', 'view results', '']:
                                            podium.append({
                                                'pos': pos,
                                                'rider': rider,
                                                'time': time if time and time != ',,' else ''
                                            })
                                        i += 3
                                        continue
                                i += 1

                            logger.info(f"  -> Carrera: {race_name}, Podio: {podium}")

                            # Generar hash único para esta combinación
                            first_rider = podium[0]['rider'] if podium else ""
                            result_hash = self.generate_result_hash(race_name, first_rider)

                            # Solo agregar si no se ha enviado antes
                            if result_hash not in self.sent_results:
                                today_races.append({
                                    'race': race_name,
                                    'location': location,
                                    'podium': podium,
                                    'hash': result_hash
                                })
                                logger.info(f"✅ Carrera agregada: {race_name} - Podio: {podium}")
                            else:
                                logger.info(f"Carrera ya enviada (omitida): {race_name}")

                current_element = current_element.find_next_sibling()

            # Solo retornar mensaje si hay carreras nuevas
            if today_races:
                result = "· ProCycling Alert Bot ·\n\n"

                for race in today_races:
                    # Nombre de la carrera en BOLD
                    result += f"*{race['race']}*\n"

                    # Ubicación si existe
                    if race.get('location'):
                        result += f"📍 {race['location']}\n"

                    result += "\n"

                    # Podio con tiempos
                    if race.get('podium'):
                        for rider_info in race['podium'][:3]:
                            pos = rider_info.get('pos', '?')
                            rider = rider_info.get('rider', '')
                            time = rider_info.get('time', '')
                            if time:
                                result += f"{pos}º - {rider}  {time}\n"
                            else:
                                result += f"{pos}º - {rider}\n"

                    result += "\n"

                return result, today_races
            else:
                # Si no hay carreras nuevas, retornar None
                logger.info("No hay carreras nuevas para enviar")
                return None, []

        except requests.RequestException as e:
            logger.error(f"Error al obtener datos de ProCyclingStats: {e}")
            return None, []
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return None, []
    
    def run(self):
        """Ejecuta el bot y envía resultados por Telegram solo si hay carreras nuevas"""
        logger.info("Bot ejecutándose - buscando carreras del día")

        # Obtener carreras de hoy con sus podios
        races_info, races_list = self.scrape_today_winners()

        # Solo enviar mensaje si hay carreras nuevas
        if races_info and races_list:
            # Mostrar en logs
            logger.info(f"Encontradas {len(races_list)} carrera(s) nueva(s)")
            logger.info(races_info)

            # Enviar por Telegram
            if self.send_telegram(races_info):
                # Marcar resultados como enviados
                for race in races_list:
                    self.sent_results.add(race['hash'])

                # Guardar el caché actualizado
                self.save_sent_results()
                logger.info(f"{len(races_list)} nueva(s) carrera(s) enviada(s) y guardada(s) en caché")
        else:
            logger.info("No se envió mensaje porque no hay carreras nuevas")

if __name__ == '__main__':
    bot = ProCyclingAlertBot()
    bot.run()
