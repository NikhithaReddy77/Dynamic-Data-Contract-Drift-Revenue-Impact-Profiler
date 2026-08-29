import networkx as nx
from .models import DownstreamAsset


class LineageGraph:
    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def add_table(self, table_fqn: str) -> None:
        self.graph.add_node(table_fqn, kind="table")

    def add_asset(self, asset: DownstreamAsset) -> None:
        self.graph.add_node(asset.asset_id, kind=asset.asset_type, asset=asset)

    def link(self, table_fqn: str, asset_id: str, columns_used: list[str]) -> None:
        if table_fqn not in self.graph:
            self.add_table(table_fqn)
        self.graph.add_edge(table_fqn, asset_id, columns=set(columns_used))

    def downstream_assets_for_column(self, table_fqn: str, column: str) -> list[DownstreamAsset]:
        if table_fqn not in self.graph:
            return []
        affected: list[DownstreamAsset] = []
        visited = set()

        def _walk(node: str):
            for _, neighbor, data in self.graph.out_edges(node, data=True):
                cols = data.get("columns")
                touches = (cols is None) or (column in cols)
                if not touches or neighbor in visited:
                    continue
                visited.add(neighbor)
                node_data = self.graph.nodes[neighbor]
                if "asset" in node_data:
                    affected.append(node_data["asset"])
                _walk(neighbor)

        _walk(table_fqn)
        return affected
