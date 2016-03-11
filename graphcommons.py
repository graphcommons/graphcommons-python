from requests.api import request
from itertools import chain


def extend(base, name=None, **kwargs):
    return type(name, (base,), kwargs)


class Entity(dict):
    __getattr__ = dict.get

    def __repr__(self):
        printable = self.name or self.id

        if not printable:
            return super(Entity, self).__repr__()

        return '%s: %s' % (
            self.__class__.__name__,
            printable.encode("utf-8")
        )


Signal = extend(Entity, 'Signal')
Path = extend(Entity, 'Path')


class Edge(Entity):

    def to_signal(self, action, graph):
        # signal types: create or update
        action = "edge_%s" % action

        from_id, to_id = map(self.get, ('from', 'to'))
        from_node = graph.get_node(from_id)
        to_node = graph.get_node(to_id)
        kwargs = dict(action=action,
                      name=self.edge_type,
                      from_name=from_node.name,
                      from_type=from_node.type,
                      to_name=to_node.name,
                      to_type=to_node.type,
                      reference=self.get('reference', None),
                      weight=self.get('weight'),
                      properties=self.properties)
        return Signal(**kwargs)


class Node(Entity):

    def to_signal(self, action, graph):
        # signal types: create or update
        action = "node_%s" % action
        kwargs = dict(action=action,
                      name=self.name,
                      type=self.type['name'],
                      reference=self.reference,
                      image=self.image,
                      color=self.type['color'],
                      url=self.url,
                      description=self.description,
                      properties=self.properties)
        return Signal(**kwargs)


class EdgeType(Entity):

    def to_signal(self, action):
        action = "edgetype_%s" % action
        kwargs = dict(action=action)
        kwargs.update(dict((k, self.get(k, None)) for k in ['name', 'color', 'name_alias', 'weighted',
                                                            'properties', 'image_as_icon', 'image']))
        return Signal(**kwargs)


class NodeType(Entity):

    def to_signal(self, action):
        action = "nodetype_%s" % action
        kwargs = dict(action=action)
        kwargs.update(dict((k, self.get(k, None)) for k in ['name', 'color', 'name_alias', 'size_limit',
                                                            'properties', 'image_as_icon', 'image', 'size']))
        return Signal(**kwargs)


class Graph(Entity):
    def __init__(self, *args, **kwargs):
        super(Graph, self).__init__(*args, **kwargs)
        self.edges = map(Edge, self.edges or [])
        self.nodes = map(Node, self.nodes or [])
        self.node_types = map(NodeType, self.nodeTypes or [])
        self.edge_types = map(EdgeType, self.edgeTypes or [])

        # hash for quick search
        self._edges = dict((edge.id, edge) for edge in self.edges)
        self._nodes = dict((node.id, node) for node in self.nodes)
        self._node_types = dict((t.id, t) for t in self.node_types)
        self._edge_types = dict((t.id, t) for t in self.edge_types)

    def get_node(self, node_id):
        return self._nodes.get(node_id, None)

    def get_edge_type(self, edge_type_id):
        return self._edge_types.get(edge_type_id, None)

    def get_node_type(self, node_type_id):
        return self._node_types.get(node_type_id, None)

    def edges_for(self, node, direction):
        if isinstance(node, basestring):
            node = self.get_node(node)

        return [edge for edge in self.edges
                if edge[direction] == node.id]

    def edges_from(self, node):
        return self.edges_for(node, 'from')

    def edges_to(self, node):
        return self.edges_for(node, 'to')


class GraphCommonsException(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code

        if isinstance(message, unicode):
            message = message.encode("utf-8")  # Otherwise, it will not be printed.

        self.message = message

    def __str__(self):
        return self.message


class GraphCommons(object):
    BASE_URL = "https://graphcommons.com/api/v1"
    ERROR_CODES = [400, 401, 403, 404, 405, 500]

    def __init__(self, api_key, base_url=None):
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL

    def build_url(self, endpoint, id=None):
        parts = filter(bool, [self.base_url, endpoint, id])
        return '/'.join(parts)

    @staticmethod
    def get_error_message(response):
        try:
            bundle = response.json()
        except (ValueError, TypeError):
            return response.content
        return bundle['msg']

    def make_request(self, method, endpoint, data=None, id=None):
        response = request(method, self.build_url(endpoint, id), json=data,
                           headers={"Authentication": self.api_key,
                                    "Content-Type": "application/json"
                                    }
                           )

        if response.status_code in self.ERROR_CODES:
            raise GraphCommonsException(status_code=response.status_code,
                                        message=GraphCommons.get_error_message(response))

        return response

    def status(self):
        response = self.make_request('get', 'status')
        return Entity(**response.json())

    def graphs(self, id=None):
        response = self.make_request('get', 'graphs', id=id)
        return Graph(**response.json()['graph'])

    def nodes(self, id=None):
        response = self.make_request('get', 'nodes', id=id)
        return Node(**response.json()['node'])

    def new_graph(self, signals=None, **kwargs):
        if signals is not None:
            kwargs['signals'] = map(dict, signals)
        response = self.make_request('post', 'graphs', data=kwargs)
        return Graph(**response.json()['graph'])

    def update_graph(self, id, signals=None, **kwargs):
        if signals is not None:
            kwargs['signals'] = map(dict, signals)
        endpoint = 'graphs/%s/add' % id
        response = self.make_request('put', endpoint, data=kwargs)
        return Graph(**response.json()['graph'])

    def clear_graph(self, graph_id):
        graph = self.graphs(graph_id)
        # Remove all nodes. (This also removes all edges.)
        signals = map(lambda node: dict(action="node_delete", id=node.id), graph.nodes)
        endpoint = "graphs/{}/add".format(graph_id)
        kwargs = dict(signals=signals)
        response = self.make_request("put", endpoint, data=kwargs)
        return Graph(**response.json()['graph'])

    def create_graph_from_path(self, name, paths, base_graph):

        kwargs = dict((k, base_graph.get(k, None)) for k in ['status', 'license', 'users', 'layout'])
        kwargs['name'] = name
        subtitle = ""
        description = ""
        edges = []
        nodes = []
        edge_type_ids = []
        node_type_ids = []
        for path in paths:
            description = u"{}\n{}".format(description, path.path_string)
            subtitle = u"{}\n{}".format(subtitle, path.path_string)

            # Type ids
            edge_type_ids.extend([edge.type_id for edge in path.edges])
            node_type_ids.extend([node.type['id'] for node in path.nodes])

            edges.extend(path.edges)
            nodes.extend(path.nodes)

        # Add explanation of original graph.
        kwargs['description'] = u"{}\n{}".format(description, base_graph.description)
        kwargs['subtitle'] = u"{}\n{}".format(subtitle, base_graph.subtitle)

        # Get edge_types by using their ids.
        edge_types = map(base_graph.get_edge_type, set(edge_type_ids))
        node_types = map(base_graph.get_node_type, set(node_type_ids))

        # Add node and edge type Signals first.
        signals = map(lambda entity: entity.to_signal('create'), chain(node_types, edge_types))

        edge_ids = set()
        node_ids = set()

        # Remove duplicates for efficiency in graph creation.
        edges = [e for e in edges if not (e.id in edge_ids or edge_ids.add(e.id))]
        nodes = [n for n in nodes if not (n.id in node_ids or node_ids.add(n.id))]

        # Add node and edge Signals.
        signals.extend(map(lambda entity: entity.to_signal('create', base_graph), chain(edges, nodes)))
        return self.new_graph(signals=signals, **kwargs)

    def paths(self, graph_id, kwargs):
        end_point = 'graphs/%s/paths' % graph_id
        response = self.make_request("get", end_point, data=kwargs).json()
        edges = response['edges']
        nodes = response['nodes']
        paths = []
        for path in response['paths']:
            p = {'edges': map(Edge, (edges[edge_id] for edge_id in path['edges'])),
                 'nodes': map(Node, (nodes[node_id] for node_id in path['nodes'])), 'dirs': path['dirs'],
                 'path_string': path['path_string']}
            paths.append(Path(**p))
        return paths
