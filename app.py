import requests

from flask import (Flask, jsonify, request)
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


# Horribly ghetto, but temporary
TOKEN = 'eyJhbGciOiJSUzI1NiIsImtpZCI6IjV6VHRjR3lOZy1rRzgzZDdQbnRUaWE4TU9EeDNPVlM4dGpsWVNmbndhNTAifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6IndvcHItdG9rZW4td3h3eHQiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoid29wciIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6IjA2ODU2ZTUyLWQxNWQtNGU3NC05M2Y3LWExNzIyMzAyY2FkNCIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OndvcHIifQ.wm_c0ViJIi0cPvqms7kF8GxZOwhROTJgslI9fzeJN1BzUT-14ZQQNQFpSQAU8deF1jmwpkBsvxaf8lKlF3oBV3XdmzVZeDSQdCO8KZ1y-SUzTdF7rkI9vi0IPJfI9jEE-VAXY1FMdyKGz_OqwzitAXkFBWwSB1bmmzUWsHpX3qeh-ryg-A8fPBTBKolJK81WdVWAr0UBBleoA4XUIISqUDA4afdqrQYlv4a3FTlw-elqdsw5Wep979CE0wt7J-g92zgGfiddERl_nM8vHWZYR2neKCsDNBCy4eLCQQf0dXPBgxqSFPfRjR6P0L5mGrAa3NlmXCw-17kOy4Bo8gJ_kA'


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
    url = 'https://192.168.99.100:8443/' + path
    headers = {
        'Authorization': 'Bearer %s' % TOKEN
    }

    response = requests.get(url,
                            headers=headers,
                            verify=False)
    data = response.json()
    return data


if __name__ == '__main__':
    app.run(debug=True)