#!/usr/bin/env python3
"""Script de prueba para verificar el scraping sin enviar a Telegram"""

import requests
from bs4 import BeautifulSoup

# URL de ProCyclingStats
PROCYCLING_URL = "https://www.procyclingstats.com"

# Headers para evitar bloqueos
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

print("🔍 Testeando scraping de ProCyclingStats...\n")

try:
    print(f"📡 Conectando a {PROCYCLING_URL}...")
    response = requests.get(PROCYCLING_URL, headers=HEADERS, timeout=10)
    print(f"✅ Status code: {response.status_code}")

    if response.status_code != 200:
        print(f"❌ Error: Código de respuesta {response.status_code}")
        exit(1)

    soup = BeautifulSoup(response.content, 'html.parser')

    # Buscar el encabezado 'Results today'
    results_header = soup.find('h3', string='Results today')

    if not results_header:
        print("❌ No se encontró el encabezado 'Results today'")
        print("Posibles encabezados encontrados:")
        for h3 in soup.find_all('h3')[:10]:
            print(f"  - {h3.get_text(strip=True)}")
        exit(1)

    print("✅ Encabezado 'Results today' encontrado\n")

    # Buscar enlaces de carreras
    current_element = results_header.find_next_sibling()
    races_found = 0

    print("🏁 Carreras encontradas:\n")

    while current_element and races_found < 5:
        if current_element.name == 'h3':
            break

        if current_element.name == 'ul':
            list_items = current_element.find_all('li')

            for item in list_items:
                all_links = item.find_all('a', href=True)

                if len(all_links) >= 1:
                    race_link = all_links[0]
                    race_name = race_link.get_text(strip=True)
                    race_url = race_link['href']

                    if not race_url.startswith('http'):
                        race_url = PROCYCLING_URL + race_url

                    races_found += 1
                    print(f"{races_found}. {race_name}")
                    print(f"   URL: {race_url}\n")

        current_element = current_element.find_next_sibling()

    if races_found == 0:
        print("❌ No se encontraron carreras en 'Results today'")
    else:
        print(f"\n✅ Total: {races_found} carrera(s) encontrada(s)")
        print("\n🎯 El scraping está funcionando correctamente!")

except requests.RequestException as e:
    print(f"❌ Error de conexión: {e}")
    exit(1)
except Exception as e:
    print(f"❌ Error inesperado: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
