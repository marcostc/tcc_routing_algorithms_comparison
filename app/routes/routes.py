# proj/app/routes/routes.py

import os
from flask import Blueprint, render_template, request
from app.services import ShortestPathTester

main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # ... obter dados do formulário
        tester = ShortestPathTester()
        address = request.form['address']
        num_destinations = int(request.form['num_destinations'])
        algorithm = request.form['algorithm']
        source_coords = tester.geocode_address(address)
        if not source_coords:
            return "Endereço de origem inválido.", 400

        source_node = tester.get_nearest_node(*source_coords)

        # Obter restaurantes de pizza
        targets = tester.get_pizza_restaurants(num_destinations)

        routes, total_time = tester.calculate_route(algorithm, source_node, targets)
        map_object = tester.generate_map(routes, source_coords)
        tester.close()

        map_html = map_object._repr_html_()

        return render_template('index.html', map_html=map_html, total_time=total_time)
    else:
        return render_template('index.html')
