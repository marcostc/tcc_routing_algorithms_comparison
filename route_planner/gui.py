# route_planner/gui.py

import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import networkx as nx
from PIL import Image, ImageTk
import pandas as pd
import os

from route_planner.utils import RedirectText
from route_planner.preferences import UserPreferences
from route_planner.geocoder import GeoCoder
from route_planner.graph_handler import GraphHandler
from route_planner.poi_finder import POIFinder
from route_planner.route_calculator import RouteCalculator
from route_planner.route_plotter import RoutePlotter
from route_planner.customization_window import CustomizationWindow
from route_planner.logger import logger  # Importar o logger
from route_planner.data_analyzer import DataAnalyzer

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
        self.graph_info_label = None  # Atributo para exibir informações do grafo
        self.main_frame = None  # Atributo para o frame principal

        # Iniciar a interface gráfica
        self.root = tk.Tk()
        self.root.title("Planejador de Rotas")
        self.load_images()
        self.create_widgets()
        self.apply_styles()
        self.create_menu()
        self.root.mainloop()

    def load_images(self):
        import io
        import requests
        from PIL import Image, ImageTk

        # Caminhos locais dos ícones
        calculate_icon_path = 'icons/calculate.png'
        customize_icon_path = 'icons/customize.png'

        # URLs dos ícones na internet
        calculate_icon_url = 'https://img.icons8.com/ios-filled/50/000000/route.png'
        customize_icon_url = 'https://img.icons8.com/ios-filled/50/000000/settings.png'

        # Carregar ícone 'calculate'
        self.calculate_icon = None
        try:
            # Tentar carregar localmente
            self.calculate_icon = ImageTk.PhotoImage(Image.open(calculate_icon_path).resize((20, 20)))
            logger.info("Ícone 'calculate' carregado localmente com sucesso.")
        except Exception as e:
            logger.warning(f"Não foi possível carregar o ícone 'calculate' localmente: {e}")
            # Tentar baixar da internet
            try:
                logger.info("Tentando baixar o ícone 'calculate' da internet...")
                response = requests.get(calculate_icon_url, timeout=5)
                response.raise_for_status()
                image_data = response.content
                image = Image.open(io.BytesIO(image_data)).resize((20, 20))
                self.calculate_icon = ImageTk.PhotoImage(image)
                logger.info("Ícone 'calculate' baixado com sucesso da internet.")
            except Exception as e:
                logger.error(f"Erro ao baixar o ícone 'calculate' da internet: {e}")
                self.calculate_icon = None

        # Carregar ícone 'customize'
        self.customize_icon = None
        try:
            # Tentar carregar localmente
            self.customize_icon = ImageTk.PhotoImage(Image.open(customize_icon_path).resize((20, 20)))
            logger.info("Ícone 'customize' carregado localmente com sucesso.")
        except Exception as e:
            logger.warning(f"Não foi possível carregar o ícone 'customize' localmente: {e}")
            # Tentar baixar da internet
            try:
                logger.info("Tentando baixar o ícone 'customize' da internet...")
                response = requests.get(customize_icon_url, timeout=5)
                response.raise_for_status()
                image_data = response.content
                image = Image.open(io.BytesIO(image_data)).resize((20, 20))
                self.customize_icon = ImageTk.PhotoImage(image)
                logger.info("Ícone 'customize' baixado com sucesso da internet.")
            except Exception as e:
                logger.error(f"Erro ao baixar o ícone 'customize' da internet: {e}")
                self.customize_icon = None

    def create_widgets(self):
        # Frame principal
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        # Configurar expansão
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)

        # Campos de entrada com labels
        ttk.Label(self.main_frame, text="Endereço de Origem:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.address_entry = ttk.Entry(self.main_frame)
        self.address_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        self.address_entry.insert(0, self.preferences.preferences.get('address', ''))

        # Informações do grafo
        self.graph_info_label = ttk.Label(self.main_frame, text="", justify=tk.LEFT)
        self.graph_info_label.grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=5)

        # Atualizar a configuração da grade
        self.main_frame.rowconfigure(7, weight=0)

        ttk.Label(self.main_frame, text="Raio de Busca (metros):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.radius_entry = ttk.Entry(self.main_frame)
        self.radius_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        self.radius_entry.insert(0, str(self.preferences.preferences.get('radius', 1000)))

        ttk.Label(self.main_frame, text="Número de Destinos:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.num_destinations_entry = ttk.Entry(self.main_frame)
        self.num_destinations_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        self.num_destinations_entry.insert(0, str(self.preferences.preferences.get('num_destinations', 10)))

        # Botões
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        self.run_button = ttk.Button(button_frame, text="Calcular Rotas", command=self.run_thread)
        self.run_button.pack(side=tk.LEFT, padx=5)
        # Botão para gerar relatório
        self.report_button = ttk.Button(button_frame, text="Gerar Relatório", command=self.generate_report)
        self.report_button.pack(side=tk.LEFT, padx=5)

        self.customize_button = ttk.Button(button_frame, text="Personalizar Visualização", command=self.open_customization_window)
        self.customize_button.pack(side=tk.LEFT, padx=5)

        # Barra de progresso
        self.progress = ttk.Progressbar(self.main_frame, orient='horizontal', mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Mensagens
        self.message = tk.StringVar()
        ttk.Label(self.main_frame, textvariable=self.message).grid(row=5, column=0, columnspan=2, sticky=tk.W)

        # Janela de saída de texto
        self.output_text = tk.Text(self.main_frame, wrap='word', height=10)
        self.output_text.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.rowconfigure(6, weight=1)

        # Redirecionar stdout e stderr para a janela de texto
        sys.stdout = RedirectText(self.output_text)

        # Não redirecionar o stderr
        # sys.stderr = RedirectText(self.output_text)

    def apply_styles(self):
        style = ttk.Style()
        style.configure('TButton', font=('Arial', 10))
        style.configure('TLabel', font=('Arial', 10))
        style.configure('TEntry', font=('Arial', 10))

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Sobre", command=self.show_about)
        menubar.add_cascade(label="Ajuda", menu=help_menu)

    def show_about(self):
        messagebox.showinfo("Sobre", "Planejador de Rotas\nVersão 1.0\nDesenvolvido por [Seu Nome]")

    def open_customization_window(self):
        CustomizationWindow(self.root, self.preferences)

    def run_thread(self):
        # Alterar o cursor para 'watch' durante o processamento
        self.root.config(cursor='watch')
        # Executar o processamento em uma thread separada para não travar a GUI
        threading.Thread(target=self.run).start()

        # Informações do grafo
        self.graph_info_label = ttk.Label(self.main_frame, text="", justify=tk.LEFT)
        self.graph_info_label.grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=5)

        # Atualizar a configuração da grade
        self.main_frame.rowconfigure(7, weight=0)

        # Informações do grafo
        self.graph_info_label = ttk.Label(self.main_frame, text="", justify=tk.LEFT)
        self.graph_info_label.grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=5)

        # Atualizar a configuração da grade
        self.main_frame.rowconfigure(7, weight=0)

        # Informações do grafo
        self.graph_info_label = ttk.Label(self.main_frame, text="", justify=tk.LEFT)
        self.graph_info_label.grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=5)

        # Atualizar a configuração da grade
        self.main_frame.rowconfigure(7, weight=0)

    def validate_inputs(self):
        valid = True
        # Validar o raio
        try:
            radius = int(self.radius_entry.get())
            if radius <= 0:
                raise ValueError
            self.radius_entry.config(background='white')
        except ValueError:
            self.radius_entry.config(background='#FFCCCC')  # Vermelho claro
            valid = False

        # Validar o número de destinos
        try:
            num_destinations = int(self.num_destinations_entry.get())
            if num_destinations <= 0:
                raise ValueError
            self.num_destinations_entry.config(background='white')
        except ValueError:
            self.num_destinations_entry.config(background='#FFCCCC')  # Vermelho claro
            valid = False

        return valid

    def run(self):
        if not self.validate_inputs():
            messagebox.showerror("Erro", "Por favor, corrija os campos destacados em vermelho.")
            self.run_button.config(state=tk.NORMAL)
            self.progress.stop()
            self.message.set("")
            self.root.config(cursor='')
            return

        self.run_button.config(state=tk.DISABLED)
        self.progress.start()
        self.message.set("Processando...")

        try:
            # Obter entradas do usuário
            self.address = self.address_entry.get()
            self.radius = int(self.radius_entry.get())
            self.num_destinations = int(self.num_destinations_entry.get())

            # Atualizar preferências
            self.preferences.get_user_input(self.address, self.radius, '', self.num_destinations)
            self.preferences.save_preferences()

            # Geocodificar o endereço
            geocode_result = GeoCoder.geocode_address(self.address)
            if geocode_result is None:
                messagebox.showerror("Erro", "Endereço não encontrado. Tente novamente.")
                logger.warning("Endereço não encontrado.")
                return
            elif isinstance(geocode_result, list) and len(geocode_result) > 1:
                # Se múltiplos resultados, permitir que o usuário selecione
                selected = self.select_address(geocode_result)
                if selected is None:
                    messagebox.showinfo("Informação", "Nenhum endereço selecionado.")
                    return
                else:
                    self.origin_point = (selected[0], selected[1])
                    self.origin_address = selected[2]
            else:
                # Apenas um resultado encontrado
                self.origin_point = (geocode_result[0], geocode_result[1])
                self.origin_address = geocode_result[2]

            logger.info(f"Endereço selecionado: {self.origin_address}")

            # Criar e processar o grafo
            self.graph_handler = GraphHandler(self.origin_point, self.radius)
            self.graph_handler.create_graph()
            self.graph_handler.find_origin_node()
            self.graph_handler.print_graph_info()

            # Exibir informações do grafo na interface
            self.display_graph_info()

            # Prosseguir com o restante do processamento
            threading.Thread(target=self.fetch_cuisines).start()

        except Exception as e:
            logger.exception(f"Ocorreu um erro no método run: {e}")
            messagebox.showerror("Erro", f"Ocorreu um erro: {e}")
        finally:
            # Reabilitar o botão e parar a barra de progresso
            self.root.after(0, lambda: self.run_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.message.set(""))
            self.root.after(0, lambda: self.root.config(cursor=''))
 
    def display_graph_info(self):
        """
        Exibe as informações do grafo na interface gráfica.
        """
        num_nodes = self.graph_handler.G_projected.number_of_nodes()
        num_edges = self.graph_handler.G_projected.number_of_edges()
        density = self.graph_handler.graph_density

        info_text = f"Grafo: {num_nodes} nós, {num_edges} arestas\n"
        if density is not None:
            info_text += f"Densidade do grafo: {density:.6f}"
        else:
            info_text += "Densidade do grafo: Não disponível"

        self.graph_info_label.config(text=info_text)

    def fetch_cuisines(self):
        try:
            # Buscar estabelecimentos e obter cozinhas disponíveis
            self.poi_finder = POIFinder(
                self.graph_handler.G_projected,
                self.origin_point,
                self.radius
            )
            self.poi_finder.get_available_cuisines()
            cuisine_counts = self.poi_finder.cuisine_counts
            if not cuisine_counts:
                self.root.after(0, lambda: messagebox.showwarning("Aviso", "Nenhum tipo de estabelecimento encontrado na área."))
                return
            else:
                # Abrir a janela de seleção de cozinha no thread principal
                self.root.after(0, lambda: self.select_cuisine_and_proceed(cuisine_counts))
        except Exception as e:
            logger.exception(f"Ocorreu um erro no método fetch_cuisines: {e}")
            self.root.after(0, lambda e=e: messagebox.showerror("Erro", f"Ocorreu um erro ao buscar estabelecimentos: {e}"))
        finally:
            # Reabilitar o botão e parar a barra de progresso
            self.root.after(0, lambda: self.run_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.message.set(""))

    def select_cuisine_and_proceed(self, cuisine_counts):
        selected_cuisine = self.select_cuisine(cuisine_counts)
        if selected_cuisine is None:
            messagebox.showinfo("Informação", "Nenhuma opção selecionada.")
            return
        else:
            self.cuisine = selected_cuisine
            self.preferences.preferences['cuisine'] = self.cuisine
            self.preferences.save_preferences()
            self.poi_finder.cuisine = self.cuisine

            # Prosseguir com o restante do processamento
            threading.Thread(target=self.after_fetch_cuisines).start()

    def select_cuisine_and_proceed_step2(self, cuisine_counts):
        selected_cuisine = self.select_cuisine(cuisine_counts)
        if selected_cuisine is None:
            messagebox.showinfo("Informação", "Nenhuma opção selecionada.")
            return
        else:
            self.cuisine = selected_cuisine
            self.preferences.preferences['cuisine'] = self.cuisine
            self.preferences.save_preferences()
            self.poi_finder.cuisine = self.cuisine

            # Prosseguir com o restante do processamento
            threading.Thread(target=self.after_fetch_cuisines).start()

    def after_fetch_cuisines(self):
        try:
            # Buscar POIs com a 'cuisine' selecionada
            self.poi_finder.get_pois()

            if not self.poi_finder.destination_nodes:
                self.root.after(0, lambda: messagebox.showwarning("Aviso", "Nenhum destino encontrado. Tente novamente com outros parâmetros."))
                return

            # Selecionar os destinos mais próximos
            self.selected_nodes, self.selected_names, self.selected_dists = self.select_closest_destinations()

            if not self.selected_nodes:
                self.root.after(0, lambda: messagebox.showwarning("Aviso", "Nenhum destino selecionado. Tente novamente."))
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
                logger.info(f"Tempo Médio {alg.replace('_', ' ').capitalize()}: {avg_time:.6f} segundos")
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

            # Salvar os resultados
            self.save_results()
            logger.info("Resultados salvos com sucesso.")

            self.root.after(0, lambda: self.message.set("Processamento concluído. O mapa foi aberto no navegador. Resultados salvos."))

        except Exception as e:
            logger.exception(f"Ocorreu um erro no método after_fetch_cuisines: {e}")
            self.root.after(0, lambda e=e: messagebox.showerror("Erro", f"Ocorreu um erro: {e}"))
        finally:
            # Reabilitar o botão e parar a barra de progresso
            self.root.after(0, lambda: self.run_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.progress.stop())

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

    def select_cuisine(self, cuisine_counts):
        """
        Exibe uma janela para o usuário selecionar uma 'cuisine' dentre as opções encontradas,
        mostrando a quantidade de estabelecimentos disponíveis para cada uma.
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

        # Ordenar as opções por nome
        cuisines_list = sorted(cuisine_counts.keys())

        # Inserir as opções no listbox com as quantidades
        for cuisine in cuisines_list:
            count = cuisine_counts[cuisine]
            listbox.insert(tk.END, f"{cuisine} ({count} estabelecimentos)")

        select_button = ttk.Button(top, text="Selecionar", command=on_select)
        select_button.pack(pady=5)

        self.root.wait_window(top)

        if selected_cuisine[0]:
            # Remover a parte da contagem para obter o nome da 'cuisine' selecionada
            selected_cuisine_name = selected_cuisine[0].split(' (')[0]
            return selected_cuisine_name
        else:
            return None

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



        # Informações do grafo
        self.graph_info_label = ttk.Label(main_frame, text="", justify=tk.LEFT)
        self.graph_info_label.grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=5)

        # Atualizar a configuração da grade
        main_frame.rowconfigure(7, weight=0)

    def save_results(self):
        """
        Salva os resultados em um arquivo CSV para análise posterior.
        """
        # Dados a serem salvos
        data = {
            'Endereço de Origem': self.origin_address,
            'Latitude': self.origin_point[0],
            'Longitude': self.origin_point[1],
            'Raio de Busca (m)': self.radius,
            'Tipo de Estabelecimento': self.cuisine,
            'Número de Vértices': self.graph_handler.G_projected.number_of_nodes(),
            'Número de Arestas': self.graph_handler.G_projected.number_of_edges(),
            'Densidade do Grafo': self.graph_handler.graph_density,
        }

        # Adicionar os tempos médios de cada algoritmo
        for alg in self.algorithms:
            alg_name = alg.replace('_', ' ').capitalize()
            avg_time = self.route_calculator.avg_times.get(alg, None)
            data[f'Tempo Médio {alg_name} (s)'] = avg_time

        # Criar um DataFrame com uma única linha
        df = pd.DataFrame([data])

        # Nome do arquivo CSV
        csv_file = 'resultados.csv'

        # Verificar se o arquivo já existe
        if os.path.isfile(csv_file):
            # Se existir, anexar sem escrever o cabeçalho
            df.to_csv(csv_file, mode='a', index=False, header=False)
        else:
            # Se não existir, criar e escrever o cabeçalho
            df.to_csv(csv_file, mode='w', index=False)

    def generate_report(self):
        # Desabilitar o botão durante o processamento
        self.report_button.config(state=tk.DISABLED)
        self.message.set("Gerando relatório...")

        try:
            analyzer = DataAnalyzer()
            analyzer.generate_report()
            messagebox.showinfo(
                "Sucesso",
                "Relatório gerado com sucesso.\nOs gráficos estão na pasta 'graficos' e a análise estatística em 'analise_estatistica.csv'."
            )
        except Exception as e:
            logger.exception(f"Erro ao gerar o relatório: {e}")
            messagebox.showerror("Erro", f"Ocorreu um erro ao gerar o relatório: {e}")
        finally:
            # Reabilitar o botão
            self.report_button.config(state=tk.NORMAL)
            self.message.set("")

