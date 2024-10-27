# route_planner/customization_window.py

import tkinter as tk
from tkinter import ttk, messagebox

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
