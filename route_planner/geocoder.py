# route_planner/geocoder.py

from geopy.geocoders import Nominatim

class GeoCoder:
    """
    Classe para geocodificar endereços utilizando o Nominatim.
    """
    @staticmethod
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
        geolocator = Nominatim(user_agent="route_planner")
        try:
            locations = geolocator.geocode(address, exactly_one=False, limit=50, country_codes='br')
            if not locations:
                print("Endereço não encontrado. Tente novamente.")
                return None
            elif len(locations) == 1:
                location = locations[0]
                return (location.latitude, location.longitude, location.address)
            else:
                # Retornar todos os resultados encontrados
                return [(loc.latitude, loc.longitude, loc.address) for loc in locations]
        except Exception as e:
            print(f"Erro ao geocodificar o endereço: {e}")
            return None
