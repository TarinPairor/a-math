from anytree import Node, RenderTree
import networkx as nx
import matplotlib.pyplot as plt
from collections import Counter

S = "S"
O = "O"
DIVIDE = "/"
DASH = "-"
EQ = "="
M = "M"
W = "W"
Z = "Z"
T = "T"  # Define terminal node

MAX_DEPTH = 11
MAX_CONTIG_W = 3

def can_terminate(path):
    """
    Decide if the path up to this non-terminal can be terminated with T.

    We use the reversed path from leaves up to root.
    """
    if len(path) == 1 and path[0] == S:
        return False
    # We'll look for these forbidden patterns:
    # 1. S->M->=->W   AND   =->M->=->W  (if = occurs and has children: i.e., not at leaf)
    if len(path) >= 4 and (path[-4:] == [S, M, EQ, W] or path[-4:] == [EQ, M, EQ, W]):
        return False

    # 2. S -> W = M   AND   = -> W = M
    if len(path) >= 4 and (path[-4:] == [S, W, EQ, M] or path[-4:] == [EQ, W, EQ, M]):
        return False

    # 3. S->W(x in a row)=W(y in a row) where x != y
    #    AND  = -> W(x in a row) = W(y in a row), x != y, and = has children
    if EQ in path:
        eq_idx = path.index(EQ)
        # S ... W(w1) = W(w2), with S before -- previous behavior
        left_w = 0
        i = eq_idx-1
        while i >= 0 and path[i] == W:
            left_w += 1
            i -= 1
        right_w = 0
        i = eq_idx+1
        while i < len(path) and path[i] == W:
            right_w += 1
            i += 1
        # Original S ... = ... pattern
        if left_w > 0 and right_w > 0 and left_w != right_w:
            if S in path[:eq_idx-left_w+1]:
                return False
        # Additionally: = ... W(w1)=W(w2) with left/right
        if len(path) >= eq_idx+2:
            if path[0] == EQ and left_w > 0 and right_w > 0 and left_w != right_w:
                return False

    # 4. S-> W(1 or 3 in a row) = M
    #    AND  = -> W(1 or 3 in a row) = M
    if EQ in path:
        eq_idx = path.index(EQ)
        left_w = 0
        i = eq_idx-1
        while i >= 0 and path[i] == W:
            left_w += 1
            i -= 1
        if left_w in (1, 3) and eq_idx+1 < len(path) and path[eq_idx+1] == M:
            if S in path[:eq_idx-left_w+1]:
                return False
            if path[0] == EQ:
                return False

    # 5. S -> M = W(1 or 3 in a row)
    #    AND  = -> M = W(1 or 3 in a row)
    if len(path) >= 4 and ((path[-4] == S and path[-3] == M and path[-2] == EQ) or
                           (path[-4] == EQ and path[-3] == M and path[-2] == EQ)):
        # trailing W streak after EQ
        i = len(path)-1
        w_streak = 0
        while i > len(path)-1 or i > -1 and path[i] == W:
            w_streak += 1
            i -= 1
        if w_streak in (1, 3):
            return False
        eq_idx = len(path)-2
        w_after_eq = 0
        for tok in path[eq_idx+1:]:
            if tok == W:
                w_after_eq += 1
            else:
                break
        if w_after_eq in (1, 3):
            return False

    # s -> -N=N and s -> N=-N where N is a stream of M/W/0/Z combinations, must not allow can_terminate
    # = -> -N=N and = -> N=-N (same)
    if len(path) >= 5:
        # S -> - N = N (where N is at least one, and N = stream of M/W/0/Z)
        if path[-5] == S and path[-4] == DASH and path[-2] == EQ:
            # get what N is
            n1_seq = []
            i = -3
            while abs(i) < len(path) and path[i] in (M, W, Z, '0', 0):
                n1_seq.append(path[i])
                i -= 1
            # N must be at least one
            if len(n1_seq) >= 1:
                # N right of = must match same "N token type"
                n2_seq = []
                i = -1
                while abs(i) <= len(path) and path[i] in (M, W, Z, '0', 0):
                    n2_seq.append(path[i])
                    i -= 1
                # If there is at least one token after = (N)
                if len(n2_seq) >= 1:
                    return False
        # = -> - N = N
        if path[-5] == EQ and path[-4] == DASH and path[-2] == EQ:
            n1_seq = []
            i = -3
            while abs(i) < len(path) and path[i] in (M, W, Z, '0', 0):
                n1_seq.append(path[i])
                i -= 1
            if len(n1_seq) >= 1:
                n2_seq = []
                i = -1
                while abs(i) <= len(path) and path[i] in (M, W, Z, '0', 0):
                    n2_seq.append(path[i])
                    i -= 1
                if len(n2_seq) >= 1:
                    return False
        # S -> N = - N
        if path[-5] == S and path[-3] == EQ and path[-2] == DASH:
            # get left N (must be at least 1 and stream of M/W/Z/0)
            n1_seq = []
            i = -4
            while abs(i) < len(path) and path[i] in (M, W, Z, '0', 0):
                n1_seq.append(path[i])
                i -= 1
            if len(n1_seq) >= 1:
                # get right N after - (must be at least 1)
                n2_seq = []
                i = -1
                while abs(i) <= len(path) and path[i] in (M, W, Z, '0', 0):
                    n2_seq.append(path[i])
                    i -= 1
                if len(n2_seq) >= 1:
                    return False
        # = -> N = - N
        if path[-5] == EQ and path[-3] == EQ and path[-2] == DASH:
            n1_seq = []
            i = -4
            while abs(i) < len(path) and path[i] in (M, W, Z, '0', 0):
                n1_seq.append(path[i])
                i -= 1
            if len(n1_seq) >= 1:
                n2_seq = []
                i = -1
                while abs(i) <= len(path) and path[i] in (M, W, Z, '0', 0):
                    n2_seq.append(path[i])
                    i -= 1
                if len(n2_seq) >= 1:
                    return False

    # 6. An O (T cannot terminate from ALL Os)
    if path[-1] == O:
        return False

    # 7. An = (T cannot terminate from EQ)
    if path[-1] == EQ:
        return False

    # 8. A - (T cannot terminate from DASH)
    if path[-1] == DASH:
        return False
    # 9. A / (T cannot terminate from /)
    if path[-1] == DIVIDE:
        return False

    # Else allowed to terminate
    return True

def build_custom_dag():
    """
    Build a DAG such that at each (depth, node type, W streak),
    nodes at the same level with the same value are shared.
    Returns a dict-of-dicts: dag_nodes[level][nodetype][w_streak] = nodeid, with a nx.DiGraph
    """
    G = nx.DiGraph()
    # Each node in the DAG will have a unique id: (depth, symbol, w_streak)
    dag_nodes = {}  # dag_nodes[depth][symbol][wstreak] = node_id
    # To track valid nodes that can be reached
    from collections import defaultdict

    # For T terminal, always make a unique per (depth, path) node to avoid merge
    # To recover equivalence to original tree for display, assign labels with depth

    def get_node_id(depth, symbol, w_streak):
        return (depth, symbol, w_streak)

    # T nodes are terminal (unique per location, but we can just use a special symbol if desired)

    # Initial root
    dag_nodes = defaultdict(lambda: defaultdict(dict))
    node_labels = {}

    root_depth = 0
    root_wstreak = 0
    root_nodeid = get_node_id(root_depth, S, root_wstreak)
    dag_nodes[root_depth][S][root_wstreak] = root_nodeid
    G.add_node(root_nodeid, label=S)
    node_labels[root_nodeid] = S

    edges_to_add = []

    # BFS queue: (depth, nodetype, w_streak, path_so_far)
    from collections import deque
    queue = deque()
    queue.append((root_depth, S, root_wstreak, [S]))

    while queue:
        depth, nodetype, w_streak, path = queue.popleft()
        cur_nodeid = get_node_id(depth, nodetype, w_streak)

        # If max depth: only allow T if permissible, never add further branches
        if depth >= MAX_DEPTH:
            if can_terminate(path):
                t_id = (depth+1, T, 0)
                G.add_node(t_id, label=T)
                node_labels[t_id] = T
                G.add_edge(cur_nodeid, t_id)
            continue

        # Try terminating here if possible
        if can_terminate(path):
            t_id = (depth+1, T, 0)
            G.add_node(t_id, label=T)
            node_labels[t_id] = T
            G.add_edge(cur_nodeid, t_id)

        # Figure new children/edges per rules
        new_w_streak = w_streak  # default, may be overwritten below

        def insert_child(child_symbol, extra_w_streak, pathadd):
            nonlocal queue
            # Update W streak only if relevant
            if child_symbol == W:
                new_ws = w_streak + 1
            else:
                new_ws = 0
            # W streak constraint
            if child_symbol == W and new_ws > MAX_CONTIG_W:
                return
            child_id = get_node_id(depth+1, child_symbol, new_ws)
            if child_id not in G:
                G.add_node(child_id, label=child_symbol)
                node_labels[child_id] = child_symbol
            # DAG dedup: same node for same (depth+1, symbol, new_ws)
            if child_symbol not in dag_nodes[depth+1]:
                dag_nodes[depth+1][child_symbol] = {}
            if new_ws not in dag_nodes[depth+1][child_symbol]:
                dag_nodes[depth+1][child_symbol][new_ws] = child_id
                queue.append((depth+1, child_symbol, new_ws, path + [child_symbol]))
            G.add_edge(cur_nodeid, dag_nodes[depth+1][child_symbol][new_ws])

        # Node expansion rules
        if nodetype == S:
            insert_child(DASH, 0, [DASH])
            insert_child(M, 0, [M])
            insert_child(W, 1, [W])
            insert_child(Z, 0, [Z])
        elif nodetype == DASH:
            insert_child(M, 0, [M])
            insert_child(W, 1, [W])
        elif nodetype == EQ:
            insert_child(M, 0, [M])
            insert_child(W, 1, [W])
            insert_child(Z, 0, [Z])
            insert_child(DASH, 0, [DASH])
        elif nodetype == M:
            insert_child(O, 0, [O])
            insert_child(EQ, 0, [EQ])
            insert_child(DIVIDE, 0, [DIVIDE])
            insert_child(DASH, 0, [DASH])
        elif nodetype == Z:
            # Z can lead to O, = and can lead to Z only if previous was W (i.e. W->Z->Z)
            if len(path) >= 2 and path[-2] == W:
                insert_child(Z, 0, [Z])
            insert_child(O, 0, [O])
            insert_child(EQ, 0, [EQ])
            insert_child(DIVIDE, 0, [DIVIDE])
            insert_child(DASH, 0, [DASH])
        elif nodetype == W:
            insert_child(W, w_streak, [W])
            insert_child(Z, 0, [Z])
            insert_child(O, 0, [O])
            insert_child(EQ, 0, [EQ])
            insert_child(DIVIDE, 0, [DIVIDE])
            insert_child(DASH, 0, [DASH])
        elif nodetype == O:
            insert_child(M, 0, [M])
            insert_child(W, 1, [W])
            insert_child(Z, 0, [Z])
        elif nodetype == DIVIDE:
            insert_child(M, 0, [M])
            insert_child(W, 1, [W])

    return G, dag_nodes, node_labels

custom_G, dag_nodes, custom_labels = build_custom_dag()

# For display: Count nodes by type and number of Ts
type_cnt = Counter()
for nodeid in custom_G.nodes:
    label = custom_G.nodes[nodeid].get("label", "")
    type_cnt[label] += 1
num_terminators = type_cnt.get(T, 0)

print("Node counts in custom DAG:", type_cnt)
print("Number of T nodes (terminal nodes):", num_terminators)

try:
    custom_pos = nx.nx_pydot.graphviz_layout(custom_G, prog='dot')
except Exception:
    custom_pos = nx.spring_layout(custom_G)

draw_labels = {k: f"{v}\n{str(k)}" for k, v in custom_labels.items()}

plt.figure(figsize=(20, 14))
nx.draw(custom_G, custom_pos, with_labels=True, labels=draw_labels, arrows=False, node_size=200, node_color='lightcyan', font_size=10)
plt.title("Custom S → -,M,W,Z DAG with Terminals, Node ids = (depth,symbol,w_streak)")
plt.tight_layout(pad=3.0)
plt.show()


def get_terminal_paths_dag(G, T, start_node=None):
    """
    Find all paths from the root(s) to terminal "T" nodes in the DAG G,
    returning paths as lists of labels.
    If start_node is given, start from there, else use the root node (0, S, 0).
    """
    # We use node ids (tuples) in the DAG as path elements
    if start_node is None:
        # Default start node: first node inserted (should be root)
        for nodeid in G.nodes:
            label = G.nodes[nodeid].get("label", "")
            if label == "S" or label == S:
                start_node = nodeid
                break
        else:
            raise ValueError("No 'S' node (root) found in DAG.")
    results = []
    stack = [(start_node, [])]
    while stack:
        nodeid, path = stack.pop()
        node_label = G.nodes[nodeid].get("label", "")
        new_path = path + [node_label]
        children = list(G.successors(nodeid))
        if not children:
            if node_label == T:
                results.append(new_path)
        else:
            for child in children:
                stack.append((child, new_path))
    return results

terminal_paths = get_terminal_paths_dag(custom_G, T)
# for p in terminal_paths:
#     print(p)
print(len(terminal_paths))


import networkx as nx
from collections import Counter

def prune_dag(G, target_counts, T, S):
    """
    Return a new pruned DAG (as a new nx.DiGraph) from G,
    such that no path from the root ("S") contains more than allowed counts (target_counts)
    for any node label in {"O", "M", "W", "Z", DASH, EQ}.
    """

    pruned_G = nx.DiGraph()
    node_map = {}  # maps (nodeid, frozenset(counts)) -> newnode id so we don't re-add the same pruned nodes

    keys = ["O", "M", "W", "Z", DASH, EQ]
    root = None
    for nodeid in G.nodes:
        label = G.nodes[nodeid].get("label", "")
        if label == "S" or label == S:
            root = nodeid
            break
    if root is None:
        raise ValueError("No S root node found in DAG")

    # We use a DFS stack: (old node id, new parent in pruned_G, Counter current_counts)
    stack = [(root, None, Counter())]
    while stack:
        nodeid, parent_newid, curr_counts = stack.pop()
        label = G.nodes[nodeid].get("label", "")
        next_counts = curr_counts.copy()
        if label in keys:
            # Check for exceeding limit
            if curr_counts[label] >= target_counts.get(label, 0):
                continue
            if target_counts.get(label, 0) == 0:
                continue
            next_counts[label] += 1
        # nodeid+counts tuple to uniquely identify this element in the DAG
        state = (nodeid, tuple((k, next_counts[k]) for k in keys))
        if state in node_map:
            this_newid = node_map[state]
        else:
            this_newid = (nodeid, tuple(sorted(next_counts.items())))
            pruned_G.add_node(this_newid, label=label)
            node_map[state] = this_newid
        if parent_newid is not None:
            pruned_G.add_edge(parent_newid, this_newid)
        # Terminal check
        children = list(G.successors(nodeid))
        if not children:
            # If terminal, only keep if it is a T
            if label == T:
                continue
            else:
                continue  # drop non-T leaves
        else:
            for child in children:
                stack.append((child, this_newid, next_counts))
    return pruned_G

def label_counts_on_dag(G, T):
    """
    Return Counter of labels in the given DAG. Includes all nodes.
    """
    labels = [G.nodes[n].get("label", "") for n in G.nodes]
    return Counter(labels)

# Example: prune out all subtrees with any DASH or EQ node if {DASH: 0, O: 0, M:3, W:0, Z:0, EQ:0, ...}
target_counts = {O: 2, M: 2, W: 2, Z: 0, DASH: 0, EQ: 1, DIVIDE: 1}  # adjust these as appropriate

# Create pruned DAG
pruned_G = prune_dag(custom_G, target_counts, T, S)

# Visualize pruned DAG
import matplotlib.pyplot as plt

def visualize_dag(pruned_G, title="Pruned DAG"):
    node_labels = {n: G_data.get("label", "") if isinstance(G_data := pruned_G.nodes[n], dict) else "" for n in pruned_G.nodes}
    try:
        pos = nx.nx_pydot.graphviz_layout(pruned_G, prog='dot')
    except Exception:
        pos = nx.spring_layout(pruned_G)
    plt.figure(figsize=(20, 14))
    nx.draw(pruned_G, pos, with_labels=True, labels=node_labels, arrows=False, node_size=200, node_color='lightblue', font_size=10)
    plt.title(title)
    plt.tight_layout(pad=3.0)
    plt.show()

# visualize_dag(pruned_G, title="Custom DAG pruned for " + str(target_counts))
custom_counts = label_counts_on_dag(pruned_G, T)
num_terminators = custom_counts.get(T, 0)

print("Node counts in custom DAG:", custom_counts)
print("Number of T nodes (terminal nodes):", num_terminators)


# Given an input mapping (dict) of {type: value}, where sum of values == N,
# for each way to split into (left_sum, right_sum) with left_sum + right_sum = N,
# enumerate all unordered splits of the MULTISET (all items, as individuals) into left_sum/right_sum,
# Each split is described by counts per type in each part; splits that differ by which particular 'M' or 'O'
# are NOT counted as different, so only bag counts matter (unordered multiset partition)
# Example: left: {O:1, M:1}, right: {O:1, M:1, W:3, EQ:1} is different from left: {O:2}, right: {M:2, W:3, EQ:1}, etc.

from collections import Counter
from itertools import product

input_mapping = {'O': 1, 'M': 1, 'W': 2, 'Z': 1, 'DASH': 1, 'EQ': 1, 'DIVIDE': 1}
types = list(input_mapping.keys())
N = sum(input_mapping.values())

def all_type_count_selections(types, input_counts, target_total):
    """
    For the given type list and their total counts, yield all dicts {type: count} summing to target_total,
    with each type's count from 0 up to its input_count.
    """
    ranges = [range(input_counts[t] + 1) for t in types]
    for counts in product(*ranges):
        if sum(counts) == target_total:
            yield dict(zip(types, counts))

def subtract_counts(full, sub):
    # Returns a dict of full - sub for each type
    return {k: full[k] - sub.get(k,0) for k in full}

# Helper: represent each partition signature for unorderedness (sort types in a fixed order)
def partition_signature(left_counts, right_counts, types):
    # Create tuple of type-count pairs in the same order for both sides, e.g.
    # (('EQ', 1), ('M', 1), ('O', 1), ('W', 2)), (('EQ', 0), ('M', 1), ('O', 1), ('W', 1))
    left_tuple = tuple((t, left_counts.get(t, 0)) for t in types)
    right_tuple = tuple((t, right_counts.get(t, 0)) for t in types)
    # Unordered: use frozenset with tuples sorted so (min, max)
    return frozenset([left_tuple, right_tuple])

big_sum = 0
for left_sum in range(1, N//2 + 1):
    right_sum = N - left_sum
    seen_partitions = set()
    count = 0
    for left_counts in all_type_count_selections(types, input_mapping, left_sum):
        right_counts = subtract_counts(input_mapping, left_counts)
        sig = partition_signature(left_counts, right_counts, types)
        if sig in seen_partitions:
            continue
        seen_partitions.add(sig)
        # Only print if both sides have at least one element!
        left_counts_str = ', '.join(f"{k}:{v}" for k, v in left_counts.items() if v > 0)
        right_counts_str = ', '.join(f"{k}:{v}" for k, v in right_counts.items() if v > 0)
        print(f"Left({left_sum}): {{{left_counts_str}}} | Right({right_sum}): {{{right_counts_str}}}")
        count += 1
    print(f"Total unordered ways for split {left_sum} + {right_sum}: {count}\n")
    big_sum += count
print("Sum of all unordered splits across all splits:", big_sum)



import networkx as nx
from collections import Counter
from itertools import product

# ----------------------------
# 1) Tile -> counts
# ----------------------------

OPS = {"+", "*"}   # concrete operator tiles

def tiles_to_counts(arr):
    """
    Build counts for:
      - M: numbers 10-20
      - W: digits 1-9
      - Z: 0
      - EQ: '='
      - DASH: '-'
      - DIVIDE: '/'
      - O: total operators (+,-,*,/)  (coarse pool used for pruning)
    Note: '-' and '/' are ALSO counted in O (because O can be - or / too).
    """
    c = Counter()
    for x in arr:
        # normalize
        if isinstance(x, int):
            s = str(x)
        else:
            s = str(x).strip()

        if s in OPS:
            c["O"] += 1
        elif s == "-":
            c["DASH"] += 1
        elif s == "/":
            c["DIVIDE"] += 1
        elif s == "=":
            c["EQ"] += 1
        else:
            # numbers
            try:
                n = int(s)
            except:
                continue

            if n == 0:
                c["Z"] += 1
            elif 1 <= n <= 9:
                c["W"] += 1
            elif 10 <= n <= 20:
                c["M"] += 1
            else:
                # ignore out-of-range tiles
                pass

    return dict(c)

def tiles_to_multiset(arr):
    """
    Concrete tile multiset for backtracking assignment.
    Uses string tokens: '0','1'..'9','10'..'20','+','-','*','/','='
    """
    ms = Counter()
    for x in arr:
        s = str(x).strip()

        if s in OPS or s in {"=", "-", "/"}:
            ms[s] += 1
        else:
            try:
                n = int(s)
            except:
                continue
            if 0 <= n <= 20:
                ms[str(n)] += 1
    return ms

# ----------------------------
# 2) Unordered dual partitions (bag partitions)
# ----------------------------

def all_type_count_selections(types, input_counts, target_total):
    ranges = [range(input_counts.get(t, 0) + 1) for t in types]
    for counts in product(*ranges):
        if sum(counts) == target_total:
            yield dict(zip(types, counts))

def subtract_counts(full, sub):
    return {k: full.get(k, 0) - sub.get(k, 0) for k in full}

def partition_signature(left_counts, right_counts, types):
    left_tuple  = tuple((t, left_counts.get(t, 0))  for t in types)
    right_tuple = tuple((t, right_counts.get(t, 0)) for t in types)
    return frozenset([left_tuple, right_tuple])

def unordered_partitions(count_map, require_nonempty=True):
    """
    Yields (left_counts, right_counts) as dicts, unordered (no duplicates).
    """
    types = list(count_map.keys())
    N = sum(count_map.values())
    start = 1 if require_nonempty else 0
    end = N//2 + 1

    for left_sum in range(start, end):
        right_sum = N - left_sum
        if require_nonempty and right_sum == 0:
            continue
        seen = set()
        for left_counts in all_type_count_selections(types, count_map, left_sum):
            right_counts = subtract_counts(count_map, left_counts)
            sig = partition_signature(left_counts, right_counts, types)
            if sig in seen:
                continue
            seen.add(sig)
            yield left_counts, right_counts

# ----------------------------
# 3) Prune DAG by coarse label counts (includes DIVIDE)
# ----------------------------

def prune_dag_by_counts(G, target_counts, T, S, DASH, EQ, DIVIDE):
    """
    Coarse pruning: only enforces label-count limits.
    O-count is treated as a pool limit (but final backtracking does exact tile checks).
    """
    keys = ["O", "M", "W", "Z", DASH, EQ, DIVIDE]

    # find root
    root = None
    for nodeid in G.nodes:
        label = G.nodes[nodeid].get("label", "")
        if label == "S" or label == S:
            root = nodeid
            break
    if root is None:
        raise ValueError("No S root node found in DAG")

    pruned = nx.DiGraph()
    node_map = {}  # state -> new node id

    stack = [(root, None, Counter())]
    while stack:
        nodeid, parent_newid, curr = stack.pop()
        label = G.nodes[nodeid].get("label", "")

        nxt = curr.copy()
        if label in keys:
            limit = target_counts.get(label, 0)
            if limit <= 0:
                continue
            if curr[label] >= limit:
                continue
            nxt[label] += 1

        state = (nodeid, tuple((k, nxt.get(k, 0)) for k in keys))
        if state in node_map:
            this_newid = node_map[state]
        else:
            this_newid = (nodeid, tuple(sorted(nxt.items())))
            pruned.add_node(this_newid, label=label)
            node_map[state] = this_newid

        if parent_newid is not None:
            pruned.add_edge(parent_newid, this_newid)

        children = list(G.successors(nodeid))
        if not children:
            # keep leaf only if it's T
            continue
        for child in children:
            stack.append((child, this_newid, nxt))

    return pruned

# ----------------------------
# 4) Terminal paths (your function, cleaned)
# ----------------------------

def get_terminal_paths_dag(G, T, S, start_node=None):
    """
    Find all paths from root to terminal T leaves, returning label lists.
    """
    if start_node is None:
        for nodeid in G.nodes:
            label = G.nodes[nodeid].get("label", "")
            if label == "S" or label == S:
                start_node = nodeid
                break
        else:
            raise ValueError("No 'S' node found.")

    results = []
    stack = [(start_node, [])]
    while stack:
        nodeid, path = stack.pop()
        node_label = G.nodes[nodeid].get("label", "")
        new_path = path + [node_label]
        children = list(G.successors(nodeid))
        if not children:
            if node_label == T:
                results.append(new_path)
        else:
            for child in children:
                stack.append((child, new_path))
    return results

# ----------------------------
# 5) Backtracking assignment: labels -> concrete tiles, deduped
# ----------------------------

def label_choices(label, ms_counter):
    """
    Return possible concrete tokens for a DAG label given remaining multiset.
    """
    # numbers
    if label == "M":
        # 10..20
        return [t for t in ms_counter if ms_counter[t] > 0 and t.isdigit() and 10 <= int(t) <= 20]
    if label == "W":
        return [t for t in ms_counter if ms_counter[t] > 0 and t.isdigit() and 1 <= int(t) <= 9]
    if label == "Z":
        return ["0"] if ms_counter.get("0", 0) > 0 else []

    # fixed symbols
    if label == "=":
        return ["="] if ms_counter.get("=", 0) > 0 else []
    if label == "-":
        return ["-"] if ms_counter.get("-", 0) > 0 else []
    if label == "/":
        return ["/"] if ms_counter.get("/", 0) > 0 else []

    # O can be any operator tile still available
    if label == "O":
        return [op for op in ["+", "*"] if ms_counter.get(op, 0) > 0]


    # S/T should not be assigned here
    return []

def paths_to_expressions(paths, ms_side):
    """
    For a side (lhs or rhs):
      - paths: label paths like ['S','M','O','W','T']
      - ms_side: Counter of concrete tiles available for that side
    Returns: set of comma-joined expressions (without S/T).
    """
    out = set()

    for p in paths:
        core = [x for x in p if x not in ("S", "T")]  # assign only internal labels

        def rec(i, ms, built):
            if i == len(core):
                out.add(",".join(built))
                return

            lab = core[i]
            # iterate unique choices (Counter already dedupes)
            for tok in label_choices(lab, ms):
                ms[tok] -= 1
                if ms[tok] == 0:
                    del ms[tok]
                rec(i+1, ms, built + [tok])
                ms[tok] += 1

        rec(0, ms_side.copy(), [])

    return out

from functools import lru_cache
from collections import Counter

def paths_to_expressions_memo(paths, ms_side: Counter):
    """
    Like paths_to_expressions, but memoized.
    Returns a set of comma-joined expressions (without S/T).
    """

    # --- Helper: make a stable token list + count tuple ---
    tokens = sorted(ms_side.keys(), key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else 999, x))
    idx = {t:i for i,t in enumerate(tokens)}
    start_counts = tuple(ms_side[t] for t in tokens)

    def token_allowed_for_label(tok: str, lab: str) -> bool:
        # numbers
        if lab == "Z":
            return tok == "0"
        if lab == "W":
            return tok.isdigit() and 1 <= int(tok) <= 9
        if lab == "M":
            return tok.isdigit() and 10 <= int(tok) <= 20

        # operators / symbols (your new exclusive rules)
        if lab == "O":
            return tok in {"+", "*"}
        if lab == "-":      # DASH label
            return tok == "-"
        if lab == "/":      # DIVIDE label
            return tok == "/"
        if lab == "=":      # EQ label (only if allowed inside sides)
            return tok == "="

        return False

    # --- Group by core label sequence so we solve each shape once ---
    core_shapes = set()
    for p in paths:
        core = tuple(x for x in p if x not in ("S", "T"))
        core_shapes.add(core)

    out = set()

    for core in core_shapes:

        # Precompute candidate token indices for each label position (fast)
        cand_idxs = []
        for lab in core:
            cand = [idx[tok] for tok in tokens if token_allowed_for_label(tok, lab)]
            cand_idxs.append(tuple(cand))

        @lru_cache(None)
        def rec(i, rem_counts):
            """
            Returns a frozenset of suffix strings for core[i:].
            """
            if i == len(core):
                return frozenset([""])  # empty suffix

            results = set()
            for j in cand_idxs[i]:
                if rem_counts[j] <= 0:
                    continue

                new_counts = list(rem_counts)
                new_counts[j] -= 1
                new_counts = tuple(new_counts)

                tok = tokens[j]
                for suf in rec(i + 1, new_counts):
                    if suf == "":
                        results.add(tok)
                    else:
                        results.add(tok + "," + suf)

            return frozenset(results)

        out |= set(rec(0, start_counts))

    return out


# ----------------------------
# 6) End-to-end: tiles -> partitions -> pruned dags -> terminal paths -> equations
# ----------------------------

def generate_all_equations(custom_G, tiles_arr, T, S, DASH, EQ, DIVIDE, special_sep="(=)"):
    """
    Returns unique equations formatted:
      "lhs_tokens_comma_joined(=)rhs_tokens_comma_joined"

    special_sep is VIRTUAL and does NOT consume any '=' tile.
    '=' tiles in the rack are treated like normal tokens (EQ label).
    """
    full_counts = tiles_to_counts(tiles_arr)
    full_ms = tiles_to_multiset(tiles_arr)

    # Always include EQ in partitions since '=' is a normal tile (if present)
    part_types = ["O", "M", "W", "Z", "DASH", "DIVIDE", "EQ"]
    part_count_map = {k: full_counts.get(k, 0) for k in part_types}

    def split_multiset(ms, left_counts):
        ms = ms.copy()
        left_ms = Counter()

        def take_n(pred, n):
            taken = 0
            for tok in sorted(list(ms.keys())):
                while taken < n and ms.get(tok, 0) > 0 and pred(tok):
                    ms[tok] -= 1
                    if ms[tok] == 0:
                        del ms[tok]
                    left_ms[tok] += 1
                    taken += 1
                if taken == n:
                    break
            return taken == n

        if left_counts.get("Z", 0):
            if not take_n(lambda t: t == "0", left_counts["Z"]): return None, None
        if left_counts.get("W", 0):
            if not take_n(lambda t: t.isdigit() and 1 <= int(t) <= 9, left_counts["W"]): return None, None
        if left_counts.get("M", 0):
            if not take_n(lambda t: t.isdigit() and 10 <= int(t) <= 20, left_counts["M"]): return None, None
        if left_counts.get("DASH", 0):
            if not take_n(lambda t: t == "-", left_counts["DASH"]): return None, None
        if left_counts.get("DIVIDE", 0):
            if not take_n(lambda t: t == "/", left_counts["DIVIDE"]): return None, None
        if left_counts.get("EQ", 0):
            if not take_n(lambda t: t == "=", left_counts["EQ"]): return None, None
        if left_counts.get("O", 0):
            if not take_n(lambda t: t in OPS, left_counts["O"]): return None, None

        right_ms = ms
        return left_ms, right_ms

    equations = set()

    for left_counts, right_counts in unordered_partitions(part_count_map, require_nonempty=True):
        left_ms, right_ms = split_multiset(full_ms, left_counts)
        if left_ms is None:
            continue

        lhs_prune_counts = {
            "O": left_counts.get("O", 0),
            "M": left_counts.get("M", 0),
            "W": left_counts.get("W", 0),
            "Z": left_counts.get("Z", 0),
            DASH: left_counts.get("DASH", 0),
            DIVIDE: left_counts.get("DIVIDE", 0),
            EQ: left_counts.get("EQ", 0),
        }
        rhs_prune_counts = {
            "O": right_counts.get("O", 0),
            "M": right_counts.get("M", 0),
            "W": right_counts.get("W", 0),
            "Z": right_counts.get("Z", 0),
            DASH: right_counts.get("DASH", 0),
            DIVIDE: right_counts.get("DIVIDE", 0),
            EQ: right_counts.get("EQ", 0),
        }

        lhs_G = prune_dag_by_counts(custom_G, lhs_prune_counts, T, S, DASH, EQ, DIVIDE)
        rhs_G = prune_dag_by_counts(custom_G, rhs_prune_counts, T, S, DASH, EQ, DIVIDE)

        lhs_paths = get_terminal_paths_dag(lhs_G, T, S)
        rhs_paths = get_terminal_paths_dag(rhs_G, T, S)

        lhs_exprs = paths_to_expressions_memo(lhs_paths, left_ms)  # memo version
        rhs_exprs = paths_to_expressions_memo(rhs_paths, right_ms)

        for le in lhs_exprs:
            for re in rhs_exprs:
                equations.add(f"{le}{special_sep}{re}")

    return sorted(equations)


# ----------------------------
# Example usage
# ----------------------------
# tiles_arr example:
tiles_arr = ['+', '-', 0, '4', '12', '+', '*', '=']

eqs = generate_all_equations(custom_G, tiles_arr, T=T, S=S, DASH=DASH, EQ=EQ, DIVIDE=DIVIDE)
print("total equations:", len(eqs))
print(eqs[:50])



import time

# ----------------------------
# Example usage
# ----------------------------
# tiles_arr example:
tiles_arr = [0, '-', 3, '4', 3, '+', '/', '9']

num_trials = 10
total_time = 0
eqs = None  # declare ahead so available after loop
for _ in range(num_trials):
    start_time = time.time()
    eqs = generate_all_equations(custom_G, tiles_arr, T=T, S=S, DASH=DASH, EQ=EQ, DIVIDE=DIVIDE)
    end_time = time.time()
    total_time += (end_time - start_time)
print("total equations:", len(eqs))
print(eqs)
avg_time = total_time / num_trials
print(f"Average time over {num_trials} runs: {avg_time:.4f} seconds")

# tiles_arr = [0, '-', 3, '4', 3, '+', '/', '9', '/', '=']

# start_time = time.time()
# eqs = generate_all_equations(custom_G, tiles_arr, T=T, S=S, DASH=DASH, EQ=EQ, DIVIDE=DIVIDE)
# end_time = time.time()
# print("total equations:", len(eqs))
# print(eqs)
# print(f"Time elapsed: {end_time - start_time:.4f} seconds")

# Average time over 10 runs: 0.0802 seconds
# paths_to_expressions_memo seems to make it slightly slower 

# adding condition to remove partitions with oneside having NO numbers -> 0.05 seconds
