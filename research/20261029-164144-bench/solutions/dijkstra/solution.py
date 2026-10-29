import heapq
from typing import List, Tuple

def shortest_paths(n: int, edges: List[Tuple[int, int, int]], src: int) -> List[float]:
    """
    Compute the shortest distances from a source node to all other nodes in a directed
    graph with non-negative edge weights using Dijkstra's algorithm.

    Parameters
    ----------
    n : int
        Number of nodes in the graph. Nodes are labeled from 0 to n-1.
    edges : List[Tuple[int, int, int]]
        List of directed edges represented as (u, v, weight). All weights are
        assumed to be non-negative.
    src : int
        The source node from which shortest paths are computed.

    Returns
    -------
    List[float]
        A list of length n where the i-th element is the shortest distance from
        src to node i. If a node is unreachable, its distance is float('inf').
    """
    # Edge case: empty graph
    if n == 0:
        return []

    # Build adjacency list
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        # Validate indices (optional, but safe)
        if 0 <= u < n and 0 <= v < n:
            adj[u].append((v, w))

    # Initialize distances
    dist = [float('inf')] * n
    dist[src] = 0.0

    # Min-heap priority queue: (distance, node)
    heap = [(0.0, src)]

    while heap:
        d, u = heapq.heappop(heap)

        # If we have already found a better path to u, skip
        if d > dist[u]:
            continue

        for v, w in adj[u]:
            new_dist = d + w
            if new_dist < dist[v]:
                dist[v] = new_dist
                heapq.heappush(heap, (new_dist, v))

    return dist