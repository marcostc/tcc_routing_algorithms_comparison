# proj/app/services.py

import time
import os
import psycopg2
import folium
from geopy.geocoders import Nominatim

class ShortestPathTester:
    def __init__(self):
        db_config = {
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASS'),
            'host': os.getenv('DB_HOST', 'db'),
            'port': 5432
        }
        self.connection = psycopg2.connect(**db_config)
        self.geolocator = Nominatim(user_agent="route_app")

    def geocode_address(self, address):
        location = self.geolocator.geocode(address)
        return (location.latitude, location.longitude) if location else None

    def get_nearest_node(self, lat, lon):
        query = """
        SELECT id FROM ways_vertices_pgr
        ORDER BY the_geom <-> ST_SetSRID(ST_Point(%s, %s), 4326) LIMIT 1;
        """
        cursor = self.connection.cursor()
        cursor.execute(query, (lon, lat))
        node_id = cursor.fetchone()[0]
        cursor.close()
        return node_id

    def get_pizza_restaurants(self, num_destinations):
        query = """
        SELECT id, ST_Y(the_geom) AS lat, ST_X(the_geom) AS lon
        FROM ways_vertices_pgr
        WHERE id IN (
            SELECT source FROM ways
            WHERE cuisine = 'pizza'
        )
        LIMIT %s;
        """
        cursor = self.connection.cursor()
        cursor.execute(query, (num_destinations,))
        results = cursor.fetchall()
        cursor.close()
        return results

    def calculate_route(self, algorithm, source, targets):
        routes = []
        total_time = 0

        for target in targets:
            start_time = time.time()
            query = self.build_query(algorithm, source, target[0])
            cursor = self.connection.cursor()
            cursor.execute(query)
            path = cursor.fetchall()
            cursor.close()
            end_time = time.time()

            routes.append((path, target[1], target[2]))  # path, lat, lon
            total_time += (end_time - start_time)

        return routes, total_time

    def build_query(self, algorithm, source, target):
        if algorithm == 'dijkstra':
            function = 'pgr_dijkstra'
        elif algorithm == 'astar':
            function = 'pgr_astar'
        elif algorithm == 'bellman_ford':
            function = 'pgr_bellmanFord'
        else:
            raise ValueError("Algoritmo inválido.")

        query = f"""
        SELECT * FROM {function}(
            'SELECT id, source, target, cost, reverse_cost FROM ways',
            {source}, {target}, directed := true
        );
        """
        return query

    def generate_map(self, routes, source_coords):
        m = folium.Map(location=source_coords, zoom_start=13)
        folium.Marker(location=source_coords, icon=folium.Icon(color='green'), popup='Origem').add_to(m)

        for path, lat, lon in routes:
            lat_lngs = []
            for row in path:
                edge_id = row[2]  # Assuming 'edge' is the third column
                geom_query = "SELECT ST_AsGeoJSON(the_geom) FROM ways WHERE id = %s;"
                cursor = self.connection.cursor()
                cursor.execute(geom_query, (edge_id,))
                geom = cursor.fetchone()[0]
                cursor.close()
                coords = folium.GeoJson(geom).data['geometry']['coordinates']
                if isinstance(coords[0], list):
                    coords = coords
                else:
                    coords = [coords]
                lat_lngs.extend([[coord[1], coord[0]] for coord in coords])

            folium.PolyLine(lat_lngs, color="blue", weight=2.5, opacity=1).add_to(m)
            folium.Marker(location=[lat, lon], icon=folium.Icon(color='red'), popup='Destino').add_to(m)

        return m

    def close(self):
        self.connection.close()
