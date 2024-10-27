# tests/test_preferences.py

import unittest
import os
from route_planner.preferences import UserPreferences

class TestUserPreferences(unittest.TestCase):
    def setUp(self):
        # Usar um arquivo de preferências temporário para testes
        self.test_filename = 'test_user_preferences.json'
        self.preferences = UserPreferences(filename=self.test_filename)

    def tearDown(self):
        # Remover o arquivo de preferências de teste após os testes
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)

    def test_default_visualization_preferences(self):
        default_prefs = self.preferences.default_visualization_preferences()
        self.assertIn('dijkstra', default_prefs)
        self.assertEqual(default_prefs['dijkstra']['color'], 'green')

    def test_save_and_load_preferences(self):
        self.preferences.get_user_input('Endereço Teste', 1000, 'pizza', 5)
        self.preferences.save_preferences()

        # Criar uma nova instância para carregar as preferências salvas
        new_preferences = UserPreferences(filename=self.test_filename)
        self.assertEqual(new_preferences.preferences['address'], 'Endereço Teste')
        self.assertEqual(new_preferences.preferences['radius'], 1000)
        self.assertEqual(new_preferences.preferences['cuisine'], 'pizza')
        self.assertEqual(new_preferences.preferences['num_destinations'], 5)

if __name__ == '__main__':
    unittest.main()
