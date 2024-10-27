# route_planner/graph_handler.py

import sys
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point
from pyproj import Transformer

class GraphHandler:
    def __init__(self, origin_point, radius):
        self.origin_point = origin_point
        self.radius = radius
        self.G = None
        self.G_projected = None
        self.transformer = None
        self.origin_node = None
        self.origin_address = None

    def create_graph(self):
        print("Baixando dados de ruas do OSM...")
        try:
            self.G = ox.graph_from_point(
                self.origin_point,
                dist=self.radius,
                network_type='drive',
                simplify=False  # Desativar simplificação para maior densidade
            )
            # Reprojetar o grafo para um CRS projetado (por exemplo, UTM)
            self.G_projected = ox.project_graph(self.G)
            print("Grafo de ruas carregado e reprojetado.")
        except Exception as e:
            print(f"Erro ao baixar ou processar o grafo: {e}")
            sys.exit()

        # Verificar se o grafo é direcionado
        if not self.G_projected.is_directed():
            print("O grafo não é direcionado. Certifique-se de que 'network_type'='drive' está sendo usado.")
            sys.exit()

        # Definir o transformador
        crs_projected = self.G_projected.graph['crs']
        self.transformer = Transformer.from_crs(crs_projected, "epsg:4326", always_xy=True)

    def find_origin_node(self):
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
            print(f"Nó de Origem: {self.origin_node}")
            print(f"Coordenadas do Nó de Origem: {origin_node_coords}")
        except Exception as e:
            print(f"Erro ao encontrar o nó de origem: {e}")
            sys.exit()

    def print_graph_info(self):
        num_nodes = self.G_projected.number_of_nodes()
        num_edges = self.G_projected.number_of_edges()
        print(f"O grafo utilizado para o cálculo das rotas possui {num_nodes} nós e {num_edges} arestas.")
