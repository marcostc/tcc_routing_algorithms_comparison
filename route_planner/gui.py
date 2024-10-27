# route_planner/gui.py

import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import networkx as nx

from .utils import RedirectText
from .preferences import UserPreferences
from .geocoder import GeoCoder
from .graph_handler import GraphHandler
from .poi_finder import POIFinder
from .route_calculator import RouteCalculator
from .route_plotter import RoutePlotter
from .customization_window import CustomizationWindow

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