# route_planner/poi_finder.py

import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point

# Importar o logger
from route_planner.logger import logger
from collections import Counter

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
        self.cuisine_counts = {}  # Dicionário para armazenar tipos de estabelecimentos e suas quantidades

    def get_available_cuisines(self):
        """
        Obtém todos os tipos de estabelecimentos ('cuisine') disponíveis na área especificada,
        juntamente com a contagem de estabelecimentos para cada tipo.
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

        # Obter todas as tags 'cuisine' disponíveis e contar os estabelecimentos
        self.cuisine_counts = {}
        if 'cuisine' in pois.columns:
            # Expandir as entradas com múltiplas cozinhas separadas por ';'
            pois['cuisine_list'] = pois['cuisine'].str.split(';')
            pois['cuisine_list'] = pois['cuisine_list'].apply(lambda x: [c.strip() for c in x] if isinstance(x, list) else [])

            # Contar as ocorrências de cada 'cuisine'
            cuisine_list = [cuisine for sublist in pois['cuisine_list'] for cuisine in sublist]
            self.cuisine_counts = Counter(cuisine_list)
        else:
            # Se não houver 'cuisine', tentar usar 'name' como alternativa
            if 'name' in pois.columns:
                names = pois['name'].dropna().unique()
                self.cuisine_counts = {name: 1 for name in names}
            else:
                print("As colunas 'cuisine' e 'name' não estão presentes nos dados.")
                self.cuisine_counts = {}

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
            # Expandir as entradas com múltiplas cozinhas separadas por ';'
            pois['cuisine_list'] = pois['cuisine'].str.split(';')
            pois['cuisine_list'] = pois['cuisine_list'].apply(lambda x: [c.strip() for c in x] if isinstance(x, list) else [])

            # Filtrar os POIs que contêm a 'cuisine' selecionada
            pois_filtered = pois[pois['cuisine_list'].apply(lambda x: self.cuisine in x)]
            print(f"{len(pois_filtered)} estabelecimentos correspondem à busca por '{self.cuisine}'.")
        else:
            # Se não houver 'cuisine', usar 'name' como alternativa
            pois_filtered = pois[pois['name'].str.contains(self.cuisine, case=False, na=False)]
            print(f"{len(pois_filtered)} estabelecimentos correspondem à busca por nome contendo '{self.cuisine}'.")

        if pois_filtered.empty:
            print("Nenhum estabelecimento correspondente encontrado após filtragem.")
            return

        # Reprojetar para o CRS do grafo projetado
        pois_projected = pois_filtered.to_crs(self.G_projected.graph['crs'])

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
        self.destination_names = pois_projected['name'].tolist()

        # Converter para coordenadas geográficas para plotagem
        pois_centroids_geo = pois_centroids_projected.to_crs(epsg=4326)
        self.destination_coords_geo = [(point.y, point.x) for point in pois_centroids_geo]
