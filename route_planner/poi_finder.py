# route_planner/poi_finder.py

import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point

# Importar o logger
from route_planner.logger import logger

class POIFinder:
    """
    Classe para encontrar pontos de interesse (POIs), como estabelecimentos comerciais,
    dentro de um raio especificado a partir de um ponto de origem.
    """
    def __init__(self, G_projected, origin_point_geo, radius):
        self.G_projected = G_projected
        self.origin_point_geo = origin_point_geo  # (latitude, longitude)
        self.radius = radius
        self.cuisine = None  # Será definido após a seleção pelo usuário
        self.destination_nodes = []
        self.destination_coords_geo = []
        self.destination_names = []
        self.available_cuisines = set()  # Armazena os tipos de estabelecimentos disponíveis

    def get_available_cuisines(self):
        """
        Obtém todos os tipos de estabelecimentos ('cuisine') disponíveis na área especificada.
        """
        # Buscar todos os restaurantes na área
        tags = {'amenity': 'restaurant'}
        try:
            pois = ox.features_from_point(self.origin_point_geo, tags=tags, dist=self.radius)
        except Exception as e:
            print(f"Erro ao obter POIs: {e}")
            logger.error(f"Erro ao obter POIs: {e}")
            return

        if pois.empty:
            print("Nenhum estabelecimento encontrado na área.")
            logger.info("Nenhum estabelecimento encontrado na área.")
            return

        # Obter todas as tags 'cuisine' disponíveis
        if 'cuisine' in pois.columns:
            cuisines = pois['cuisine'].dropna().unique()
            # Algumas entradas podem ter múltiplas cozinhas separadas por ';'
            cuisines_split = [c.strip() for sublist in cuisines for c in sublist.split(';')]
            self.available_cuisines = set(cuisines_split)
        else:
            self.available_cuisines = set()

        # Se não houver 'cuisine', tentar usar 'name' como alternativa
        if not self.available_cuisines:
            print("A coluna 'cuisine' não está presente nos dados ou está vazia.")
            if 'name' in pois.columns:
                names = pois['name'].dropna().unique()
                self.available_cuisines = set(names)
            else:
                print("A coluna 'name' também não está presente.")
                self.available_cuisines = set()

    def get_pois(self):
        """
        Filtra os POIs de acordo com o tipo de estabelecimento selecionado pelo usuário.
        """
        if not self.cuisine:
            print("Nenhuma 'cuisine' foi selecionada.")
            return

        tags = {'amenity': 'restaurant'}
        try:
            pois = ox.features_from_point(self.origin_point_geo, tags=tags, dist=self.radius)
        except Exception as e:
            print(f"Erro ao obter POIs: {e}")
            return

        if pois.empty:
            print("Nenhum estabelecimento encontrado na área.")
            return

        # Filtrar por 'cuisine' selecionada
        if 'cuisine' in pois.columns:
            pois = pois[pois['cuisine'].str.contains(self.cuisine, case=False, na=False)]
            print(f"{len(pois)} estabelecimentos correspondem à busca por '{self.cuisine}'.")
        else:
            pois = pois[pois['name'].str.contains(self.cuisine, case=False, na=False)]
            print(f"{len(pois)} estabelecimentos correspondem à busca por nome contendo '{self.cuisine}'.")

        if pois.empty:
            print("Nenhum estabelecimento correspondente encontrado após filtragem.")
            return

        # Reprojetar para o CRS do grafo projetado
        pois_projected = pois.to_crs(self.G_projected.graph['crs'])

        # Calcular os centróides
        pois_centroids_projected = pois_projected.geometry.centroid

        # Obter coordenadas projetadas
        pois_coords_proj = [(point.x, point.y) for point in pois_centroids_projected]

        # Encontrar os nós mais próximos
        self.destination_nodes = ox.distance.nearest_nodes(
            self.G_projected,
            X=[coord[0] for coord in pois_coords_proj],
            Y=[coord[1] for coord in pois_coords_proj]
        )

        # Obter nomes dos estabelecimentos
        self.destination_names = pois['name'].tolist()

        # Converter para coordenadas geográficas para plotagem
        pois_centroids_geo = pois_centroids_projected.to_crs(epsg=4326)
        self.destination_coords_geo = [(point.y, point.x) for point in pois_centroids_geo]
