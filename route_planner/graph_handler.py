# route_planner/graph_handler.py

import sys
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point
from pyproj import Transformer
import networkx as nx  # Importar o NetworkX
from .logger import logger

class GraphHandler:
    """
    Classe para criar e manipular o grafo rodoviário a partir de um ponto de origem
    e um raio de busca especificado.
    """
    def __init__(self, origin_point, radius):
        self.origin_point = origin_point  # (latitude, longitude)
        self.radius = radius
        self.G = None
        self.G_projected = None
        self.transformer = None
        self.origin_node = None
        self.origin_address = None
        self.graph_density = None  # Novo atributo para armazenar a densidade

    def create_graph(self):
        """
        Cria o grafo rodoviário a partir do OpenStreetMap usando o OSMnx.
        O grafo é projetado para um sistema de coordenadas adequado para cálculos de distância.
        """
        logger.info("Baixando dados de ruas do OSM...")
        try:
            self.G = ox.graph_from_point(
                self.origin_point,
                dist=self.radius,
                network_type='drive',
                simplify=False  # Desativar simplificação para maior densidade
            )
            # Reprojetar o grafo para um CRS projetado (por exemplo, UTM)
            self.G_projected = ox.project_graph(self.G)
            logger.info("Grafo de ruas carregado e reprojetado.")
        except Exception as e:
            logger.error(f"Erro ao baixar ou processar o grafo: {e}")
            raise Exception(f"Erro ao baixar ou processar o grafo: {e}")

        # Obter o CRS do grafo projetado
        crs_projected = self.G_projected.graph.get('crs', None)
        if crs_projected is None:
            logger.error("CRS não encontrado no grafo projetado.")
            raise Exception("CRS não encontrado no grafo projetado.")

        # Definir o transformador para converter coordenadas
        self.transformer = Transformer.from_crs(crs_projected, "epsg:4326", always_xy=True)
        logger.info(f"Transformer definido: {self.transformer}")

        # Verificar se o grafo é direcionado
        if not self.G_projected.is_directed():
            logger.error("O grafo não é direcionado.")
            raise ValueError("O grafo não é direcionado. Verifique o 'network_type' utilizado.")

        # Calcular a densidade do grafo
        self.calculate_density()

    def calculate_density(self):
        """
        Calcula a densidade do grafo e armazena no atributo 'graph_density'.
        """
        try:
            self.graph_density = nx.density(self.G_projected)
            logger.info(f"Densidade do grafo calculada: {self.graph_density:.6f}")
        except Exception as e:
            logger.error(f"Erro ao calcular a densidade do grafo: {e}")
            self.graph_density = None

    def find_origin_node(self):
        """
        Encontra o nó mais próximo do ponto de origem no grafo projetado.
        """
        crs_projected = self.G_projected.graph['crs']
        # Converter as coordenadas da origem para o CRS projetado
        origin_gdf = gpd.GeoDataFrame(
            {'geometry': [Point(self.origin_point[1], self.origin_point[0])]},  # (lon, lat)
            crs='epsg:4326'  # CRS geográfico
        )
        origin_projected = origin_gdf.to_crs(crs_projected)
        origin_x_proj, origin_y_proj = origin_projected.geometry.x[0], origin_projected.geometry.y[0]

        # Encontrar nó de origem no grafo projetado
        try:
            self.origin_node = ox.distance.nearest_nodes(self.G_projected, X=origin_x_proj, Y=origin_y_proj)
            origin_node_coords = (self.G_projected.nodes[self.origin_node]['y'], self.G_projected.nodes[self.origin_node]['x'])
            logger.info(f"Nó de Origem: {self.origin_node}")
            logger.info(f"Coordenadas do Nó de Origem: {origin_node_coords}")
        except Exception as e:
            logger.error(f"Erro ao encontrar o nó de origem: {e}")
            raise Exception(f"Erro ao encontrar o nó de origem: {e}")

    def print_graph_info(self):
        """
        Imprime informações sobre o grafo, como o número de nós, arestas e densidade.
        """
        num_nodes = self.G_projected.number_of_nodes()
        num_edges = self.G_projected.number_of_edges()
        logger.info(f"O grafo possui {num_nodes} nós e {num_edges} arestas.")
        if self.graph_density is not None:
            logger.info(f"Densidade do grafo: {self.graph_density:.6f}")
