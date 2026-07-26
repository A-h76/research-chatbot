"""GraphML serialization for KnowledgeGraph."""

import xml.etree.ElementTree as ET

from ..models import KnowledgeGraph


class GraphMLSerializer:
    def serialize(self, graph: KnowledgeGraph) -> str:
        root = ET.Element("graphml", {"xmlns": "http://graphml.graphdrawing.org/xmlns"})
        ET.SubElement(root, "key", {"id": "label", "for": "node", "attr.name": "label", "attr.type": "string"})
        ET.SubElement(root, "key", {"id": "node_type", "for": "node", "attr.name": "type", "attr.type": "string"})
        ET.SubElement(root, "key", {"id": "node_conf", "for": "node", "attr.name": "confidence", "attr.type": "double"})
        ET.SubElement(root, "key", {"id": "edge_type", "for": "edge", "attr.name": "type", "attr.type": "string"})
        ET.SubElement(root, "key", {"id": "edge_conf", "for": "edge", "attr.name": "confidence", "attr.type": "double"})

        graph_elem = ET.SubElement(root, "graph", {"id": graph.graph_id, "edgedefault": "directed"})

        for node in graph.nodes:
            node_elem = ET.SubElement(graph_elem, "node", {"id": node.node_id})
            ET.SubElement(node_elem, "data", {"key": "label"}).text = node.label
            ET.SubElement(node_elem, "data", {"key": "node_type"}).text = node.node_type.value
            ET.SubElement(node_elem, "data", {"key": "node_conf"}).text = f"{node.confidence:.4f}"

        for edge in graph.edges:
            edge_elem = ET.SubElement(
                graph_elem,
                "edge",
                {"id": edge.edge_id, "source": edge.source_node_id, "target": edge.target_node_id},
            )
            ET.SubElement(edge_elem, "data", {"key": "edge_type"}).text = edge.edge_type.value
            ET.SubElement(edge_elem, "data", {"key": "edge_conf"}).text = f"{edge.confidence:.4f}"

        return ET.tostring(root, encoding="unicode")
