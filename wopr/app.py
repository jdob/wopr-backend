import os
import requests

from flask import (Flask, jsonify, request)
from flask_cors import CORS


app = Flask(__name__)
CORS(app)


ENV_TOKEN = 'TOKEN'
ENV_API = 'API'


@app.route('/nodes', methods=['GET'])
def all_nodes():

    # Load all of the nodes
    nodes = _get('api/v1/nodes')
    all_nodes = _parse_node_data(nodes)

    # Load all of the pods
    pods = _get('api/v1/pods')
    image_name = request.args.get('image', None)
    _merge_pods(all_nodes, pods, image_name)

    return jsonify({'nodes': all_nodes})


def _parse_node_data(data):

    nodes = []
    for node_data in data['items']:
        s = node_data['status']

        n = {
            'name': node_data['metadata']['name'],
            'os': s['nodeInfo']['operatingSystem'],
            'arch': s['nodeInfo']['architecture'],
            'capacity': {
                'cpu': s['capacity']['cpu'],
                'pods': s['capacity']['pods'],
            },
            'pods': [],
        }

        for addy in s['addresses']:
            print(addy)
            if addy['type'] == 'InternalIP':
                n['ip'] = addy['address']

        nodes.append(n)
    return nodes


def _merge_pods(nodes, pods, image_name):
    nodes_by_name = {}
    for node in nodes:
        nodes_by_name[node['name']] = node

    for pod in pods['items']:
        p = {
            'name': pod['metadata']['name'],
            'image': pod['spec']['containers'][0]['image'],
        }

        if image_name is None or image_name in p['image']:
            node_name = pod['spec']['nodeName']
            nodes_by_name[node_name]['pods'].append(p)


def _get(path):

    url = _api() + path
    headers = {
        'Authorization': 'Bearer %s' % _token()
    }

    response = requests.get(url,
                            headers=headers,
                            verify=False)
    data = response.json()
    return data


def _token():
    return os.environ[ENV_TOKEN]


def _api():
    return os.environ[ENV_API]


if __name__ == '__main__':
    print('Connecting to cluster: %s' % _api())
    print('Using token: %s' % _token())

    app.run(debug=True)
