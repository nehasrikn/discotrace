import networkx as nx
from utils import load_jsonlines, PROJECT_ROOT_DIR
from collections import defaultdict
from tqdm import tqdm
import numpy as np

def select_representative_wrt_whole_space(clique_members, G):
    representative = max(
        clique_members,  # Iterate over all members of the clique
        key=lambda member: sum(
            1 - G[member][non_clique_item]['weight']  # Dissimilarity to non-clique items
            for non_clique_item in G.nodes  # Iterate over all graph nodes
            if non_clique_item not in clique_members and G.has_edge(member, non_clique_item)  # Only non-clique neighbors
        )
    )
    return representative

def select_representative_wrt_clique_dissimilarity(clique_members, G):
    representative = max(
        clique_members,
        key=lambda member: sum(
            1 - G[member][neighbor]['weight']  # Dissimilarity = 1 - similarity
            for neighbor in G.neighbors(member)  # All neighbors of the node
            if neighbor in clique_members  # Only consider neighbors within the clique
        )
    )
    return representative

def select_representative_wrt_clique_similarity(clique_members, G):
    representative = max(
        clique_members,  # Iterate over all members of the clique
        key=lambda member: sum(
            G[member][neighbor]['weight']  # Similarity score between member and neighbor
            for neighbor in G.neighbors(member)  # All neighbors of the member
            if neighbor in clique_members  # Only consider neighbors within the clique
        )
    )
    return representative

def select_representative_both(clique_members, G, alpha):
    beta = 1 - alpha
    
    representative = max(
        clique_members,
        key=lambda member: (
            # Weighted Intra-clique Similarity
            alpha * sum(
                G[member][neighbor]['weight']
                for neighbor in G.neighbors(member)
                if neighbor in clique_members
            )
            -
            # Weighted Non-clique Similarity (treated as dissimilarity)
            beta * sum(
                G[member][non_clique_item]['weight']
                for non_clique_item in G.nodes
                if non_clique_item not in clique_members and G.has_edge(member, non_clique_item)
            )
        )
    )
    return representative


def dedupe_from_similarity_matrix(similarity_matrix, question, representative_function, threshold=0.86, alpha=0.5):
    
    G = nx.Graph()
    num_nodes = similarity_matrix.shape[0]
    assert num_nodes == len(question.interpretations)
    G.add_nodes_from(range(num_nodes))
    
    
    for i in range(num_nodes):
        for j in range(i+1, num_nodes):  # Matrix is symmetric, avoid redundant edges
            if similarity_matrix[i, j] >= threshold:
                G.add_edge(i, j, weight=similarity_matrix[i, j])

    cliques = list(nx.find_cliques(G))
    
    # Calculate average similarity for each clique to prioritize them
    clique_priorities = {}
    for i, clique in enumerate(cliques):
        edge_similarities = []
        for j in range(len(clique)):
            for k in range(j + 1, len(clique)):
                if G.has_edge(clique[j], clique[k]):
                    edge_similarities.append(G[clique[j]][clique[k]]['weight'])
        
        # Compute average similarity for the clique
        avg_similarity = sum(edge_similarities) / len(edge_similarities) if edge_similarities else 0
        clique_priorities[i] = avg_similarity  # Store the priority as the average similarity

    # Map each item to the cliques it belongs to
    item_to_cliques = defaultdict(list)
    for i, clique in enumerate(cliques):
        for item in clique:
            item_to_cliques[item].append(i)  # Track all cliques each item is part of

    # Resolve overlaps by assigning each item to the highest-priority clique
    item_to_representative = {}  # Maps each item to its deduplicated representative
    processed_cliques = set()  # Keeps track of cliques that have been processed

    for item, clique_indices in item_to_cliques.items():
        # Identify the best clique for the item based on average similarity
        best_clique = max(clique_indices, key=lambda idx: clique_priorities[idx])
        
        if best_clique not in processed_cliques:
            # Get all members of the best clique
            clique_members = cliques[best_clique]
            
            representative = representative_function(clique_members, G)
            
            # Assign all members of the clique to this representative
            for member in clique_members:
                item_to_representative[member] = representative
            
            # Mark this clique as processed
            processed_cliques.add(best_clique)

    # Extract the unique deduplicated items
    unique_items = set(item_to_representative.values())

    # return the indices of the unique items in question.interpretations
    return [question.interpretations[i] for i in unique_items]