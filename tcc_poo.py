import json
import os
import sys
import time
import warnings
import heapq
import geojson
import folium
import geopandas as gpd
import networkx as nx
import osmnx as ox
from shapely.geometry import Point, LineString
from folium.plugins import PolyLineTextPath
from geopy.geocoders import Nominatim
from pyproj import Transformer

# Ignorar FutureWarnings temporariamente
warnings.filterwarnings("ignore", category=FutureWarning)

def timed(func):
    """
    Decorador para medir o tempo de execução de uma função.
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        func_name = func.__name__.replace('_', ' ').capitalize()
        print(f"Tempo de execução de {func_name}: {end_time - start_time:.6f} segundos")
        return result
    return wrapper

class UserPreferences:
    def __init__(self, filename='user_preferences.json'):
        self.filename = filename
        self.preferences = self.load_preferences()

    def save_preferences(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.preferences, f, ensure_ascii=False, indent=4)

    def load_preferences(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r', encoding='utf-8') as f:
                preferences = json.load(f)
            return preferences
        else:
            return {}

    def get_user_input(self):
        # Endereço de origem
        if 'address' in self.preferences and self.preferences['address']:
            use_previous = input(f"Deseja usar o endereço salvo '{self.preferences['address']}'? (s/n): ").lower()
            if use_previous == 's':
                address = self.preferences['address']
                print(f"Usando endereço anterior: {address}")
            else:
                address = input("Digite o novo endereço de origem: ")
                if address.strip() == '':
                    print("Nenhum endereço fornecido. Encerrando a aplicação.")
                    return None, None, None
                self.preferences['address'] = address  # Atualizar preferências
        else:
            address = input("Digite o endereço de origem: ")
            if address.strip() == '':
                print("Nenhum endereço fornecido. Encerrando a aplicação.")
                return None, None, None
            self.preferences['address'] = address  # Atualizar preferências

        # Raio de busca
        if 'radius' in self.preferences and self.preferences['radius']:
            radius_default = self.preferences['radius']
        else:
            radius_default = 1000  # 1 km como padrão

        radius_input = input(f"Digite o raio de busca em metros (padrão {radius_default}m): ")
        if radius_input.strip() == '':
            radius = radius_default  # Usar raio anterior ou padrão
        else:
            try:
                radius = int(radius_input)
                self.preferences['radius'] = radius  # Atualizar preferências
            except ValueError:
                print("Entrada inválida para o raio. Usando o valor padrão.")
                radius = radius_default

        # Tipo de estabelecimento (cuisine)
        if 'cuisine' in self.preferences and self.preferences['cuisine']:
            cuisine_default = self.preferences['cuisine']
        else:
            cuisine_default = 'pizza'

        cuisine_input = input(f"Digite o tipo de estabelecimento para buscar (padrão '{cuisine_default}'): ")
        if cuisine_input.strip() == '':
            cuisine = cuisine_default  # Usar tipo anterior ou padrão
        else:
            cuisine = cuisine_input
            self.preferences['cuisine'] = cuisine  # Atualizar preferências

        return address, radius, cuisine

class GeoCoder:
    @staticmethod
    def geocode_address(address):
        geolocator = Nominatim(user_agent="shortest_path_tester")
        locations = geolocator.geocode(address, exactly_one=False, limit=5)
        if not locations:
            print("Endereço não encontrado. Tente novamente.")
            return None
        elif len(locations) == 1:
            location = locations[0]
            return (location.latitude, location.longitude, location.address)
        else:
            print("Vários endereços encontrados:")
            for idx, loc in enumerate(locations):
                print(f"{idx + 1}: {loc.address}")
            while True:
                try:
                    choice = int(input("Escolha o número do endereço correto (ou 0 para sair): "))
                    if choice == 0:
                        return None
                    elif 1 <= choice <= len(locations):
                        location = locations[choice - 1]
                        return (location.latitude, location.longitude, location.address)
                    else:
                        print("Opção inválida. Tente novamente.")
                except ValueError:
                    print("Entrada inválida. Por favor, insira um número.")

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

class POIFinder:
    def __init__(self, G_projected, origin_point_geo, radius, cuisine):
        self.G_projected = G_projected
        self.origin_point_geo = origin_point_geo
        self.radius = radius
        self.cuisine = cuisine
        self.destination_nodes = []
        self.destination_coords_geo = []
        self.destination_names = []

    def get_pois(self):
        tags = {'amenity': 'restaurant'}
        pois = ox.geometries_from_point(self.origin_point_geo, tags=tags, dist=self.radius)

        if pois.empty:
            print("Nenhum estabelecimento encontrado na área.")
            return
        else:
            print(f"{len(pois)} estabelecimentos encontrados.")

            # Filtrar por substring na coluna 'cuisine'
            if 'cuisine' in pois.columns:
                pois = pois[pois['cuisine'].str.contains(self.cuisine, case=False, na=False)]
                print(f"{len(pois)} estabelecimentos correspondem à busca por '{self.cuisine}'.")
            else:
                print("A coluna 'cuisine' não está presente nos dados.")
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

class RouteCalculator:
    def __init__(self, G_projected, origin_node, destination_nodes):
        self.G_projected = G_projected
        self.origin_node = origin_node
        self.destination_nodes = destination_nodes
        self.routes = {}
        self.avg_times = {}

    @timed
    def calculate_routes(self, algorithms):
        self.routes = {alg: [] for alg in algorithms}
        times = {alg: [] for alg in algorithms}

        for alg in algorithms:
            for target in self.destination_nodes:
                try:
                    start_time = time.time()
                    if alg == 'dijkstra':
                        route = nx.shortest_path(self.G_projected, self.origin_node, target, weight='length')
                    elif alg == 'astar':
                        route = nx.astar_path(
                            self.G_projected,
                            self.origin_node,
                            target,
                            weight='length',
                            heuristic=lambda u, v: ox.distance.euclidean(
                                self.G_projected.nodes[u]['y'], self.G_projected.nodes[u]['x'],
                                self.G_projected.nodes[v]['y'], self.G_projected.nodes[v]['x']
                            )
                        )
                    elif alg == 'bellman_ford':
                        route = nx.bellman_ford_path(self.G_projected, self.origin_node, target, weight='length')
                    elif alg == 'bidirectional_dijkstra':
                        path = nx.bidirectional_dijkstra(self.G_projected, self.origin_node, target, weight='length')[1]
                        route = path
                    elif alg == 'bidirectional_a_star':
                        heuristic = lambda u, v: ox.distance.euclidean(
                            self.G_projected.nodes[u]['y'], self.G_projected.nodes[u]['x'],
                            self.G_projected.nodes[v]['y'], self.G_projected.nodes[v]['x']
                        )
                        route = self.bidirectional_a_star(self.G_projected, self.origin_node, target, heuristic)
                    else:
                        raise ValueError("Algoritmo não suportado.")
                    end_time = time.time()
                    self.routes[alg].append(route)
                    times[alg].append(end_time - start_time)
                except nx.NetworkXNoPath:
                    print(f"Nenhuma rota encontrada para o nó {target} usando {alg}.")
                except Exception as e:
                    print(f"Erro ao calcular rota para o nó {target} usando {alg}: {e}")

        self.avg_times = {alg: (sum(times[alg]) / len(times[alg]) if times[alg] else 0) for alg in algorithms}

    @staticmethod
    def bidirectional_a_star(G, source, target, heuristic):
        # Implementação do algoritmo Bidirectional A*
        # (Mesmo código da versão anterior)
        forward_queue = []
        backward_queue = []
        heapq.heappush(forward_queue, (heuristic(source, target), 0, source))
        heapq.heappush(backward_queue, (heuristic(target, source), 0, target))

        forward_visited = {source: 0}
        backward_visited = {target: 0}

        forward_parents = {source: None}
        backward_parents = {target: None}

        meeting_node = None
        best_cost = float('inf')

        while forward_queue and backward_queue:
            # Verifica a condição de parada
            min_forward_priority = forward_queue[0][0]
            min_backward_priority = backward_queue[0][0]
            if best_cost <= min_forward_priority + min_backward_priority:
                break

            # Expansão na direção forward
            if forward_queue:
                current_forward_priority, current_forward_cost, current_forward_node = heapq.heappop(forward_queue)
                if current_forward_node in backward_visited:
                    total_cost = current_forward_cost + backward_visited[current_forward_node]
                    if total_cost < best_cost:
                        best_cost = total_cost
                        meeting_node = current_forward_node
                for neighbor in G.successors(current_forward_node):
                    edge_data = G.get_edge_data(current_forward_node, neighbor, default={})
                    length = edge_data.get('length', 1)
                    cost = forward_visited[current_forward_node] + length
                    if neighbor not in forward_visited or cost < forward_visited[neighbor]:
                        forward_visited[neighbor] = cost
                        priority = cost + heuristic(neighbor, target)
                        heapq.heappush(forward_queue, (priority, cost, neighbor))
                        forward_parents[neighbor] = current_forward_node

            # Expansão na direção backward
            if backward_queue:
                current_backward_priority, current_backward_cost, current_backward_node = heapq.heappop(backward_queue)
                if current_backward_node in forward_visited:
                    total_cost = current_backward_cost + forward_visited[current_backward_node]
                    if total_cost < best_cost:
                        best_cost = total_cost
                        meeting_node = current_backward_node
                for neighbor in G.predecessors(current_backward_node):
                    edge_data = G.get_edge_data(neighbor, current_backward_node, default={})
                    length = edge_data.get('length', 1)
                    cost = backward_visited[current_backward_node] + length
                    if neighbor not in backward_visited or cost < backward_visited[neighbor]:
                        backward_visited[neighbor] = cost
                        priority = cost + heuristic(neighbor, source)
                        heapq.heappush(backward_queue, (priority, cost, neighbor))
                        backward_parents[neighbor] = current_backward_node

        if meeting_node is None:
            raise nx.NetworkXNoPath(f"Nenhuma rota encontrada entre {source} e {target} usando Bidirectional A*.")

        # Reconstrução do caminho
        path_forward = []
        node = meeting_node
        while node is not None:
            path_forward.append(node)
            node = forward_parents[node]
        path_forward.reverse()

        path_backward = []
        node = backward_parents[meeting_node]
        while node is not None:
            path_backward.append(node)
            node = backward_parents[node]

        full_path = path_forward + path_backward
        return full_path

class RoutePlotter:
    def __init__(self, G_projected, transformer):
        self.G_projected = G_projected
        self.transformer = transformer

    def plot_routes_subset(self, origin_point_geo, routes, destination_coords_geo, destination_names, destination_dists, algorithms, limit):
        # Plota as rotas no mapa
        m = folium.Map(location=origin_point_geo, zoom_start=13)

        # Adicionar marcador para a origem
        folium.Marker(
            location=origin_point_geo,
            popup="Origem",
            icon=folium.Icon(color='blue', icon='home')
        ).add_to(m)

        # Adicionar marcadores para os destinos
        for idx, (coord, name, dist) in enumerate(zip(destination_coords_geo, destination_names, destination_dists)):
            folium.Marker(
                location=coord,
                popup=f"Destino {idx+1}: {name} (Distância: {dist:.2f} metros)",
                icon=folium.Icon(color='red', icon='cutlery')
            ).add_to(m)

        # Definir cores para os algoritmos
        color_map = {
            'dijkstra': 'green',
            'astar': 'purple',
            'bellman_ford': 'orange',
            'bidirectional_dijkstra': 'blue',
            'bidirectional_a_star': 'darkgreen'
        }

        # Adicionar rotas em camadas separadas, limitando o número de rotas
        for alg in algorithms:
            layer = folium.FeatureGroup(name=f"Rotas {alg.replace('_', ' ').capitalize()}")
            for route in routes[alg][:limit]:
                try:
                    if len(route) < 2:
                        continue  # Rotas inválidas com menos de 2 nós

                    # Obter as coordenadas projetadas dos nós da rota
                    route_proj = [(self.G_projected.nodes[node]['x'], self.G_projected.nodes[node]['y']) for node in route]

                    # Converter para geográficas
                    route_geo = [self.transformer.transform(x, y) for x, y in route_proj]

                    # Rearranjar para (lat, lon) para Folium
                    route_geo_latlon = [(lat, lon) for lon, lat in route_geo]

                    # Adicionar a rota como PolyLine
                    polyline = folium.PolyLine(
                        route_geo_latlon,
                        color=color_map.get(alg, 'blue'),
                        weight=5,
                        opacity=1,
                        popup=f"Rota {alg.replace('_', ' ').capitalize()}"
                    )
                    polyline.add_to(layer)

                    # Adicionar setas para indicar o sentido do percurso usando PolyLineTextPath
                    arrow_symbol = '\u27A4'  # Símbolo Unicode para seta para a direita
                    folium.plugins.PolyLineTextPath(
                        polyline,
                        arrow_symbol * 3,
                        repeat=True,      # Repetir o símbolo para aumentar o tamanho
                        offset=9,         # Ajusta a posição vertical do símbolo
                        attributes={
                            'fill': color_map.get(alg, 'blue'),
                            'font-weight': 'normal',
                            'font-size': '8'  # Aumenta o tamanho da seta
                        }
                    ).add_to(layer)
                except Exception as e:
                    print(f"Erro ao plotar rota {alg}: {e}")
            layer.add_to(m)

        # Adicionar controle de camadas
        folium.LayerControl().add_to(m)

        # Salvar e exibir o mapa
        m.save('mapa_rotas.html')
        print("Mapa salvo como 'mapa_rotas.html'. Abra-o no seu navegador para visualização.")

class RoutePlanner:
    def __init__(self):
        self.preferences = UserPreferences()
        self.address = None
        self.radius = None
        self.cuisine = None
        self.origin_point = None
        self.origin_address = None
        self.graph_handler = None
        self.poi_finder = None
        self.route_calculator = None
        self.route_plotter = None

    def run(self):
        while True:
            # Coletar informações do usuário
            self.address, self.radius, self.cuisine = self.preferences.get_user_input()
            if not self.address:
                print("Nenhum endereço fornecido. Encerrando a aplicação.")
                sys.exit()

            # Geocodificar o endereço
            geocode_result = GeoCoder.geocode_address(self.address)
            if geocode_result is None:
                print("O endereço fornecido não pode ser convertido em coordenadas geográficas. Tente novamente!\n")
                continue  # Tentar novamente
            else:
                self.origin_point = (geocode_result[0], geocode_result[1])
                self.origin_address = geocode_result[2]
                print(f"Endereço selecionado: {self.origin_address}")

            # Criar e processar o grafo
            self.graph_handler = GraphHandler(self.origin_point, self.radius)
            self.graph_handler.create_graph()
            self.graph_handler.find_origin_node()

            # Buscar estabelecimentos
            self.poi_finder = POIFinder(
                self.graph_handler.G_projected,
                self.origin_point,
                self.radius,
                self.cuisine
            )
            self.poi_finder.get_pois()

            if not self.poi_finder.destination_nodes:
                print("Nenhum destino encontrado. Tente novamente com outros parâmetros.\n")
                continue  # Reiniciar o loop

            # Selecionar os destinos mais próximos
            selected_nodes, selected_names, selected_dists = self.select_closest_destinations()

            if not selected_nodes:
                print("Nenhum destino selecionado. Tente novamente.\n")
                continue  # Reiniciar o loop
            else:
                break

        # Exibir informações do grafo
        print(f"O grafo utilizado para o cálculo das rotas possui {self.graph_handler.G_projected.number_of_nodes()} nós e {self.graph_handler.G_projected.number_of_edges()} arestas.")

        # Atualizar o endereço completo nas preferências
        self.preferences.preferences['address_full'] = self.origin_address

        # Salvar preferências atualizadas
        self.preferences.save_preferences()

        # Calcular rotas
        algorithms = ['dijkstra', 'astar', 'bellman_ford', 'bidirectional_dijkstra', 'bidirectional_a_star']
        self.route_calculator = RouteCalculator(
            self.graph_handler.G_projected,
            self.graph_handler.origin_node,
            selected_nodes
        )
        self.route_calculator.calculate_routes(algorithms=algorithms)

        # Exibir tempos médios
        for alg, avg_time in self.route_calculator.avg_times.items():
            print(f"Tempo Médio {alg.replace('_', ' ').capitalize()}: {avg_time:.6f} segundos")

        # Verificar número de rotas
        routes_limit = 0
        for alg in algorithms:
            print(f"Total de rotas para {alg}: {len(self.route_calculator.routes[alg])}")
            if routes_limit < len(self.route_calculator.routes[alg]):
                routes_limit = len(self.route_calculator.routes[alg])

        # Plotar as rotas
        self.route_plotter = RoutePlotter(
            self.graph_handler.G_projected,
            self.graph_handler.transformer
        )
        self.route_plotter.plot_routes_subset(
            self.origin_point,
            self.route_calculator.routes,
            self.selected_coords_geo,
            selected_names,
            selected_dists,
            algorithms=algorithms,
            limit=routes_limit
        )

    def select_closest_destinations(self):
        G_projected = self.graph_handler.G_projected
        origin_node = self.graph_handler.origin_node
        destination_nodes = self.poi_finder.destination_nodes
        destination_names = self.poi_finder.destination_names

        # Calcular distâncias do nó de origem para todos os destinos
        distances = []
        for idx, dest_node in enumerate(destination_nodes):
            try:
                length = nx.shortest_path_length(G_projected, origin_node, dest_node, weight='length')
                distances.append((length, dest_node, destination_names[idx]))
            except nx.NetworkXNoPath:
                continue  # Ignorar destinos sem caminho disponível

        # Ordenar por distância
        distances.sort(key=lambda x: x[0])

        if not distances:
            print("Nenhum destino alcançável encontrado.")
            return [], [], []

        # Perguntar ao usuário quantos destinos deseja
        num_destinations_input = input(f"Total de destinos encontrados: {len(distances)}. Quantos deseja traçar? (pressione Enter para todos): ")
        if num_destinations_input == '':
            num_destinations = len(distances)
        else:
            num_destinations = int(num_destinations_input)

        # Selecionar os N destinos mais próximos
        selected_destinations = distances[:num_destinations]

        # Extrair os nós e nomes selecionados
        selected_nodes = [node for dist, node, name in selected_destinations]
        selected_names = [name for dist, node, name in selected_destinations]
        selected_dists = [dist for dist, node, name in selected_destinations]

        # Filtrar as coordenadas e nomes correspondentes aos destinos selecionados
        selected_coords_geo = []
        for node in selected_nodes:
            idx = list(destination_nodes).index(node)
            selected_coords_geo.append(self.poi_finder.destination_coords_geo[idx])

        self.selected_coords_geo = selected_coords_geo  # Para uso posterior

        return selected_nodes, selected_names, selected_dists

if __name__ == "__main__":
    planner = RoutePlanner()
    planner.run()