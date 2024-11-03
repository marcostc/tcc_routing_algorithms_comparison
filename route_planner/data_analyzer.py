# route_planner/data_analyzer.py

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr
import os

class DataAnalyzer:
    def __init__(self, csv_file='resultados.csv'):
        self.csv_file = csv_file
        self.data = None
        self.algorithms = ['Dijkstra', 'Astar', 'Bellman ford', 'Bidirectional dijkstra', 'Bidirectional a star']

    def load_data(self):
        if os.path.isfile(self.csv_file):
            self.data = pd.read_csv(self.csv_file)
        else:
            print(f"O arquivo {self.csv_file} não foi encontrado.")
            return False
        return True

    def generate_plots(self):
        if self.data is None:
            print("Os dados não foram carregados.")
            return

        # Configurar o estilo dos gráficos
        sns.set(style='whitegrid')

        # Variáveis independentes
        x_vars = ['Número de Vértices', 'Número de Arestas', 'Densidade do Grafo']

        for alg in self.algorithms:
            alg_col = f'Tempo Médio {alg} (s)'

            for x_var in x_vars:
                plt.figure(figsize=(8, 6))

                # Scatterplot com linha de tendência
                sns.regplot(
                    data=self.data,
                    x=x_var,
                    y=alg_col,
                    ci=None,  # Não mostrar intervalo de confiança
                    scatter_kws={'s': 50, 'alpha': 0.7},  # Personalizar pontos
                    line_kws={'color': 'red'}  # Personalizar linha de tendência
                )

                plt.title(f'{alg} - Tempo de Execução vs {x_var}')
                plt.xlabel(x_var)
                plt.ylabel('Tempo de Execução (s)')
                plt.legend([f'Linha de Tendência'], loc='upper left')

                # Ajustar os eixos se necessário
                plt.tight_layout()

                # Salvar o gráfico
                filename = f'graficos/{alg}_{x_var.replace(" ", "_")}.png'
                os.makedirs('graficos', exist_ok=True)
                plt.savefig(filename)
                plt.close()
                print(f'Gráfico salvo: {filename}')


    def perform_statistical_analysis(self):
        if self.data is None:
            print("Os dados não foram carregados.")
            return

        results = []

        # Variáveis independentes
        x_vars = ['Número de Vértices', 'Número de Arestas', 'Densidade do Grafo']

        for alg in self.algorithms:
            alg_col = f'Tempo Médio {alg} (s)'

            for x_var in x_vars:
                x = self.data[x_var]
                y = self.data[alg_col]

                # Remover valores NaN
                valid_indices = ~(x.isna() | y.isna())
                x_valid = x[valid_indices]
                y_valid = y[valid_indices]

                if len(x_valid) > 1:
                    # Cálculo da correlação de Pearson
                    corr_coef, p_value = pearsonr(x_valid, y_valid)

                    # Ajuste de regressão linear simples
                    slope, intercept = self.linear_regression(x_valid, y_valid)

                    result = {
                        'Algoritmo': alg,
                        'Variável Independente': x_var,
                        'Coeficiente de Correlação': corr_coef,
                        'P-Valor': p_value,
                        'Inclinação (Slope)': slope,
                        'Intercepto': intercept
                    }
                    results.append(result)
                else:
                    print(f"Dados insuficientes para {alg} com {x_var}")

        # Criar um DataFrame com os resultados
        results_df = pd.DataFrame(results)

        # Salvar os resultados em um arquivo CSV
        results_df.to_csv('analise_estatistica.csv', index=False)
        print("Análise estatística salva em 'analise_estatistica.csv'.")

    def linear_regression(self, x, y):
        # Ajuste de regressão linear simples usando numpy
        import numpy as np
        slope, intercept = np.polyfit(x, y, 1)
        return slope, intercept

    def generate_comparative_plots(self):
        if self.data is None:
            print("Os dados não foram carregados.")
            return

        # Configurar o estilo dos gráficos
        sns.set(style='whitegrid')

        # Variáveis independentes
        x_vars = ['Número de Vértices', 'Número de Arestas']

        for x_var in x_vars:
            plt.figure(figsize=(10, 6))

            # Plotar as curvas de cada algoritmo
            for alg in self.algorithms:
                alg_col = f'Tempo Médio {alg} (s)'

                # Ordenar os dados com base na variável independente
                sorted_data = self.data.sort_values(by=x_var)

                # Remover valores NaN
                x = sorted_data[x_var].values
                y = sorted_data[alg_col].values
                valid_indices = ~(np.isnan(x) | np.isnan(y))
                x = x[valid_indices]
                y = y[valid_indices]

                plt.plot(x, y, marker='o', label=alg)

            plt.title(f'Tempo de Execução dos Algoritmos vs {x_var}')
            plt.xlabel(x_var)
            plt.ylabel('Tempo de Execução (s)')
            plt.legend()
            plt.tight_layout()

            # Salvar o gráfico
            filename = f'graficos/Comparativo_{x_var.replace(" ", "_")}.png'
            os.makedirs('graficos', exist_ok=True)
            plt.savefig(filename)
            plt.close()
            print(f'Gráfico comparativo salvo: {filename}')

    def generate_report(self):
        # Carregar os dados
        if not self.load_data():
            return

        # Gerar gráficos individuais
        self.generate_plots()

        # Gerar gráficos comparativos
        self.generate_comparative_plots()

        # Gerar o gráfico 3D
        self.generate_3d_plot()

        # Realizar análise estatística
        self.perform_statistical_analysis()

        # TODO: implementar a geração de um relatório consolidado, se desejado

    def generate_3d_plot(self):
        if self.data is None:
            print("Os dados não foram carregados.")
            return

        # Configurar o estilo dos gráficos
        sns.set(style='whitegrid')

        # Remover valores NaN e preparar os dados
        valid_data = self.data.dropna(subset=['Número de Vértices', 'Número de Arestas'])
        V = valid_data['Número de Vértices'].values
        E = valid_data['Número de Arestas'].values

        # Criar uma figura 3D
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')

        # Escolher um conjunto de cores para os algoritmos
        colors = plt.cm.get_cmap('tab10', len(self.algorithms))

        # Plotar os tempos de execução para cada algoritmo
        for idx, alg in enumerate(self.algorithms):
            alg_col = f'Tempo Médio {alg} (s)'
            T = valid_data[alg_col].values

            # Verificar se há valores NaN nos tempos de execução
            valid_indices = ~np.isnan(T)
            V_valid = V[valid_indices]
            E_valid = E[valid_indices]
            T_valid = T[valid_indices]

            # Plotar os pontos 3D
            ax.scatter(V_valid, E_valid, T_valid, color=colors(idx), label=alg, s=50)

        # Configurações do gráfico
        ax.set_title('Tempos de Execução dos Algoritmos em Função de Vértices e Arestas')
        ax.set_xlabel('Número de Vértices')
        ax.set_ylabel('Número de Arestas')
        ax.set_zlabel('Tempo de Execução (s)')
        ax.legend()

        plt.tight_layout()

        # Salvar o gráfico
        filename = 'graficos/Tempos_Execucao_3D.png'
        os.makedirs('graficos', exist_ok=True)
        plt.savefig(filename)
        plt.close()
        print(f'Gráfico 3D salvo: {filename}')

