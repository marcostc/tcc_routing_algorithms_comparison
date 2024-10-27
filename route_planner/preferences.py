# route_planner/preferences.py

import json
import os

class UserPreferences:
    """
    Classe para gerenciar as preferências do usuário, como endereço, raio de busca,
    tipo de estabelecimento e número de destinos. As preferências são salvas em um
    arquivo JSON para serem persistidas entre sessões.
    """
    def __init__(self, filename='user_preferences.json'):
        self.filename = filename
        self.preferences = self.load_preferences()
        # Definir cores e estilos padrão se não existirem
        if 'visualization' not in self.preferences:
            self.preferences['visualization'] = self.default_visualization_preferences()

    def default_visualization_preferences(self):
        """
        Retorna um dicionário com as preferências de visualização padrão para cada algoritmo.
        """
        return {
            'dijkstra': {'color': 'green', 'style': 'solid'},
            'astar': {'color': 'purple', 'style': 'solid'},
            'bellman_ford': {'color': 'orange', 'style': 'solid'},
            'bidirectional_dijkstra': {'color': 'blue', 'style': 'solid'},
            'bidirectional_a_star': {'color': 'darkgreen', 'style': 'solid'}
        }

    def save_preferences(self):
        """
        Salva as preferências atuais no arquivo JSON especificado.
        """
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.preferences, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Erro ao salvar preferências: {e}")

    def load_preferences(self):
        """
        Carrega as preferências do arquivo JSON especificado.
        """
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    preferences = json.load(f)
                return preferences
            except Exception as e:
                print(f"Erro ao carregar preferências: {e}")
                return {}
        else:
            return {}

    def get_user_input(self, address, radius, cuisine, num_destinations):
        """
        Atualiza as preferências do usuário com os valores fornecidos.

        Args:
            address (str): Endereço de origem.
            radius (int): Raio de busca em metros.
            cuisine (str): Tipo de estabelecimento.
            num_destinations (int): Número de destinos mais próximos.

        Returns:
            tuple: Valores atualizados das preferências.
        """
        self.preferences['address'] = address
        self.preferences['radius'] = radius
        self.preferences['cuisine'] = cuisine
        self.preferences['num_destinations'] = num_destinations
        return address, radius, cuisine, num_destinations
