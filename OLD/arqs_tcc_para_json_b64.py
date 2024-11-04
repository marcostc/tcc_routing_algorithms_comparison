import base64
import json
import os

# Diretório dos arquivos Python
diretorio = 'caminho/para/seus/arquivos'

# Lista de arquivos
arquivos = [
    '__init__.py',
    'main.py',
    'gui.py',
    'preferences.py',
    'geocoder.py',
    'graph_handler.py',
    'poi_finder.py',
    'route_calculator.py',
    'route_plotter.py',
    'customization_window.py',
    'utils.py'
]

projeto = {
    "projeto": {
        "nome": "Comparação de algoritmos de traçado do caminho mínimo",
        "visao_geral": "Desenvolver uma aplicação para comparar o desempenho temporal de algoritmos performáticos no traçado de rotas com o caminho mínimo, considerando a complexidade temporal teórica prevista para cada um dos algoritmos",
        "arquivos": {},
        "decisoes": [
            "Divisão do arquivo tcc_poo.py em módulos específicos para melhor organização e manutenção.",
            "Implementação da interface gráfica usando Tkinter.",
            "Uso do módulo Geocoder para geolocalização de endereços."
        ],
        "roadmap": {
            "historico": "O projeto começou como tcc_poo.py e foi subdividido em múltiplos módulos.",
            "proximas_etapas": [
                "Adicionar funcionalidade de salvamento de rotas em JSON.",
                "Implementar testes automatizados para cada módulo.",
                "Integrar API de mapas para melhorar precisão das rotas.",
                "Desenvolver documentação detalhada do projeto."
            ]
        }
    }
}

# Codificar arquivos em Base64
for arquivo in arquivos:
    caminho = os.path.join(diretorio, arquivo)
    with open(caminho, 'rb') as f:
        conteudo = f.read()
        conteudo_base64 = base64.b64encode(conteudo).decode('utf-8')
        projeto['projeto']['arquivos'][arquivo] = conteudo_base64

# Converter para JSON minificado
json_minificado = json.dumps(projeto, separators=(',', ':'))

# Salvar em um arquivo JSON
with open('projeto_compactado.json', 'w', encoding='utf-8') as f:
    f.write(json_minificado)

print("Projeto compactado com sucesso em 'projeto_compactado.json'")
