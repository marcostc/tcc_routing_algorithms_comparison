# route_planner/route_calculator.py

import time
import heapq
import networkx as nx

from .utils import timed
from .logger import logger

class RouteCalculator:
    """
    Classe para calcular rotas entre o nó de origem e os nós de destino utilizando
    diferentes algoritmos de caminho mínimo.
    """
    def __init__(self, G_projected, origin_node, destination_nodes):
        self.G_projected = G_projected
        self.origin_node = origin_node
        self.destination_nodes = destination_nodes
        self.routes = {}
        self.avg_times = {}

    @timed
    def calculate_routes(self, algorithms):
        """
        Calcula rotas para todos os destinos utilizando os algoritmos especificados.

        Args:
            algorithms (list): Lista de strings com os nomes dos algoritmos a serem utilizados.
        """
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
                            heuristic=lambda u, v: ((self.G_projected.nodes[u]['x'] - self.G_projected.nodes[v]['x'])**2 + 
                                                    (self.G_projected.nodes[u]['y'] - self.G_projected.nodes[v]['y'])**2) ** 0.5
                        )
                    elif alg == 'bellman_ford':
                        route = nx.bellman_ford_path(self.G_projected, self.origin_node, target, weight='length')
                    elif alg == 'bidirectional_dijkstra':
                        path = nx.bidirectional_dijkstra(self.G_projected, self.origin_node, target, weight='length')[1]
                        route = path
                    elif alg == 'bidirectional_a_star':
                        heuristic = lambda u, v: ((self.G_projected.nodes[u]['x'] - self.G_projected.nodes[v]['x'])**2 + 
                                                  (self.G_projected.nodes[u]['y'] - self.G_projected.nodes[v]['y'])**2) ** 0.5
                        route = self.bidirectional_a_star(self.G_projected, self.origin_node, target, heuristic)
                    else:
                        raise ValueError("Algoritmo não suportado.")
                    end_time = time.time()
                    self.routes[alg].append(route)
                    times[alg].append(end_time - start_time)
                except nx.NetworkXNoPath:
                    logger.warning(f"Nenhuma rota encontrada para o nó {target} usando {alg}.")
                except Exception as e:
                    logger.exception(f"Erro ao calcular rota para o nó {target} usando {alg}")

        self.avg_times = {alg: (sum(times[alg]) / len(times[alg]) if times[alg] else 0) for alg in algorithms}

    @staticmethod
    def bidirectional_a_star(G, source, target, heuristic):
        """
        Implementação personalizada do algoritmo Bidirectional A*.

        Args:
            G (networkx.DiGraph): Grafo direcionado.
            source (int): Nó de origem.
            target (int): Nó de destino.
            heuristic (function): Função heurística que estima a distância entre dois nós.

        Returns:
            list: Lista de nós que representa o caminho encontrado.

        Raises:
            nx.NetworkXNoPath: Se não houver caminho entre source e target.
        """
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
