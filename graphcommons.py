from requests.api import request


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


Edge = extend(Entity, 'Edge')
Node = extend(Entity, 'Node')
EdgeType = extend(Entity, 'EdgeType')
NodeType = extend(Entity, 'NodeType')
Signal = extend(Entity, 'Signal')


class Graph(Entity):
    def __init__(self, *args, **kwargs):
        super(Graph, self).__init__(*args, **kwargs)
        self.edges = map(Edge, self.edges or [])
        self.nodes = map(Node, self.nodes or [])
        self.node_types = map(Node, self.nodeTypes or [])
        self.edge_types = map(Node, self.edgeTypes or [])

    def get_node(self, id):
        for node in self.nodes:
            if node.id == id:
                return node

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

    def get_error_message(self, response):
        try:
            bundle = response.json()
        except (ValueError, TypeError):
            return response.content
        return bundle['msg']

    def make_request(self, method, endpoint, data=None, id=None):
        response = request(
            method,
            self.build_url(endpoint, id),
            json=data,
            headers={
                "Authentication": self.api_key,
                "Content-Type": "application/json"
            }
        )

        if response.status_code in self.ERROR_CODES:
            raise GraphCommonsException(
                status_code=response.status_code,
                message=self.get_error_message(response)
            )

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
