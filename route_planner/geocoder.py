# route_planner/geocoder.py

import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from functools import lru_cache

class GeoCoder:
    """
    Classe para geocodificar endereços utilizando o Nominatim.
    """

    @staticmethod
    @lru_cache(maxsize=1000)
    def geocode_address(address):
        """
        Geocodifica um endereço e retorna suas coordenadas geográficas.

        Args:
            address (str): Endereço a ser geocodificado.

        Returns:
            tuple or list: Se apenas um endereço for encontrado, retorna uma tupla com
            (latitude, longitude, endereço completo). Se múltiplos endereços forem encontrados,
            retorna uma lista de tais tuplas.
        """
        # Utilizar um user_agent único e informativo
        geolocator = Nominatim(user_agent="sua_aplicacao/1.0 (seu_email@example.com)")

        # Respeitar o limite de 1 requisição por segundo
        time.sleep(1)

        try:
            # Reduzir o limite de resultados para minimizar a carga no servidor
            locations = geolocator.geocode(
                address,
                exactly_one=False,
                limit=5,
                country_codes='br',
                timeout=10  # Aumentar o tempo limite para 10 segundos
            )

            if not locations:
                print("Endereço não encontrado. Tente novamente.")
                return None
            elif len(locations) == 1:
                location = locations[0]
                return (location.latitude, location.longitude, location.address)
            else:
                # Retornar todos os resultados encontrados
                return [(loc.latitude, loc.longitude, loc.address) for loc in locations]

        except GeocoderTimedOut:
            print("O serviço de geocodificação demorou muito para responder. Por favor, tente novamente mais tarde.")
            return None
        except GeocoderServiceError as e:
            print(f"Erro no serviço de geocodificação: {e}")
            return None
        except Exception as e:
            print(f"Erro ao geocodificar o endereço: {e}")
            return None
