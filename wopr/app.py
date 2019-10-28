import os
import requests

from flask import (Flask, jsonify, request)
from flask_cors import CORS


app = Flask(__name__)
CORS(app)


ENV_TOKEN = 'TOKEN'
ENV_API = 'API'

WOPR = None


@app.route('/nodes', methods=['GET'])
def all_nodes():
    image_name = request.args.get('image', None)
    all_nodes = WOPR.get_nodes(image_name=image_name)
    return jsonify({'nodes': all_nodes})


class Wopr(object):

    def __init__(self):
        self.token = os.environ[ENV_TOKEN]
        self.api_host = os.environ[ENV_API]

    def get_nodes(self, image_name = None):
        # Load all of the nodes
        nodes = self._get('api/v1/nodes')
        all_nodes = self._parse_node_data(nodes)

        # Load all of the pods
        pods = self._get('api/v1/pods')
        self._merge_pods(all_nodes, pods, image_name)

        return all_nodes

    def _parse_node_data(self, data):
        nodes = []
        for node_data in data['items']:

            # Determine the node's role (worker or master)
            for l in node_data['metadata']['labels']:
                if l.startswith('node-role'):
                    node_role = l
                    break

            # Only process worker nodes
            if node_role != 'node-role.kubernetes.io/worker':
                continue

            # Build up the node details
            s = node_data['status']
            n = {
                'name': node_data['metadata']['name'],
                'os': s['nodeInfo']['operatingSystem'],
                'arch': s['nodeInfo']['architecture'],
                'capacity': {
                    'cpu': s['capacity']['cpu'],
                    'pods': s['capacity']['pods'],
                },
                'role': node_role,
                'pods': [],
            }

            for addy in s['addresses']:
                if addy['type'] == 'InternalIP':
                    n['ip'] = addy['address']

            nodes.append(n)

        return nodes

    @staticmethod
    def _merge_pods(nodes, pods, image_name):

        # Build lookup for nodes
        nodes_by_name = {}
        for node in nodes:
            nodes_by_name[node['name']] = node

        # Build up pod details
        for pod in pods['items']:
            p = {
                'name': pod['metadata']['name'],
                'image': pod['spec']['containers'][0]['image'],
                'phase': pod['status']['phase'],
            }

            # If there is an image filter, make sure the pod matches
            if image_name is None or image_name in p['image']:
                node_name = pod['spec']['nodeName']

                # Ignore pods not in the filtered set of nodes
                if node_name in nodes_by_name:
                    nodes_by_name[node_name]['pods'].append(p)


    def _get(self, path):
        url = self.api_host + path
        headers = {
            'Authorization': 'Bearer %s' % self.token
        }

        response = requests.get(url, headers=headers, verify=False)
        data = response.json()
        return data


if __name__ == '__main__':

    WOPR = Wopr()

    print('Connecting to cluster: %s' % WOPR.api_host)
    print('Using token: %s' % WOPR.token)

    app.run(debug=True)
