# route_planner/route_plotter.py

import os
import webbrowser
import folium
from folium.plugins import PolyLineTextPath

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
                    PolyLineTextPath(
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
