import argparse
import os
import requests
import sys
import yaml

from flask import (Flask, jsonify, request)
from flask_cors import CORS

# Suppress the insecure warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Suppress chatty flask logging
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


app = Flask(__name__)
CORS(app)


ENV_TOKEN = 'TOKEN'
ENV_API = 'API'
ENV_IMAGE_FILTER = 'IMAGE_FILTER'
ENV_HIDE_SUCCEEDED = 'HIDE_SUCCEEDED'
ENV_FILTER_WORKER_NODES = 'FILTER_WORKER_NODES'

# Name of the holder for all pending pods that don't have a node yet
UNSCHEDULED = 'Unscheduled'

WOPR = None


@app.route('/nodes', methods=['GET'])
def all_nodes():
    # Temporarily disabling this as a query parameter
    # image_name = request.args.get('image', None)

    all_nodes = WOPR.get_nodes()
    return jsonify({'nodes': all_nodes})


class Wopr(object):

    def __init__(self, config_filepath):
        self.token = os.environ[ENV_TOKEN]
        self.api_host = os.environ[ENV_API]
        self.image_filter = os.environ.get(ENV_IMAGE_FILTER, None)
        self.hide_succeeded = os.environ.get(ENV_HIDE_SUCCEEDED, False)
        self.filter_worker_nodes = os.environ.get(ENV_FILTER_WORKER_NODES, False)

        self.load_config(config_filepath)

    def load_config(self, filepath):
        if not filepath:
            return

        with open(filepath, 'r') as stream:
            c = yaml.safe_load(stream)

            self.token = c.get(ENV_TOKEN.lower(), self.token)
            self.api_host = c.get(ENV_API.lower(), self.api_host)
            self.image_filter = c.get(ENV_IMAGE_FILTER.lower(), self.image_filter)
            self.hide_succeeded = c.get(ENV_HIDE_SUCCEEDED.lower(), self.hide_succeeded)
            self.filter_worker_nodes = c.get(ENV_FILTER_WORKER_NODES.lower(), self.filter_worker_nodes)

    def print_status(self):
        print('==================================')
        print('Host:           %s' % self.api_host)
        print('Image:          %s' % self.image_filter)
        print('Hide Succeeded: %s' % self.hide_succeeded)
        print('Filter Workers: %s' % self.filter_worker_nodes)
        print('Token:          %s' % (self.token != None))
        print('==================================')

    def get_nodes(self):
        # Load all of the nodes
        nodes = self._get('api/v1/nodes')
        all_nodes = self._parse_node_data(nodes)

        # Load all of the pods
        pods = self._get('api/v1/pods')
        self._merge_pods(all_nodes, pods)

        # Sort the list of pods in each node
        for n in all_nodes:
            self._sort_pods(n['pods'])

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
            if self.filter_worker_nodes and node_role != 'node-role.kubernetes.io/worker':
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

        # Add a holder for unscheduled nodes
        n = {
            'name': UNSCHEDULED,
            'os': '',
            'arch': '',
            'ip': '',
            'pods': [],
        }
        nodes.append(n)

        return nodes

    def _merge_pods(self, nodes, pods):

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

            # For pending pods that don't have a viable node, this will be empty
            if 'nodeName' not in pod['spec']:
                node_name = UNSCHEDULED
            else:
                node_name = pod['spec']['nodeName']

            # If there is an image filter, make sure the specified image
            # string is present in the pod's image name
            if self.image_filter is not None and \
               self.image_filter not in p['image']:
                continue

            # Ignore pods not in the filtered  set of nodes
            if node_name not in nodes_by_name:
                continue

            # Check to see if completed pods are filtered out
            if self.hide_succeeded and p['phase'] == 'Succeeded':
                continue

            # This is ugly, but there's a small race condition where
            # the pods are on a node but the node list doesn't show the node
            # yet.
            if node_name not in nodes_by_name:
                n = {
                    'name': node_name,
                    'os': 'Unknown',
                    'arch': 'Unknown',
                    'capacity': {
                        'cpu': 'Unknown',
                        'pods': 'Unknown',
                    },
                    'role': 'node-role.kubernetes.io/worker',
                    'ip': 'Unknown',
                    'pods': [],
                }
                nodes.append(n)
                nodes_by_name[node_name] = n

            nodes_by_name[node_name]['pods'].append(p)

    @staticmethod
    def _sort_pods(pods):
        # The order should be Pending, Running, Succeeded
        # (which luckily is alphabetical)
        def sort_by_phase(p):
            return p['phase']

        pods.sort(key = sort_by_phase)

    def _get(self, path):
        url = self.api_host + path
        headers = {
            'Authorization': 'Bearer %s' % self.token
        }

        response = requests.get(url, headers=headers, verify=False)
        data = response.json()
        return data


def parse_args(args):
    parser = argparse.ArgumentParser(
        description='Command line interface to the WOPR Backend',
        add_help=False
    )

    parser.add_argument('-c', '--config',
                        dest='config',
                        action='store',
                        help='path to the configuration file to use')

    return parser.parse_args(args)


if __name__ == '__main__':

    parsed = parse_args(sys.argv[1:])

    WOPR = Wopr(parsed.config)
    WOPR.print_status()

    app.run(debug=True)
