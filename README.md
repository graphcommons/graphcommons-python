### Python Wrapper For Graph Commons API.

More detailed API documentation:

<http://graphcommons.github.io/api-v1/>

### Installation

```
pip install graphcommons
```

### Usage

#### Authentication

```python
>>> from graphcommons import GraphCommons
>>> graphcommons = GraphCommons('<YOUR_API_KEY>')
>>> graphcommons.status()
{u'msg': u'Working'}
```

### Get graph
```python
graph = graphcommons.graphs('7141da86-2a40-4fdc-a7ac-031b434b9653')
print(graph.name)  # Hello from python

for node in graph.nodes:
    print(node.name)

    print(graph.edges_from(node))  # edges directed from the node
    print(graph.edges_to(node))  # edges directed to the node
```

### New Graph
```python
from graphcommons import Signal

graph = graphcommons.new_graph(
    name="Hello from python",
    description="Python Wrapper Test",
    signals=[
        Signal(
            action="node_create",
            name="Ahmet",
            type="Person",
            description="nice guy"
        ),
        Signal(
            action="edge_create",
            from_name="Ahmet",
            from_type="Person",
            to_name="Burak",
            to_type="Person",
            name="COLLABORATED",
            weight=2
        )
    ]
)


print(graph.id)  # added graph's id
```

### Update Graph

```python
from graphcommons import Signal

graphcommons.update_graph(
    id="7141da86-2a40-4fdc-a7ac-031b434b9653",
    signals=[
        Signal(
            action="node_create",
            name="Ahmet",
            type="Person",
            description="nice guy"
        ),
        Signal(
            action="edge_create",
            from_name="Ahmet",
            from_type="Person",
            to_name="Burak",
            to_type="Person",
            name="COLLABORATED",
            weight=2
        )
    ]
)
```
