# route_planner/geocoder.py

from geopy.geocoders import Nominatim

class GeoCoder:
    @staticmethod
    def geocode_address(address):
        geolocator = Nominatim(user_agent="shortest_path_tester")
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
