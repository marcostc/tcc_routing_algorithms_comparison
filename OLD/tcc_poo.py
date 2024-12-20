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
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

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

class RedirectText(object):
    """
    Classe para redirecionar stdout e stderr para um widget Text do Tkinter.
    """
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        # Agendar a atualização do widget no thread principal
        self.text_widget.after(0, self._append_text, string)

    def _append_text(self, string):
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)  # Rolar para o final

    def flush(self):
        pass

class UserPreferences:
    def __init__(self, filename='user_preferences.json'):
        self.filename = filename
        self.preferences = self.load_preferences()
        # Definir cores e estilos padrão se não existirem
        if 'visualization' not in self.preferences:
            self.preferences['visualization'] = self.default_visualization_preferences()

    def default_visualization_preferences(self):
        return {
            'dijkstra': {'color': 'green', 'style': 'solid'},
            'astar': {'color': 'purple', 'style': 'solid'},
            'bellman_ford': {'color': 'orange', 'style': 'solid'},
            'bidirectional_dijkstra': {'color': 'blue', 'style': 'solid'},
            'bidirectional_a_star': {'color': 'darkgreen', 'style': 'solid'}
        }

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

    def get_user_input(self, address, radius, cuisine, num_destinations):
        self.preferences['address'] = address
        self.preferences['radius'] = radius
        self.preferences['cuisine'] = cuisine
        self.preferences['num_destinations'] = num_destinations
        return address, radius, cuisine, num_destinations

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

class POIFinder:
    def __init__(self, G_projected, origin_point_geo, radius):
        self.G_projected = G_projected
        self.origin_point_geo = origin_point_geo
        self.radius = radius
        self.cuisine = None  # Será definido após a seleção pelo usuário
        self.destination_nodes = []
        self.destination_coords_geo = []
        self.destination_names = []
        self.available_cuisines = set()  # Novo atributo para armazenar as cozinhas disponíveis

    def get_available_cuisines(self):
        # Buscar todos os restaurantes na área
        tags = {'amenity': 'restaurant'}
        pois = ox.geometries_from_point(self.origin_point_geo, tags=tags, dist=self.radius)

        if pois.empty:
            print("Nenhum estabelecimento encontrado na área.")
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
        if not self.cuisine:
            print("Nenhuma 'cuisine' foi selecionada.")
            return

        tags = {'amenity': 'restaurant'}
        pois = ox.geometries_from_point(self.origin_point_geo, tags=tags, dist=self.radius)

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
    def __init__(self, G_projected, transformer, visualization_prefs):
        self.G_projected = G_projected
        self.transformer = transformer
        self.visualization_prefs = visualization_prefs

    def get_dash_array(self, style):
        if style == 'solid':
            return None
        elif style == 'dashed':
            return '5, 5'
        elif style == 'dotted':
            return '1, 5'
        elif style == 'dashdot':
            return '5, 5, 1, 5'
        else:
            return None  # Default to solid

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

        # Adicionar rotas em camadas separadas
        for alg in algorithms:
            alg_prefs = self.visualization_prefs.get(alg, {'color': 'blue', 'style': 'solid'})
            color = alg_prefs['color']
            style = alg_prefs['style']
            dash_array = self.get_dash_array(style)

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
                        color=color,
                        weight=5,
                        opacity=1,
                        dash_array=dash_array,
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
                            'fill': color,
                            'font-weight': 'normal',
                            'font-size': '8'  # Aumenta o tamanho da seta
                        }
                    ).add_to(layer)
                except Exception as e:
                    print(f"Erro ao plotar rota {alg}: {e}")
            layer.add_to(m)

        # Adicionar controle de camadas
        folium.LayerControl().add_to(m)

        # Gerar nome de arquivo sem sobrescrever
        file_name = self.generate_unique_filename('mapa_rotas.html')

        # Salvar e exibir o mapa
        m.save(file_name)
        print(f"Mapa salvo como '{file_name}'. Abra-o no seu navegador para visualização.")
        # Abrir o mapa no navegador
        webbrowser.open(file_name)

    @staticmethod
    def generate_unique_filename(base_filename):
        """
        Gera um nome de arquivo único, incrementando um sufixo numérico se necessário.
        """
        if not os.path.exists(base_filename):
            return base_filename
        else:
            base, ext = os.path.splitext(base_filename)
            i = 1
            while True:
                new_filename = f"{base}_{i:02d}{ext}"
                if not os.path.exists(new_filename):
                    return new_filename
                i += 1

class RoutePlannerGUI:
    def __init__(self):
        self.preferences = UserPreferences()
        self.address = None
        self.radius = None
        self.cuisine = None
        self.num_destinations = None
        self.origin_point = None
        self.origin_address = None
        self.graph_handler = None
        self.poi_finder = None
        self.route_calculator = None
        self.route_plotter = None
        self.selected_coords_geo = []
        self.selected_names = []
        self.selected_dists = []
        self.selected_nodes = []
        self.algorithms = ['dijkstra', 'astar', 'bellman_ford', 'bidirectional_dijkstra', 'bidirectional_a_star']

        # Iniciar a interface gráfica
        self.root = tk.Tk()
        self.root.title("Planejador de Rotas")
        self.create_widgets()
        self.root.mainloop()

    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Campos de entrada
        ttk.Label(main_frame, text="Endereço de Origem:").grid(row=0, column=0, sticky=tk.W)
        self.address_entry = ttk.Entry(main_frame, width=50)
        self.address_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.address_entry.insert(0, self.preferences.preferences.get('address', ''))

        ttk.Label(main_frame, text="Raio de Busca (metros):").grid(row=1, column=0, sticky=tk.W)
        self.radius_entry = ttk.Entry(main_frame, width=20)
        self.radius_entry.grid(row=1, column=1, sticky=(tk.W, tk.E))
        self.radius_entry.insert(0, str(self.preferences.preferences.get('radius', 1000)))

        # Remover o campo 'Tipo de Estabelecimento'
        # Ajustar as posições dos demais widgets
        ttk.Label(main_frame, text="Número de Destinos Mais Próximos:").grid(row=2, column=0, sticky=tk.W)
        self.num_destinations_entry = ttk.Entry(main_frame, width=20)
        self.num_destinations_entry.grid(row=2, column=1, sticky=(tk.W, tk.E))
        self.num_destinations_entry.insert(0, str(self.preferences.preferences.get('num_destinations', 10)))

        # Botão de execução
        self.run_button = ttk.Button(main_frame, text="Calcular Rotas", command=self.run_thread)
        self.run_button.grid(row=3, column=0, columnspan=2, pady=10)

        # Botão para personalizar visualização
        self.customize_button = ttk.Button(main_frame, text="Personalizar Visualização", command=self.open_customization_window)
        self.customize_button.grid(row=4, column=0, columnspan=2, pady=5)

        # Barra de progresso
        self.progress = ttk.Progressbar(main_frame, orient='horizontal', mode='indeterminate')
        self.progress.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E))

        # Mensagens
        self.message = tk.StringVar()
        ttk.Label(main_frame, textvariable=self.message).grid(row=6, column=0, columnspan=2, sticky=tk.W)

        # Janela de saída de texto
        self.output_text = tk.Text(main_frame, wrap='word', height=15)
        self.output_text.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E))

        # Redirecionar stdout e stderr para a janela de texto
        sys.stdout = RedirectText(self.output_text)
        sys.stderr = RedirectText(self.output_text)

    def open_customization_window(self):
        CustomizationWindow(self.root, self.preferences)

    def run_thread(self):
        # Executar o processamento em uma thread separada para não travar a GUI
        threading.Thread(target=self.run).start()

    def run(self):
        self.run_button.config(state=tk.DISABLED)
        self.progress.start()
        self.message.set("Processando...")

        try:
            # Obter entradas do usuário
            self.address = self.address_entry.get()
            self.radius = int(self.radius_entry.get())
            self.num_destinations = int(self.num_destinations_entry.get())

            # Atualizar preferências (não salvamos 'cuisine' neste ponto)
            self.preferences.get_user_input(self.address, self.radius, '', self.num_destinations)
            self.preferences.save_preferences()

            # Geocodificar o endereço
            geocode_result = GeoCoder.geocode_address(self.address)
            if geocode_result is None:
                messagebox.showerror("Erro", "Endereço não encontrado. Tente novamente.")
                self.run_button.config(state=tk.NORMAL)
                self.progress.stop()
                self.message.set("")
                return
            elif isinstance(geocode_result, list) and len(geocode_result) > 1:
                # Se múltiplos resultados, permitir que o usuário selecione
                selected = self.select_address(geocode_result)
                if selected is None:
                    messagebox.showinfo("Informação", "Nenhum endereço selecionado.")
                    self.run_button.config(state=tk.NORMAL)
                    self.progress.stop()
                    self.message.set("")
                    return
                else:
                    self.origin_point = (selected[0], selected[1])
                    self.origin_address = selected[2]
            else:
                # Apenas um resultado encontrado
                self.origin_point = (geocode_result[0], geocode_result[1])
                self.origin_address = geocode_result[2]

            print(f"Endereço selecionado: {self.origin_address}")

            # Criar e processar o grafo
            self.graph_handler = GraphHandler(self.origin_point, self.radius)
            self.graph_handler.create_graph()
            self.graph_handler.find_origin_node()
            self.graph_handler.print_graph_info()

            # Buscar estabelecimentos e obter cozinhas disponíveis
            self.poi_finder = POIFinder(
                self.graph_handler.G_projected,
                self.origin_point,
                self.radius
            )

            # Executar get_available_cuisines em uma thread separada
            def fetch_cuisines():
                self.poi_finder.get_available_cuisines()
                cuisines = self.poi_finder.available_cuisines
                if not cuisines:
                    messagebox.showwarning("Aviso", "Nenhum tipo de estabelecimento encontrado na área.")
                    self.run_button.config(state=tk.NORMAL)
                    self.progress.stop()
                    self.message.set("")
                    return
                else:
                    selected_cuisine = self.select_cuisine(cuisines)
                    if selected_cuisine is None:
                        messagebox.showinfo("Informação", "Nenhuma opção selecionada.")
                        self.run_button.config(state=tk.NORMAL)
                        self.progress.stop()
                        self.message.set("")
                        return
                    else:
                        self.cuisine = selected_cuisine
                        self.preferences.preferences['cuisine'] = self.cuisine
                        self.preferences.save_preferences()
                        self.poi_finder.cuisine = self.cuisine

                        # Prosseguir com o restante do processamento na thread principal
                        self.after_fetch_cuisines()

            threading.Thread(target=fetch_cuisines).start()

        except Exception as e:
            print(f"Ocorreu um erro: {e}")
            messagebox.showerror("Erro", f"Ocorreu um erro: {e}")
            self.run_button.config(state=tk.NORMAL)
            self.progress.stop()

    def after_fetch_cuisines(self):
        try:
            # Buscar POIs com a 'cuisine' selecionada
            self.poi_finder.get_pois()

            if not self.poi_finder.destination_nodes:
                messagebox.showwarning("Aviso", "Nenhum destino encontrado. Tente novamente com outros parâmetros.")
                self.run_button.config(state=tk.NORMAL)
                self.progress.stop()
                self.message.set("")
                return

            # Selecionar os destinos mais próximos
            self.selected_nodes, self.selected_names, self.selected_dists = self.select_closest_destinations()

            if not self.selected_nodes:
                messagebox.showwarning("Aviso", "Nenhum destino selecionado. Tente novamente.")
                self.run_button.config(state=tk.NORMAL)
                self.progress.stop()
                self.message.set("")
                return

            # Calcular rotas
            self.route_calculator = RouteCalculator(
                self.graph_handler.G_projected,
                self.graph_handler.origin_node,
                self.selected_nodes
            )
            self.route_calculator.calculate_routes(algorithms=self.algorithms)

            # Exibir tempos médios
            for alg, avg_time in self.route_calculator.avg_times.items():
                print(f"Tempo Médio {alg.replace('_', ' ').capitalize()}: {avg_time:.6f} segundos")

            # Plotar as rotas
            self.route_plotter = RoutePlotter(
                self.graph_handler.G_projected,
                self.graph_handler.transformer,
                self.preferences.preferences['visualization']
            )

            routes_limit = len(self.selected_nodes)  # Usar o número de destinos selecionados

            self.route_plotter.plot_routes_subset(
                self.origin_point,
                self.route_calculator.routes,
                self.selected_coords_geo,
                self.selected_names,
                self.selected_dists,
                algorithms=self.algorithms,
                limit=routes_limit
            )

            self.message.set("Processamento concluído. O mapa foi aberto no navegador.")

        except Exception as e:
            print(f"Ocorreu um erro: {e}")
            messagebox.showerror("Erro", f"Ocorreu um erro: {e}")
        finally:
            self.run_button.config(state=tk.NORMAL)
            self.progress.stop()

    def select_address(self, addresses):
        """
        Exibe uma janela para o usuário selecionar um endereço dentre as opções encontradas.
        """
        def on_select():
            selected_item = tree.selection()
            if selected_item:
                idx = int(selected_item[0])
                selected_address[0] = addresses[idx]
                top.destroy()
            else:
                selected_address[0] = None
                top.destroy()

        selected_address = [None]
        top = tk.Toplevel(self.root)
        top.title("Selecione o Endereço")
        top.geometry("600x300")  # Definir tamanho inicial da janela

        ttk.Label(top, text="Múltiplos endereços encontrados. Selecione o desejado:").pack(pady=5)

        # Frame para conter o Treeview e as barras de rolagem
        tree_frame = ttk.Frame(top)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Barras de rolagem
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)

        # Criar o Treeview com suporte a rolagem
        columns = ('endereco',)
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                            yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Configurar colunas
        tree.heading('endereco', text='Endereço')
        tree.column('endereco', minwidth=600, width=600, stretch=False)

        # Inserir os endereços no Treeview
        for idx, addr in enumerate(addresses):
            tree.insert('', 'end', iid=str(idx), values=(f"{idx + 1}. {addr[2]}",))

        # Configurar layout
        tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')

        # Configurar barras de rolagem
        v_scrollbar.config(command=tree.yview)
        h_scrollbar.config(command=tree.xview)

        # Expandir o Treeview quando a janela for redimensionada
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        select_button = ttk.Button(top, text="Selecionar", command=on_select)
        select_button.pack(pady=5)

        self.root.wait_window(top)
        return selected_address[0]

    def select_cuisine(self, cuisines):
        """
        Exibe uma janela para o usuário selecionar uma 'cuisine' dentre as opções encontradas.
        """
        def on_select():
            selected_item = listbox.curselection()
            if selected_item:
                idx = selected_item[0]
                selected_cuisine[0] = cuisines_list[idx]
                top.destroy()
            else:
                messagebox.showwarning("Aviso", "Nenhuma opção selecionada.")

        selected_cuisine = [None]
        top = tk.Toplevel(self.root)
        top.title("Selecione o Tipo de Estabelecimento")
        top.geometry("400x300")

        ttk.Label(top, text="Selecione o tipo de estabelecimento desejado:").pack(pady=5)

        # Listbox para exibir as opções
        listbox = tk.Listbox(top)
        listbox.pack(fill=tk.BOTH, expand=True)

        # Inserir as opções no listbox
        cuisines_list = sorted(cuisines)
        for cuisine in cuisines_list:
            listbox.insert(tk.END, cuisine)

        select_button = ttk.Button(top, text="Selecionar", command=on_select)
        select_button.pack(pady=5)

        self.root.wait_window(top)
        return selected_cuisine[0]

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

        # Selecionar o número de destinos especificado pelo usuário
        num_destinations = self.num_destinations
        if num_destinations > len(distances):
            num_destinations = len(distances)

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

class CustomizationWindow:
    def __init__(self, master, preferences):
        self.master = master
        self.preferences = preferences
        self.top = tk.Toplevel(self.master)
        self.top.title("Personalizar Visualização")
        self.create_widgets()

    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.top, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        algorithms = ['dijkstra', 'astar', 'bellman_ford', 'bidirectional_dijkstra', 'bidirectional_a_star']
        self.color_vars = {}
        self.style_vars = {}

        # Opções de cores e estilos
        for idx, alg in enumerate(algorithms):
            alg_name = alg.replace('_', ' ').capitalize()
            ttk.Label(main_frame, text=f"{alg_name}").grid(row=idx, column=0, sticky=tk.W)

            # Campo para selecionar a cor
            color_var = tk.StringVar(value=self.preferences.preferences['visualization'][alg]['color'])
            self.color_vars[alg] = color_var
            color_entry = ttk.Entry(main_frame, textvariable=color_var, width=10)
            color_entry.grid(row=idx, column=1, sticky=tk.W)
            ttk.Label(main_frame, text="Cor (nome ou código HEX)").grid(row=idx, column=2, sticky=tk.W)

            # Campo para selecionar o estilo
            style_var = tk.StringVar(value=self.preferences.preferences['visualization'][alg]['style'])
            self.style_vars[alg] = style_var
            style_combo = ttk.Combobox(main_frame, textvariable=style_var, values=['solid', 'dashed', 'dotted', 'dashdot'], width=10)
            style_combo.grid(row=idx, column=3, sticky=tk.W)
            ttk.Label(main_frame, text="Estilo da Linha").grid(row=idx, column=4, sticky=tk.W)

        # Botão para salvar as preferências
        save_button = ttk.Button(main_frame, text="Salvar", command=self.save_preferences)
        save_button.grid(row=len(algorithms), column=0, columnspan=5, pady=10)

    def save_preferences(self):
        for alg in self.color_vars:
            self.preferences.preferences['visualization'][alg]['color'] = self.color_vars[alg].get()
            self.preferences.preferences['visualization'][alg]['style'] = self.style_vars[alg].get()
        self.preferences.save_preferences()
        messagebox.showinfo("Informação", "Preferências salvas com sucesso.")
        self.top.destroy()

if __name__ == "__main__":
    RoutePlannerGUI()
