"""
Supply Chain Graph Propagation
Uses NetworkX to model supply chain dependencies and propagate risks
"""

import networkx as nx
import logging
from typing import Dict, Any, List, Tuple
from pymongo.database import Database

logger = logging.getLogger(__name__)


def build_supply_graph(db: Database, company_id: str) -> nx.DiGraph:
    """
    Build supply chain graph from MongoDB suppliers
    
    Args:
        db: MongoDB database instance
        company_id: Company ID
    
    Returns:
        NetworkX directed graph
    """
    G = nx.DiGraph()
    
    # Get company
    company = db.companies.find_one({"_id": company_id})
    if not company:
        logger.error(f"Company {company_id} not found")
        return G
    
    # Add company node
    G.add_node(
        company["_id"],
        type="company",
        name=company["company_name"],
        tier=0
    )
    logger.debug(f"Added company node: {company['company_name']}")
    
    # Get all suppliers for this company
    suppliers = list(db.suppliers.find({"company_id": company_id}))
    logger.info(f"Building graph with {len(suppliers)} suppliers")
    
    # Add supplier nodes and edges to company
    for supplier in suppliers:
        supplier_id = supplier["_id"]
        
        # Add supplier node
        G.add_node(
            supplier_id,
            type="supplier",
            name=supplier["name"],
            country=supplier["country"],
            tier=supplier.get("tier", 1),
            supplies=supplier.get("supplies", []),
            status=supplier.get("status", "active"),
            risk_score=supplier.get("risk_score_current", 0.0),
            is_single_source=supplier.get("is_single_source", False)
        )
        
        # Add edge from supplier to company (supply direction)
        # Edge weight represents dependency
        weight = supplier.get("supply_volume_pct", 50) / 100.0
        material = supplier.get("supplies", ["unknown"])[0] if supplier.get("supplies") else "unknown"
        
        # Determine target node (company or parent supplier)
        if supplier.get("tier", 1) == 1:
            # Tier-1 suppliers connect to company
            target_node = company["_id"]
        else:
            # Tier-2+ suppliers connect to their parent (if specified)
            # For now, connect all to company; in production, maintain parent relationships
            target_node = company["_id"]
        
        G.add_edge(
            supplier_id,
            target_node,
            weight=weight,
            material=material,
            tier=supplier.get("tier", 1)
        )
        
        # Add upstream suppliers (Tier-2+)
        for upstream in supplier.get("upstream_suppliers", []):
            upstream_id = f"{supplier_id}_upstream_{upstream['name']}"
            
            G.add_node(
                upstream_id,
                type="supplier",
                name=upstream["name"],
                country=upstream["country"],
                tier=supplier.get("tier", 1) + 1,
                is_upstream=True
            )
            
            upstream_weight = upstream.get("supply_volume_pct", 100) / 100.0
            
            G.add_edge(
                upstream_id,
                supplier_id,
                weight=upstream_weight,
                material=material
            )
    
    logger.info(
        f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges"
    )
    
    return G


def propagate_risk(
    G: nx.DiGraph,
    risk_node_id: str,
    initial_score: float,
    threshold: float = 1.0
) -> Dict[str, float]:
    """
    Propagate risk backward through supply chain using BFS
    
    Args:
        G: Supply chain graph
        risk_node_id: Node ID where risk originates
        initial_score: Initial risk score
        threshold: Minimum score to continue propagation
    
    Returns:
        Dictionary mapping node_id -> propagated_score
    """
    propagated = {risk_node_id: initial_score}
    queue = [(risk_node_id, initial_score)]
    
    logger.info(
        f"Starting risk propagation from '{G.nodes[risk_node_id].get('name', risk_node_id)}' "
        f"with score {initial_score:.2f}"
    )
    
    visited = set()
    
    while queue:
        node, score = queue.pop(0)
        
        if node in visited:
            continue
        visited.add(node)
        
        # Get successors (nodes that depend on this node)
        for successor in G.successors(node):
            edge_data = G[node][successor]
            dep_weight = edge_data.get("weight", 0.5)
            
            # Get vulnerability factor of successor node
            successor_data = G.nodes[successor]
            vulnerability = 1.0
            
            # Single-source nodes are more vulnerable
            if successor_data.get("is_single_source", False):
                vulnerability = 1.5
            
            # Calculate propagated score
            propagated_score = score * dep_weight * (0.5 + vulnerability * 0.5)
            
            # Only propagate if above threshold
            if propagated_score > threshold:
                # Update if higher score or first time
                if successor not in propagated or propagated[successor] < propagated_score:
                    propagated[successor] = round(propagated_score, 2)
                    queue.append((successor, propagated_score))
                    
                    logger.debug(
                        f"Propagated to '{successor_data.get('name', successor)}': "
                        f"{propagated_score:.2f} "
                        f"(weight={dep_weight:.2f}, vuln={vulnerability:.2f})"
                    )
    
    logger.info(f"Propagation complete: {len(propagated)} nodes affected")
    
    return propagated


def find_critical_nodes(G: nx.DiGraph, top_n: int = 5) -> List[Tuple[str, float]]:
    """
    Find critical nodes using betweenness centrality
    Identifies single-points-of-failure in supply chain
    
    Args:
        G: Supply chain graph
        top_n: Number of top critical nodes to return
    
    Returns:
        List of (node_id, centrality_score) tuples
    """
    try:
        # Calculate betweenness centrality
        centrality = nx.betweenness_centrality(G, weight="weight")
        
        # Sort by centrality score
        critical = sorted(
            centrality.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        logger.info(f"Identified {len(critical)} critical nodes")
        for node_id, score in critical:
            node_data = G.nodes[node_id]
            logger.info(
                f"  Critical node: {node_data.get('name', node_id)} "
                f"(centrality={score:.3f})"
            )
        
        return critical
    
    except Exception as e:
        logger.error(f"Error calculating critical nodes: {e}")
        return []


def find_vulnerable_paths(
    G: nx.DiGraph,
    company_node: str,
    max_paths: int = 10
) -> List[List[str]]:
    """
    Find potentially vulnerable supply paths to company
    
    Args:
        G: Supply chain graph
        company_node: Company node ID
        max_paths: Maximum paths to return
    
    Returns:
        List of paths (each path is list of node IDs)
    """
    all_paths = []
    
    for node in G.nodes:
        if node != company_node and G.nodes[node].get("type") == "supplier":
            try:
                # Find shortest path (weighted by dependency)
                if nx.has_path(G, node, company_node):
                    path = nx.shortest_path(
                        G, node, company_node, weight="weight"
                    )
                    all_paths.append(path)
            except nx.NetworkXNoPath:
                continue
            except Exception as e:
                logger.error(f"Error finding path from {node}: {e}")
                continue
    
    # Sort by path length (shorter = more direct dependency)
    all_paths.sort(key=len)
    
    logger.info(f"Found {len(all_paths)} supply paths to company")
    
    return all_paths[:max_paths]


def analyze_supply_chain(G: nx.DiGraph, company_node: str) -> Dict[str, Any]:
    """
    Comprehensive supply chain analysis
    
    Args:
        G: Supply chain graph
        company_node: Company node ID
    
    Returns:
        Analysis results dictionary
    """
    analysis = {
        "total_suppliers": 0,
        "tier1_suppliers": 0,
        "tier2_suppliers": 0,
        "critical_nodes": [],
        "single_source_materials": [],
        "avg_path_length": 0.0,
        "max_path_length": 0
    }
    
    try:
        # Count suppliers by tier
        for node, data in G.nodes(data=True):
            if data.get("type") == "supplier":
                analysis["total_suppliers"] += 1
                tier = data.get("tier", 1)
                if tier == 1:
                    analysis["tier1_suppliers"] += 1
                elif tier == 2:
                    analysis["tier2_suppliers"] += 1
        
        # Find critical nodes
        critical = find_critical_nodes(G, top_n=5)
        analysis["critical_nodes"] = [
            {
                "id": node_id,
                "name": G.nodes[node_id].get("name", node_id),
                "centrality": score
            }
            for node_id, score in critical
        ]
        
        # Find single-source materials
        for node, data in G.nodes(data=True):
            if data.get("is_single_source"):
                analysis["single_source_materials"].append({
                    "supplier": data.get("name"),
                    "materials": data.get("supplies", [])
                })
        
        # Calculate path metrics
        paths = find_vulnerable_paths(G, company_node, max_paths=100)
        if paths:
            path_lengths = [len(p) for p in paths]
            analysis["avg_path_length"] = sum(path_lengths) / len(path_lengths)
            analysis["max_path_length"] = max(path_lengths)
        
        logger.info(f"Supply chain analysis complete: {analysis['total_suppliers']} suppliers")
        
    except Exception as e:
        logger.error(f"Error in supply chain analysis: {e}", exc_info=True)
    
    return analysis
