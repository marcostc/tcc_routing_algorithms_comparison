# route_planner/preferences.py

import json
import os

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
