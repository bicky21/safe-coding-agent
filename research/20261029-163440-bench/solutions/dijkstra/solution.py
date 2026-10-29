import heapq


def shortest_paths(n: int, edges: list[tuple[int, int, int]], src: int) -> list[float]:
    """
    Compute the shortest path distances from src to all nodes in a directed graph
    using Dijkstra's algorithm with a min-heap.

    Args:
        n: Number of nodes (0..n-1)
        edges: List of (u, v, weight) tuples where weight >= 0
        src: Source node

    Returns:
        List of shortest distances from src to each node, using float('inf') for
        unreachable nodes.
    """
    # Build adjacency list
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))

    # Initialize distances
    dist = [float('inf')] * n
    dist[src] = 0.0

    # Min-heap: (distance, node)
    heap = [(0.0, src)]

    while heap:
        d, u = heapq.heappop(heap)

        # If we've already found a shorter path to u, skip
        if d > dist[u]:
            continue

        for v, w in adj[u]:
            new_dist = d + w
            if new_dist < dist[v]:
                dist[v] = new_dist
                heapq.heappush(heap, (new_dist, v))

    return dist