"""Knowledge Graph — lightweight persistent knowledge store backed by networkx.

Stores entities (papers, concepts, methods, datasets, findings) and their
relationships as a directed graph. Serialized as JSON in the project workspace.

The graph enables:
- Cross-conversation knowledge accumulation
- Context injection when starting new conversations
- Finding related prior work within a project
- Tracking what the agent knows vs. doesn't know
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import networkx as nx

log = logging.getLogger(__name__)

# Node types for the knowledge graph
NODE_TYPES = {
    "paper",
    "concept",
    "method",
    "dataset",
    "finding",
    "question",
    "experiment",
    "tool",
    "author",
    "code_artifact",
}

# Edge types (relationships)
EDGE_TYPES = {
    "cites",  # paper -> paper
    "implements",  # code_artifact -> method
    "evaluates_on",  # experiment -> dataset
    "proposes",  # paper -> method
    "introduces",  # paper -> dataset
    "relates_to",  # any -> any
    "answers",  # finding -> question
    "depends_on",  # method -> method, code -> code
    "authored_by",  # paper -> author
    "uses",  # experiment -> method
    "produces",  # experiment -> finding
    "contradicts",  # finding -> finding
    "extends",  # method -> method
}


# Size limits to prevent DoS via unbounded graph growth
MAX_NODES = 10_000
MAX_EDGES = 50_000


class KnowledgeGraph:
    """A persistent knowledge graph for a project workspace.

    Uses networkx DiGraph internally and serializes to JSON.
    Thread-safe for single-writer (agent loop is single-threaded per conversation).
    """

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path)
        self.kg_path = self.workspace_path / ".project-meta" / "knowledge.json"
        self._graph: nx.DiGraph = nx.DiGraph()
        self._dirty = False
        self._load()

    def _load(self) -> None:
        """Load the knowledge graph from disk."""
        if not self.kg_path.exists():
            self._graph = nx.DiGraph()
            return

        try:
            data = json.loads(self.kg_path.read_text(encoding="utf-8"))
            if data.get("nodes") or data.get("edges"):
                self._graph = nx.DiGraph()
                for node in data.get("nodes", []):
                    node_id = node.get("id")
                    if not node_id:
                        log.warning("Skipping node without 'id' in knowledge graph")
                        continue
                    attrs = {k: v for k, v in node.items() if k != "id"}
                    self._graph.add_node(node_id, **attrs)
                for edge in data.get("edges", []):
                    src = edge.get("source")
                    tgt = edge.get("target")
                    if not src or not tgt:
                        log.warning("Skipping edge without source/target in knowledge graph")
                        continue
                    attrs = {k: v for k, v in edge.items() if k not in ("source", "target")}
                    self._graph.add_edge(src, tgt, **attrs)
            else:
                self._graph = nx.DiGraph()
        except Exception as e:
            log.warning(f"Failed to load knowledge graph: {e}")
            self._graph = nx.DiGraph()

    def save(self) -> None:
        """Persist the knowledge graph to disk."""
        if not self._dirty and self.kg_path.exists():
            return

        self.kg_path.parent.mkdir(parents=True, exist_ok=True)

        nodes = []
        for node_id, attrs in self._graph.nodes(data=True):
            nodes.append({"id": node_id, **attrs})

        edges = []
        for src, tgt, attrs in self._graph.edges(data=True):
            edges.append({"source": src, "target": tgt, **attrs})

        data = {
            "version": 1,
            "updated_at": datetime.now(UTC).isoformat(),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }

        self.kg_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        self._dirty = False

    # ── Node operations ──────────────────────────────────

    # Reserved attribute names that properties cannot overwrite
    _RESERVED_ATTRS = {"type", "label", "created_at", "updated_at", "source_conversation", "id"}

    def add_entity(
        self,
        entity_id: str,
        entity_type: str,
        label: str,
        properties: dict | None = None,
        conversation_uuid: str | None = None,
    ) -> bool:
        """Add or update an entity node.

        Returns True if the entity was newly added, False if updated.
        Validates entity_type against NODE_TYPES.
        Enforces MAX_NODES limit.
        """
        if entity_type not in NODE_TYPES:
            log.warning(f"Invalid entity type '{entity_type}', using 'concept'")
            entity_type = "concept"

        is_new = entity_id not in self._graph
        if is_new and self._graph.number_of_nodes() >= MAX_NODES:
            log.warning(f"Knowledge graph at capacity ({MAX_NODES} nodes)")
            return False

        attrs = {
            "type": entity_type,
            "label": label,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if is_new:
            attrs["created_at"] = datetime.now(UTC).isoformat()
        if conversation_uuid:
            attrs["source_conversation"] = conversation_uuid
        if properties:
            # Filter out reserved keys to prevent internal field overwrite
            safe_props = {k: v for k, v in properties.items() if k not in self._RESERVED_ATTRS}
            attrs.update(safe_props)

        self._graph.add_node(entity_id, **attrs)
        self._dirty = True
        return is_new

    def get_entity(self, entity_id: str) -> dict | None:
        """Get an entity by ID."""
        if entity_id not in self._graph:
            return None
        return {"id": entity_id, **self._graph.nodes[entity_id]}

    def find_entities(self, entity_type: str | None = None, limit: int = 50) -> list[dict]:
        """Find entities, optionally filtered by type."""
        results = []
        for node_id, attrs in self._graph.nodes(data=True):
            if entity_type and attrs.get("type") != entity_type:
                continue
            results.append({"id": node_id, **attrs})
            if len(results) >= limit:
                break
        return results

    def search_entities(self, query: str, limit: int = 20) -> list[dict]:
        """Search entities by label (case-insensitive substring match)."""
        query_lower = query.lower()
        results = []
        for node_id, attrs in self._graph.nodes(data=True):
            label = attrs.get("label", "")
            if query_lower in label.lower() or query_lower in node_id.lower():
                results.append({"id": node_id, **attrs})
                if len(results) >= limit:
                    break
        return results

    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity and all its edges."""
        if entity_id not in self._graph:
            return False
        self._graph.remove_node(entity_id)
        self._dirty = True
        return True

    # ── Edge operations ──────────────────────────────────

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        properties: dict | None = None,
        conversation_uuid: str | None = None,
    ) -> bool:
        """Add a directed relationship between two entities.

        Both entities must already exist. Returns True if edge was newly added.
        Validates relationship against EDGE_TYPES.
        Enforces MAX_EDGES limit.
        """
        if relationship not in EDGE_TYPES:
            log.warning(f"Invalid relationship type '{relationship}', using 'relates_to'")
            relationship = "relates_to"

        if source_id not in self._graph or target_id not in self._graph:
            log.warning(
                f"Cannot add edge {source_id}->{target_id}: "
                f"missing {'source' if source_id not in self._graph else 'target'}"
            )
            return False

        is_new = not self._graph.has_edge(source_id, target_id)
        if is_new and self._graph.number_of_edges() >= MAX_EDGES:
            log.warning(f"Knowledge graph at edge capacity ({MAX_EDGES} edges)")
            return False

        attrs = {
            "type": relationship,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if is_new:
            attrs["created_at"] = datetime.now(UTC).isoformat()
        if conversation_uuid:
            attrs["source_conversation"] = conversation_uuid
        if properties:
            safe_props = {k: v for k, v in properties.items() if k not in self._RESERVED_ATTRS}
            attrs.update(safe_props)

        self._graph.add_edge(source_id, target_id, **attrs)
        self._dirty = True
        return is_new

    def get_neighbors(self, entity_id: str, direction: str = "both") -> list[dict]:
        """Get connected entities.

        Args:
            entity_id: The entity to find neighbors for.
            direction: "out" (successors), "in" (predecessors), or "both".
        """
        if entity_id not in self._graph:
            return []

        neighbors = set()
        if direction in ("out", "both"):
            neighbors.update(self._graph.successors(entity_id))
        if direction in ("in", "both"):
            neighbors.update(self._graph.predecessors(entity_id))

        results = []
        for nid in neighbors:
            edge_data = self._graph.edges.get((entity_id, nid), {}) or self._graph.edges.get(
                (nid, entity_id), {}
            )
            results.append(
                {
                    "id": nid,
                    **self._graph.nodes[nid],
                    "relationship": edge_data.get("type", "relates_to"),
                }
            )
        return results

    # ── Query helpers ────────────────────────────────────

    def get_summary(self) -> dict:
        """Get a summary of the knowledge graph for context injection."""
        type_counts: dict[str, int] = {}
        for _, attrs in self._graph.nodes(data=True):
            t = attrs.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        # Get recent entities (by updated_at)
        recent = sorted(
            [{"id": nid, **attrs} for nid, attrs in self._graph.nodes(data=True)],
            key=lambda x: x.get("updated_at", ""),
            reverse=True,
        )[:10]

        return {
            "total_nodes": self._graph.number_of_nodes(),
            "total_edges": self._graph.number_of_edges(),
            "type_counts": type_counts,
            "recent_entities": [
                {"id": e["id"], "type": e.get("type"), "label": e.get("label")} for e in recent
            ],
        }

    def get_context_for_conversation(self, max_tokens_approx: int = 2000) -> str:
        """Generate a text summary of the knowledge graph for injecting into agent context.

        Produces a compact representation suitable for the system prompt.
        """
        if self._graph.number_of_nodes() == 0:
            return ""

        lines = ["## Project Knowledge Graph\n"]

        # Group by type
        by_type: dict[str, list] = {}
        for nid, attrs in self._graph.nodes(data=True):
            t = attrs.get("type", "other")
            by_type.setdefault(t, []).append((nid, attrs))

        char_count = 0
        for entity_type, entities in by_type.items():
            if char_count > max_tokens_approx * 4:  # rough char estimate
                lines.append(
                    f"\n... and more ({self._graph.number_of_nodes() - len(lines)} entities)"
                )
                break

            lines.append(f"\n### {entity_type.replace('_', ' ').title()}s")
            for nid, attrs in entities[:15]:  # cap per type
                label = attrs.get("label", nid)
                line = f"- **{label}**"
                # Add key properties
                if attrs.get("abstract"):
                    line += f": {attrs['abstract'][:150]}..."
                elif attrs.get("description"):
                    line += f": {attrs['description'][:150]}..."
                lines.append(line)
                char_count += len(line)

        # Add key relationships
        if self._graph.number_of_edges() > 0:
            lines.append("\n### Key Relationships")
            edge_count = 0
            for src, tgt, attrs in self._graph.edges(data=True):
                if edge_count >= 20:
                    lines.append(f"... and {self._graph.number_of_edges() - edge_count} more")
                    break
                src_label = self._graph.nodes[src].get("label", src)
                tgt_label = self._graph.nodes[tgt].get("label", tgt)
                rel = attrs.get("type", "relates_to")
                lines.append(f"- {src_label} --[{rel}]--> {tgt_label}")
                edge_count += 1

        return "\n".join(lines)

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()
