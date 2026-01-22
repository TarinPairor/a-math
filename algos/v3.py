from collections import Counter, deque
import networkx as nx

# ---------------------------
# Token "types" (kept as strings)
# ---------------------------
S = "S"          # start
O = "O"          # operator type: '+' or '*'
DIVIDE = "DV"    # operator type: '/'
DASH = "D"       # operator type: '-'
EQ = "E"         # operator type: '='
M = "M"          # number type: 10-20
W = "W"          # number type: 1-9
Z = "Z"          # number type: 0
T = "T"          # terminal

MAX_DEPTH = 8
MAX_CONTIG_N = 3  # no more than 3 contiguous N's where N ∈ {W,Z,M}

# ---------------------------
# Concrete-to-type helpers
#   You can now use level_filter_arr entries like:
#     [S, 0, None, 2, None, 1, None, ...]
#   Operators can be '+', '*', '/', '-', '='
# ---------------------------
TYPE_TOKENS = {S, O, DIVIDE, DASH, EQ, M, W, Z, T}

def classify(tok):
    """Return the TYPE token for a label which may be a type-token, int, or operator char."""
    if tok in TYPE_TOKENS:
        return tok

    # concrete operators
    if tok == "/" or tok == DIVIDE:
        return DIVIDE
    if tok == "-" or tok == DASH:
        return DASH
    if tok == "=" or tok == EQ:
        return EQ
    if tok == "+" or tok == "*":
        return O

    # concrete numbers
    if isinstance(tok, int):
        if tok == 0:
            return Z
        if 1 <= tok <= 9:
            return W
        if 10 <= tok <= 20:
            return M

    # allow string digits like "0", "7", "12"
    if isinstance(tok, str) and tok.isdigit():
        v = int(tok)
        return classify(v)

    raise ValueError(f"Unrecognized token/label: {tok!r}")

def is_N(tok):
    return classify(tok) in (W, Z, M)

def is_concrete(tok):
    """Concrete means 'not a type token' (e.g., 0, 2, '+', '/', etc.)."""
    return tok not in TYPE_TOKENS

def filter_allows(expected, candidate_type, candidate_label):
    """
    expected:
      - None or "" => allow anything
      - a type token like W/Z/M/O/DV/D/E/S/T => must match type
      - a concrete like 0, 2, 12, '+', '/', '-' => must match exact concrete label
    """
    if expected is None or expected == "":
        return True

    exp_type = classify(expected)
    if exp_type != candidate_type:
        return False

    # If the filter explicitly pins a concrete value, enforce exact match.
    if is_concrete(expected):
        # normalize string digits to int for nicer matching
        if isinstance(expected, str) and expected.isdigit():
            expected_norm = int(expected)
        else:
            expected_norm = expected

        if isinstance(candidate_label, str) and candidate_label.isdigit():
            cand_norm = int(candidate_label)
        else:
            cand_norm = candidate_label

        return cand_norm == expected_norm

    return True

def label_for_child(child_type, expected_at_level):
    """
    Decide the node label to store:
      - if expected pins a concrete value, store that concrete (e.g., 0, 2, '+')
      - otherwise store the type token (e.g., 'W', 'Z', 'O', 'DV')
    """
    if expected_at_level is not None and expected_at_level != "" and is_concrete(expected_at_level):
        # normalize numeric strings
        if isinstance(expected_at_level, str) and expected_at_level.isdigit():
            return int(expected_at_level)
        return expected_at_level
    return child_type

def count_trailing_N(path):
    cnt = 0
    for tok in reversed(path):
        if is_N(tok):
            cnt += 1
        else:
            break
    return cnt

def count_max_contiguous_N(path):
    max_n = 0
    curr = 0
    for tok in path:
        if is_N(tok):
            curr += 1
            max_n = max(max_n, curr)
        else:
            curr = 0
    return max_n

def contains_illegal_wwz(path):
    """
    If we ever see W -> W -> Z (by type), forbid it.
    (Your earlier comment mentioned other allowed followups, but the old code outright forbids WWZ.)
    """
    for i in range(len(path) - 2):
        if classify(path[i]) == W and classify(path[i + 1]) == W and classify(path[i + 2]) == Z:
            return True
    return False

def has_illegal_z_dash_eq(path):
    """Forbidden Z -> DASH -> EQ by type."""
    for i in range(len(path) - 2):
        if classify(path[i]) == Z and classify(path[i + 1]) == DASH and classify(path[i + 2]) == EQ:
            return True
    return False

def can_terminate_inverted(path):
    """
    Same rules as before, but works on mixed labels (types + concrete values).
    """
    if not path or len(path) < 2:
        return False

    # S cannot terminate directly
    if len(path) == 1 and classify(path[0]) == S:
        return False

    # S must be followed by a number (N=W/Z/M)
    if classify(path[0]) == S:
        if len(path) == 2 and classify(path[1]) == T:
            return False
        if len(path) >= 2 and classify(path[1]) != T and not is_N(path[1]):
            return False

    # No >3 contiguous N's anywhere
    if count_max_contiguous_N(path) > MAX_CONTIG_N:
        return False

    last = classify(path[-1])

    # Cannot terminate if last symbol is O, =, or /
    if last in (O, EQ, DIVIDE):
        return False

    # W->Z cannot terminate: must go W->Z->W...
    if len(path) >= 2 and classify(path[-2]) == W and classify(path[-1]) == Z:
        return False

    # cannot terminate on ...Z -> DASH
    if len(path) >= 2 and classify(path[-2]) == Z and classify(path[-1]) == DASH:
        return False

    # Block any Z->DASH->EQ sequence in the path
    if has_illegal_z_dash_eq(path):
        return False

    # If W->W->Z pattern anywhere, forbid
    if contains_illegal_wwz(path):
        return False

    # W->W can only be followed by W or O,/,-,=
    for i in range(len(path) - 2):
        if classify(path[i]) == W and classify(path[i + 1]) == W:
            if classify(path[i + 2]) not in (W, O, DIVIDE, DASH, EQ):
                return False

    # ---- legacy-ish rules, now by type ----

    # 1. S->M->W or =->M->W (by type)
    if len(path) >= 3:
        a, b, c = classify(path[-3]), classify(path[-2]), classify(path[-1])
        if (a == S and b == M and c == W) or (a == EQ and b == M and c == W):
            return False

    # 2. S->W->M or S->M->W
    if len(path) >= 3:
        a, b, c = classify(path[-3]), classify(path[-2]), classify(path[-1])
        if (a == S and b == W and c == M) or (a == S and b == M and c == W):
            return False

    # 3. W streak mismatch around '=' (by type)
    types = [classify(x) for x in path]
    if EQ in types:
        eq_idx = types.index(EQ)
        left_w = 0
        i = eq_idx - 1
        while i >= 0 and types[i] == W:
            left_w += 1
            i -= 1
        right_w = 0
        i = eq_idx + 1
        while i < len(types) and types[i] == W:
            right_w += 1
            i += 1
        if left_w > 0 and right_w > 0 and left_w != right_w:
            return False

    # 4. S/EQ -> W (1 or 3 streak) -> EQ -> M  (by type)
    def check_w_streak_before_eq_and_M(types_):
        if len(types_) >= 4:
            if ((types_[-4] == S and types_[-3] == W and types_[-2] == EQ and types_[-1] == M) or
                (types_[-4] == EQ and types_[-3] == W and types_[-2] == EQ and types_[-1] == M)):
                w_streak = 0
                i = len(types_) - 4
                while i >= 0 and types_[i] == W:
                    w_streak += 1
                    i -= 1
                return w_streak in (1, 3)
        return False

    if check_w_streak_before_eq_and_M(types):
        return False

    # 5. S or EQ -> N DASH EQ OR N EQ DASH (where N is any number-type)
    def is_stream_type(t):
        return t in (M, W, Z)

    if len(types) >= 4:
        a, b, c, d = types[-4], types[-3], types[-2], types[-1]
        if a in (S, EQ) and is_stream_type(b) and c == DASH and d == EQ:
            return False
        if a in (S, EQ) and is_stream_type(b) and c == EQ and d == DASH:
            return False

    return True

# ---------------------------
# Tree builder (labels are mixed: type tokens + concrete chars/ints)
# ---------------------------
def build_inverted_tree(level_filter_arr=None):
    """
    level_filter_arr: list/array length 16 (index = depth)
      - Put None for "don't care"
      - Put a TYPE token like W/Z/M/O/DV/D/E/S/T to constrain by type
      - Or put a CONCRETE value like 0, 2, 12, '+', '/', '-', '=' to pin an exact value at that depth

    Example:
      [S, 0, None, 2, None, 1, None, None, ...]  # length 16
    """
    if level_filter_arr is not None:
        if len(level_filter_arr) != 16:
            raise ValueError("level_filter_arr must be length 16")
        if classify(level_filter_arr[0]) != S:
            raise ValueError("level_filter_arr[0] must be 'S' (type)")

    G = nx.DiGraph()

    def get_node_id(path):
        return tuple(path)

    root_path = [S]
    root_id = get_node_id(root_path)
    G.add_node(root_id, label=S)

    q = deque()
    q.append(root_path)

    while q:
        path = q.popleft()
        cur_label = path[-1]
        cur_type = classify(cur_label)
        cur_id = get_node_id(path)
        depth = len(path) - 1

        # prune by filter (current node)
        if level_filter_arr is not None and depth < len(level_filter_arr):
            expected = level_filter_arr[depth]
            if expected is not None and expected != "":
                if not filter_allows(expected, cur_type, cur_label):
                    continue

        # hard cuts
        if count_max_contiguous_N(path) > MAX_CONTIG_N:
            continue
        if has_illegal_z_dash_eq(path):
            continue

        # terminate if possible
        if depth >= MAX_DEPTH:
            if can_terminate_inverted(path):
                t_path = path + [T]
                t_id = get_node_id(t_path)
                G.add_node(t_id, label=T)
                G.add_edge(cur_id, t_id)
            continue

        if can_terminate_inverted(path):
            t_path = path + [T]
            t_id = get_node_id(t_path)
            if t_id not in G:
                G.add_node(t_id, label=T)
            G.add_edge(cur_id, t_id)

        trailing_N = count_trailing_N(path)

        # choose possible CHILD TYPES based on CURRENT TYPE
        if trailing_N >= MAX_CONTIG_N:
            possible_child_types = [O, DIVIDE, DASH, EQ]
        else:
            if cur_type == S:
                possible_child_types = [W, Z, M]
            elif cur_type == O:
                possible_child_types = [W, Z, M]
            elif cur_type == DIVIDE:
                possible_child_types = [W, Z, M]
            elif cur_type == DASH:
                # if prev is Z, after Z->DASH only N
                if len(path) >= 2 and classify(path[-2]) == Z:
                    possible_child_types = [W, Z, M]
                else:
                    possible_child_types = [W, Z, M, EQ]
            elif cur_type == EQ:
                possible_child_types = [W, Z, M]
            elif cur_type == M:
                possible_child_types = [O, DIVIDE, DASH, EQ]
            elif cur_type == W:
                prev_type = classify(path[-2]) if len(path) >= 2 else None
                if prev_type == W:
                    possible_child_types = [W, O, DIVIDE, DASH, EQ]
                else:
                    possible_child_types = [Z, W, O, DIVIDE, DASH, EQ]
            elif cur_type == Z:
                possible_child_types = [Z, W, O, DASH, EQ]
            else:
                possible_child_types = []

        # expand children
        for child_type in possible_child_types:
            child_depth = depth + 1
            expected_child = level_filter_arr[child_depth] if (level_filter_arr is not None and child_depth < len(level_filter_arr)) else None
            child_label = label_for_child(child_type, expected_child)

            # filter prune (child)
            if level_filter_arr is not None and child_depth < len(level_filter_arr):
                expected = level_filter_arr[child_depth]
                if expected is not None and expected != "":
                    if not filter_allows(expected, child_type, child_label):
                        continue

            # forbid Z->DASH->EQ (by type)
            if len(path) >= 1 and cur_type == DASH and len(path) >= 2 and classify(path[-2]) == Z:
                if child_type == EQ:
                    continue

            # SPECIAL: Z->W forces W to only O,/, -, =
            if cur_type == Z and child_type == W:
                child_path = path + [child_label]
                if count_max_contiguous_N(child_path) > MAX_CONTIG_N:
                    continue

                child_id = get_node_id(child_path)
                if child_id not in G:
                    G.add_node(child_id, label=child_label)
                G.add_edge(cur_id, child_id)

                for forced_type in [O, DIVIDE, DASH, EQ]:
                    forced_depth = depth + 2
                    expected_forced = level_filter_arr[forced_depth] if (level_filter_arr is not None and forced_depth < len(level_filter_arr)) else None
                    forced_label = label_for_child(forced_type, expected_forced)

                    if level_filter_arr is not None and forced_depth < len(level_filter_arr):
                        expected = level_filter_arr[forced_depth]
                        if expected is not None and expected != "":
                            if not filter_allows(expected, forced_type, forced_label):
                                continue

                    forced_path = child_path + [forced_label]
                    if count_max_contiguous_N(forced_path) > MAX_CONTIG_N:
                        continue
                    if has_illegal_z_dash_eq(forced_path):
                        continue

                    forced_id = get_node_id(forced_path)
                    if forced_id not in G:
                        G.add_node(forced_id, label=forced_label)
                    G.add_edge(child_id, forced_id)
                    q.append(forced_path)

                continue

            # SPECIAL: Z->Z forces next W, then W forces O,/, -, =
            if cur_type == Z and child_type == Z:
                child_path = path + [child_label]
                if count_max_contiguous_N(child_path) > MAX_CONTIG_N:
                    continue

                child_id = get_node_id(child_path)
                if child_id not in G:
                    G.add_node(child_id, label=child_label)
                G.add_edge(cur_id, child_id)

                w_depth = depth + 2
                expected_w = level_filter_arr[w_depth] if (level_filter_arr is not None and w_depth < len(level_filter_arr)) else None
                w_label = label_for_child(W, expected_w)

                if level_filter_arr is not None and w_depth < len(level_filter_arr):
                    expected = level_filter_arr[w_depth]
                    if expected is not None and expected != "":
                        if not filter_allows(expected, W, w_label):
                            continue

                zz_w_path = child_path + [w_label]
                if count_max_contiguous_N(zz_w_path) > MAX_CONTIG_N:
                    continue

                zz_w_id = get_node_id(zz_w_path)
                if zz_w_id not in G:
                    G.add_node(zz_w_id, label=w_label)
                G.add_edge(child_id, zz_w_id)

                for forced_type in [O, DIVIDE, DASH, EQ]:
                    forced_depth = depth + 3
                    expected_forced = level_filter_arr[forced_depth] if (level_filter_arr is not None and forced_depth < len(level_filter_arr)) else None
                    forced_label = label_for_child(forced_type, expected_forced)

                    if level_filter_arr is not None and forced_depth < len(level_filter_arr):
                        expected = level_filter_arr[forced_depth]
                        if expected is not None and expected != "":
                            if not filter_allows(expected, forced_type, forced_label):
                                continue

                    forced_path = zz_w_path + [forced_label]
                    if count_max_contiguous_N(forced_path) > MAX_CONTIG_N:
                        continue
                    if has_illegal_z_dash_eq(forced_path):
                        continue

                    forced_id = get_node_id(forced_path)
                    if forced_id not in G:
                        G.add_node(forced_id, label=forced_label)
                    G.add_edge(zz_w_id, forced_id)
                    q.append(forced_path)

                continue

            # SPECIAL: W->Z forces next W
            if cur_type == W and child_type == Z:
                zw_path = path + [child_label]
                if count_max_contiguous_N(zw_path) > MAX_CONTIG_N:
                    continue

                zw_id = get_node_id(zw_path)
                if zw_id not in G:
                    G.add_node(zw_id, label=child_label)
                G.add_edge(cur_id, zw_id)

                w_depth = depth + 2
                expected_w = level_filter_arr[w_depth] if (level_filter_arr is not None and w_depth < len(level_filter_arr)) else None
                w_label = label_for_child(W, expected_w)

                if level_filter_arr is not None and w_depth < len(level_filter_arr):
                    expected = level_filter_arr[w_depth]
                    if expected is not None and expected != "":
                        if not filter_allows(expected, W, w_label):
                            continue

                zw_w_path = zw_path + [w_label]
                if count_max_contiguous_N(zw_w_path) > MAX_CONTIG_N:
                    continue

                zw_w_id = get_node_id(zw_w_path)
                if zw_w_id not in G:
                    G.add_node(zw_w_id, label=w_label)
                G.add_edge(zw_id, zw_w_id)
                q.append(zw_w_path)

                continue

            # GENERAL: forbid W->W->Z (by type)
            if cur_type == W and child_type == Z and len(path) >= 2 and classify(path[-2]) == W:
                continue

            child_path = path + [child_label]

            if count_max_contiguous_N(child_path) > MAX_CONTIG_N:
                continue
            if has_illegal_z_dash_eq(child_path):
                continue
            if contains_illegal_wwz(child_path):
                continue

            child_id = get_node_id(child_path)
            if child_id not in G:
                G.add_node(child_id, label=child_label)
            G.add_edge(cur_id, child_id)
            q.append(child_path)

    # convenience: return labels mapping too (optional)
    node_labels = {n: G.nodes[n].get("label", "") for n in G.nodes}
    return G, node_labels

# ---------------------------
# Terminal path extraction (unchanged)
# ---------------------------
def get_terminal_paths_tree(tree, T, start_node=None):
    """
    Find all paths from the root to terminal nodes labeled T in a tree,
    returning paths as lists of labels (now a MIX of type-tokens and concrete values).
    """
    if start_node is None:
        roots = [n for n in tree.nodes if tree.in_degree(n) == 0]
        if not roots:
            raise ValueError("No root found in the tree.")
        start_node = roots[0]

    results = []

    def dfs(node, path):
        node_label = tree.nodes[node].get("label", "")
        new_path = path + [node_label]
        children = list(tree.successors(node))
        if not children:
            if node_label == T:
                results.append(new_path)
        else:
            for child in children:
                dfs(child, new_path)

    dfs(start_node, [])
    return results

# ---------------------------
# Example usage
# ---------------------------
sample_level_filter = [S, 0, None, 2, None, 1, None, None, None, None, None, None, None, None, None, None]
inverted_G, inverted_labels = build_inverted_tree(sample_level_filter)

terminal_paths_tree = get_terminal_paths_tree(inverted_G, T)
# for p in terminal_paths_tree:
    # print(p)
# print("num paths:", len(terminal_paths_tree))

type_cnt = Counter()
for nodeid in inverted_G.nodes:
    lab = inverted_G.nodes[nodeid].get("label", "")
    type_cnt[str(lab)] += 1
# print("Node labels counts:", type_cnt)
# print("Total nodes:", len(inverted_G.nodes))



import networkx as nx
from collections import Counter, deque

# ---------------------------
# Token "types" (kept as strings)
# ---------------------------
S = "S"
O = "O"          # operator type: '+' or '*'
DIVIDE = "DV"    # operator type: '/'
DASH = "D"       # operator type: '-'
EQ = "E"         # operator type: '='
M = "M"          # number type: 10-20
W = "W"          # number type: 1-9
Z = "Z"          # number type: 0
T = "T"

MAX_DEPTH = 8
MAX_CONTIG_W = 3

TYPE_TOKENS = {S, O, DIVIDE, DASH, EQ, M, W, Z, T}

def classify(tok):
    """Return the TYPE token for a label which may be a type-token, int, or operator char."""
    if tok in TYPE_TOKENS:
        return tok

    # concrete operators
    if tok == "/" or tok == DIVIDE:
        return DIVIDE
    if tok == "-" or tok == DASH:
        return DASH
    if tok == "=" or tok == EQ:
        return EQ
    if tok == "+" or tok == "*":
        return O

    # concrete numbers
    if isinstance(tok, int):
        if tok == 0:
            return Z
        if 1 <= tok <= 9:
            return W
        if 10 <= tok <= 20:
            return M

    # allow string digits like "0", "7", "12"
    if isinstance(tok, str) and tok.isdigit():
        return classify(int(tok))

    raise ValueError(f"Unrecognized token/label: {tok!r}")

def is_concrete(tok):
    """Concrete means 'not a type token' (e.g., 0, 2, '+', '/', etc.)."""
    return tok not in TYPE_TOKENS

def filter_allows(expected, candidate_type, candidate_label):
    """
    expected:
      - None or "" => allow anything
      - a type token like W/Z/M/O/DV/D/E/S/T => must match type
      - a concrete like 0, 2, 12, '+', '/', '-', '=' => must match exact concrete label
    """
    if expected is None or expected == "":
        return True

    exp_type = classify(expected)
    if exp_type != candidate_type:
        return False

    # If pinned to a concrete, enforce exact match
    if is_concrete(expected):
        exp_norm = int(expected) if isinstance(expected, str) and expected.isdigit() else expected
        cand_norm = int(candidate_label) if isinstance(candidate_label, str) and candidate_label.isdigit() else candidate_label
        return cand_norm == exp_norm

    return True

def label_for_child(child_type, expected_at_level):
    """
    If the filter pins a concrete value at that depth, store that concrete in the node label.
    Otherwise store the type token.
    """
    if expected_at_level is not None and expected_at_level != "" and is_concrete(expected_at_level):
        if isinstance(expected_at_level, str) and expected_at_level.isdigit():
            return int(expected_at_level)
        return expected_at_level
    return child_type

# -------------------------------------------------------
# --- your can_terminate stays EXACTLY the same (as asked)
#     IMPORTANT: It expects the TYPE tokens S,O,DASH,EQ,DIVIDE,M,W,Z
#     So we call it with a "typed view" of the mixed-label path.
# -------------------------------------------------------
def can_terminate(path):
    if len(path) == 1 and path[0] == S:
        return False

    if len(path) >= 4 and (path[-4:] == [S, M, EQ, W] or path[-4:] == [EQ, M, EQ, W]):
        return False

    if len(path) >= 4 and (path[-4:] == [S, W, EQ, M] or path[-4:] == [EQ, W, EQ, M]):
        return False

    if EQ in path:
        eq_idx = path.index(EQ)
        left_w = 0
        i = eq_idx - 1
        while i >= 0 and path[i] == W:
            left_w += 1
            i -= 1
        right_w = 0
        i = eq_idx + 1
        while i < len(path) and path[i] == W:
            right_w += 1
            i += 1
        if left_w > 0 and right_w > 0 and left_w != right_w:
            if S in path[:eq_idx - left_w + 1]:
                return False
        if len(path) >= eq_idx + 2:
            if path[0] == EQ and left_w > 0 and right_w > 0 and left_w != right_w:
                return False

    if EQ in path:
        eq_idx = path.index(EQ)
        left_w = 0
        i = eq_idx - 1
        while i >= 0 and path[i] == W:
            left_w += 1
            i -= 1
        if left_w in (1, 3) and eq_idx + 1 < len(path) and path[eq_idx + 1] == M:
            if S in path[:eq_idx - left_w + 1]:
                return False
            if path[0] == EQ:
                return False

    if len(path) >= 4 and ((path[-4] == S and path[-3] == M and path[-2] == EQ) or
                           (path[-4] == EQ and path[-3] == M and path[-2] == EQ)):
        i = len(path) - 1
        w_streak = 0
        while i > -1 and path[i] == W:
            w_streak += 1
            i -= 1
        if w_streak in (1, 3):
            return False

        eq_idx = len(path) - 2
        w_after_eq = 0
        for tok in path[eq_idx + 1:]:
            if tok == W:
                w_after_eq += 1
            else:
                break
        if w_after_eq in (1, 3):
            return False

    if len(path) >= 5:
        if path[-5] == S and path[-4] == DASH and path[-2] == EQ:
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

        if path[-5] == S and path[-3] == EQ and path[-2] == DASH:
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

    if path[-1] in (O, EQ, DASH, DIVIDE):
        return False

    return True

def typed_view(path):
    """Convert a mixed-label path to a pure TYPE-token path for can_terminate()."""
    return [classify(x) for x in path]

def build_custom_tree(level_filter_arr=None):
    """
    Same behavior as your custom TREE, but:
      - level_filter_arr can contain concrete values (0, 2, '+', '/', '-', '=')
      - nodes store concrete labels when pinned, otherwise store type tokens
      - can_terminate() remains unchanged; we feed it typed_view(path)
    """
    G = nx.DiGraph()
    node_labels = {}

    def node_id(path):
        return tuple(path)  # full path identity (no merging)

    # root
    root_path = [S]
    root_id = node_id(root_path)
    G.add_node(root_id, label=S)
    node_labels[root_id] = S

    queue = deque()
    queue.append((root_path, 0))  # (path, w_streak)

    while queue:
        path, w_streak = queue.popleft()
        depth = len(path) - 1
        cur_label = path[-1]
        cur_type = classify(cur_label)
        cur_id = node_id(path)

        # ---- filter prune at current node ----
        if level_filter_arr is not None and depth < len(level_filter_arr):
            expected = level_filter_arr[depth]
            if expected is not None and expected != "":
                if not filter_allows(expected, cur_type, cur_label):
                    continue

        # depth cutoff
        if depth >= MAX_DEPTH:
            if can_terminate(typed_view(path)):
                t_path = path + [T]
                t_id = node_id(t_path)
                if t_id not in G:
                    G.add_node(t_id, label=T)
                    node_labels[t_id] = T
                G.add_edge(cur_id, t_id)
            continue

        # terminate edge if allowed
        if can_terminate(typed_view(path)):
            t_path = path + [T]
            t_id = node_id(t_path)
            if t_id not in G:
                G.add_node(t_id, label=T)
                node_labels[t_id] = T
            G.add_edge(cur_id, t_id)

        def add_child(child_type):
            # pick label (concrete if pinned, else type)
            next_depth = depth + 1
            expected_next = level_filter_arr[next_depth] if (level_filter_arr is not None and next_depth < len(level_filter_arr)) else None
            child_label = label_for_child(child_type, expected_next)

            # filter prune (child)
            if level_filter_arr is not None and next_depth < len(level_filter_arr):
                expected = level_filter_arr[next_depth]
                if expected is not None and expected != "":
                    if not filter_allows(expected, child_type, child_label):
                        return

            # update W streak (based on TYPE!)
            if child_type == W:
                new_ws = w_streak + 1
            else:
                new_ws = 0

            if child_type == W and new_ws > MAX_CONTIG_W:
                return

            child_path = path + [child_label]
            child_id = node_id(child_path)

            if child_id not in G:
                G.add_node(child_id, label=child_label)
                node_labels[child_id] = child_label
                queue.append((child_path, new_ws))

            G.add_edge(cur_id, child_id)

        # Expansion rules (same structure as yours, but based on TYPE)
        if cur_type == S:
            add_child(DASH)
            add_child(M)
            add_child(W)
            add_child(Z)
        elif cur_type == DASH:
            add_child(M)
            add_child(W)
        elif cur_type == EQ:
            add_child(M)
            add_child(W)
            add_child(Z)
            add_child(DASH)
        elif cur_type == M:
            add_child(O)
            add_child(EQ)
            add_child(DIVIDE)
            add_child(DASH)
        elif cur_type == Z:
            # Z->Z only if previous was W (W->Z->Z) by TYPE
            if len(path) >= 2 and classify(path[-2]) == W:
                add_child(Z)
            add_child(O)
            add_child(EQ)
            add_child(DIVIDE)
            add_child(DASH)
        elif cur_type == W:
            add_child(W)
            add_child(Z)
            add_child(O)
            add_child(EQ)
            add_child(DIVIDE)
            add_child(DASH)
        elif cur_type == O:
            add_child(M)
            add_child(W)
            add_child(Z)
        elif cur_type == DIVIDE:
            add_child(M)
            add_child(W)

    return G, node_labels

# ---------------------------
# Example usage
# ---------------------------
# Now you can pin concrete values:
#  - 0 means a Z node stored as 0
#  - 2 means a W node stored as 2
#  - '/' pins DIVIDE and stores '/'
#  - '-' pins DASH and stores '-'
#  - '=' pins EQ and stores '='
#  - '+' or '*' pins O and stores that char
level_filter_arr = [S, 0, None, 2, None, 1, None, None, None, None, None, None, None, None, None, None]

custom_G, custom_labels = build_custom_tree(level_filter_arr)

type_cnt = Counter()
for nodeid in custom_G.nodes:
    lab = custom_G.nodes[nodeid].get("label", "")
    type_cnt[str(lab)] += 1



terminal_paths_tree = get_terminal_paths_tree(custom_G, T)
# for p in terminal_paths_tree:
    # print(p)
# print("num paths:", len(terminal_paths_tree))

type_cnt = Counter()
for nodeid in inverted_G.nodes:
    lab = inverted_G.nodes[nodeid].get("label", "")
    type_cnt[str(lab)] += 1
# print("Node labels counts:", type_cnt)
# print("Total nodes:", len(inverted_G.nodes))


# try:
#     pos = nx.nx_pydot.graphviz_layout(custom_G, prog="dot")
# except Exception:
#     pos = nx.spring_layout(custom_G)

# draw_labels = {k: f"{custom_labels[k]}\n{list(k)}" for k in custom_G.nodes}

# plt.figure(figsize=(20, 14))
# nx.draw(custom_G, pos, with_labels=True, labels=draw_labels, arrows=False,
#         node_size=200, node_color="lightcyan", font_size=8)
# plt.title("Custom TREE (no merging): node id = full path")
# plt.tight_layout(pad=3.0)
# plt.show()



# Given an input mapping (dict) of {type: value}, where sum of values == N,
# for each way to split into (left_sum, right_sum) with left_sum + right_sum = N,
# enumerate all unordered splits of the MULTISET (all items, as individuals) into left_sum/right_sum,
# Each split is described by counts per type in each part; splits that differ by which particular 'M' or 'O'
# are NOT counted as different, so only bag counts matter (unordered multiset partition)
# Example: left: {O:1, M:1}, right: {O:1, M:1, W:3, EQ:1} is different from left: {O:2}, right: {M:2, W:3, EQ:1}, etc.
# 
# Edit: Each side (lhs, rhs) MUST contain at least one of M or W or Z.

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
    left_tuple = tuple((t, left_counts.get(t, 0)) for t in types)
    right_tuple = tuple((t, right_counts.get(t, 0)) for t in types)
    return frozenset([left_tuple, right_tuple])

def is_valid_side(cnt):
    # Require at least one of M, W, or Z
    return (cnt.get("M", 0) > 0) or (cnt.get("W", 0) > 0) or (cnt.get("Z", 0) > 0)

big_sum = 0
for left_sum in range(1, N//2 + 1):
    right_sum = N - left_sum
    seen_partitions = set()
    count = 0
    for left_counts in all_type_count_selections(types, input_mapping, left_sum):
        right_counts = subtract_counts(input_mapping, left_counts)
        # Apply validity conditions: both sides must have at least one M/W/Z
        if not (is_valid_side(left_counts) and is_valid_side(right_counts)):
            continue
        sig = partition_signature(left_counts, right_counts, types)
        if sig in seen_partitions:
            continue
        seen_partitions.add(sig)
        # Only print if both sides have at least one element!
        left_counts_str = ', '.join(f"{k}:{v}" for k, v in left_counts.items() if v > 0)
        right_counts_str = ', '.join(f"{k}:{v}" for k, v in right_counts.items() if v > 0)
        # print(f"Left({left_sum}): {{{left_counts_str}}} | Right({right_sum}): {{{right_counts_str}}}")
        count += 1
    # print(f"Total unordered ways for split {left_sum} + {right_sum}: {count}\n")
    big_sum += count
# print("Sum of all unordered splits across all splits:", big_sum)



import networkx as nx
from collections import Counter
from itertools import product
from functools import lru_cache

# ============================================================
# IMPORTANT: these must match your *tree builders* (types)
# ============================================================
S = "S"
O = "O"          
DIVIDE = "DV"   
DASH = "D"       
EQ = "E"        
M = "M"          # type: 10-20
W = "W"          # type: 1-9
Z = "Z"          # type: 0
T = "T"

TYPE_TOKENS = {S, O, DIVIDE, DASH, EQ, M, W, Z, T}
OPS = {"+", "*"}  # concrete operator tiles

# ------------------------------------------------------------
# If you already defined classify() earlier, reuse it.
# (This version matches your earlier one.)
# ------------------------------------------------------------
def classify(tok):
    if tok in TYPE_TOKENS:
        return tok
    if tok == "/" or tok == DIVIDE:
        return DIVIDE
    if tok == "-" or tok == DASH:
        return DASH
    if tok == "=" or tok == EQ:
        return EQ
    if tok == "+" or tok == "*":
        return O
    if isinstance(tok, int):
        if tok == 0: return Z
        if 1 <= tok <= 9: return W
        if 10 <= tok <= 20: return M
    if isinstance(tok, str) and tok.isdigit():
        return classify(int(tok))
    raise ValueError(f"Unrecognized token/label: {tok!r}")

def is_type_token(x): return x in TYPE_TOKENS

def normalize_concrete(x):
    """Turn node labels into concrete string tokens used in multiset: '6', '+', '-', '/', '='"""
    if isinstance(x, int):
        return str(x)
    if isinstance(x, str) and x.isdigit():
        return str(int(x))
    if x in {"+", "*", "-", "/", "="}:
        return x
    return str(x)

# ============================================================
# 1) Tiles -> counts / multiset  (UPDATED for DV/D/E + concrete)
# ============================================================

def tiles_to_counts(arr):
    """
    Counts by TYPE keys: {O, DASH, DIVIDE, EQ, M, W, Z}
    """
    c = Counter()
    for x in arr:
        s = str(x).strip()
        if s in OPS:
            c[O] += 1
        elif s == "-":
            c[DASH] += 1
        elif s == "/":
            c[DIVIDE] += 1
        elif s == "=":
            c[EQ] += 1
        else:
            try:
                n = int(s)
            except:
                continue
            if n == 0:
                c[Z] += 1
            elif 1 <= n <= 9:
                c[W] += 1
            elif 10 <= n <= 20:
                c[M] += 1
    return dict(c)

def tiles_to_multiset(arr):
    """
    Concrete tile multiset for assignment.
    Uses: '0'..'20', '+','*','-','/','='
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

# ============================================================
# 2) Unordered partitions (unchanged)
# ============================================================

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

def is_valid_side(cnt):
    # Require at least one number tile type
    return (cnt.get(M, 0) > 0) or (cnt.get(W, 0) > 0) or (cnt.get(Z, 0) > 0)

def unordered_partitions(count_map, require_nonempty=True):
    types = list(count_map.keys())
    N = sum(count_map.values())
    start = 1 if require_nonempty else 0
    end = N // 2 + 1

    for left_sum in range(start, end):
        right_sum = N - left_sum
        if require_nonempty and right_sum == 0:
            continue
        seen = set()
        for left_counts in all_type_count_selections(types, count_map, left_sum):
            right_counts = subtract_counts(count_map, left_counts)
            if not (is_valid_side(left_counts) and is_valid_side(right_counts)):
                continue
            sig = partition_signature(left_counts, right_counts, types)
            if sig in seen:
                continue
            seen.add(sig)
            yield left_counts, right_counts

# ============================================================
# 3) Prune TREE by counts (UPDATED: count by TYPE even if label is concrete)
# ============================================================

def prune_tree_by_counts(G, target_counts, T, S):
    """
    target_counts keys are TYPE keys: {O,M,W,Z,DASH,EQ,DIVIDE}
    Counts are applied by type(classify(label)) ONLY for TYPE-TOKEN labels.
    Concrete pinned labels (e.g., 6, '+', '/') are treated as FREE and do not consume counts.
    Root S is never removed even if it becomes a leaf.
    """
    count_keys = {O, M, W, Z, DASH, EQ, DIVIDE}

    # find root
    root = None
    for nodeid in G.nodes:
        if G.nodes[nodeid].get("label", "") == S:
            root = nodeid
            break
    if root is None:
        raise ValueError("No S root node found")

    pruned = nx.DiGraph()

    def dfs(old_node, parent_new, curr_counts: Counter):
        label = G.nodes[old_node].get("label", "")

        nxt = curr_counts.copy()

        # ✅ Only count if this node label is a TYPE TOKEN (not a pinned concrete)
        if is_type_token(label):
            lab_type = label
            if lab_type in count_keys:
                limit = target_counts.get(lab_type, 0)
                if limit <= 0:
                    return
                if curr_counts[lab_type] >= limit:
                    return
                nxt[lab_type] += 1

        # add node
        if old_node not in pruned:
            pruned.add_node(old_node, label=label)
        if parent_new is not None:
            pruned.add_edge(parent_new, old_node)

        children = list(G.successors(old_node))
        if not children:
            # keep leaf only if it's T OR it's the root
            if label != T and old_node != root:
                pruned.remove_node(old_node)
            return

        for ch in children:
            dfs(ch, old_node, nxt)

        # cleanup: if became a non-T leaf after pruning children, drop it (but NEVER drop root)
        if (
            pruned.has_node(old_node)
            and pruned.out_degree(old_node) == 0
            and label != T
            and old_node != root
        ):
            pruned.remove_node(old_node)

    dfs(root, None, Counter())
    return pruned


# ============================================================
# 4) Terminal paths (unchanged)
# ============================================================

def get_terminal_paths_graph(G, T, S, start_node=None):
    if start_node is None:
        for nodeid in G.nodes:
            if G.nodes[nodeid].get("label", "") == S:
                start_node = nodeid
                break
        else:
            raise ValueError("No 'S' node found.")

    results = []
    stack = [(start_node, [])]
    while stack:
        nodeid, path = stack.pop()
        lab = G.nodes[nodeid].get("label", "")
        new_path = path + [lab]
        children = list(G.successors(nodeid))
        if not children:
            if lab == T:
                results.append(new_path)
        else:
            for child in children:
                stack.append((child, new_path))
    return results

# ============================================================
# 5) Assignment: now supports FIXED concrete labels in paths
# ============================================================

def label_choices(label, ms_counter):
    """
    Pinned concrete labels are FREE (board tiles) and do NOT need to exist in tiles_arr.
    Only TYPE labels consume from ms_counter.
    """
    # FREE pinned concrete
    if not is_type_token(label):
        return [normalize_concrete(label)]  # ✅ no rack check

    # TYPE labels consume from rack
    if label == M:
        return [t for t in ms_counter if ms_counter[t] > 0 and t.isdigit() and 10 <= int(t) <= 20]
    if label == W:
        return [t for t in ms_counter if ms_counter[t] > 0 and t.isdigit() and 1 <= int(t) <= 9]
    if label == Z:
        return ["0"] if ms_counter.get("0", 0) > 0 else []

    if label == EQ:
        return ["="] if ms_counter.get("=", 0) > 0 else []
    if label == DASH:
        return ["-"] if ms_counter.get("-", 0) > 0 else []
    if label == DIVIDE:
        return ["/"] if ms_counter.get("/", 0) > 0 else []

    if label == O:
        out = []
        if ms_counter.get("+", 0) > 0: out.append("+")
        if ms_counter.get("*", 0) > 0: out.append("*")
        return out

    return []


def paths_to_expressions(paths, ms_side: Counter):
    """
    ✅ Concrete pinned labels do NOT consume rack tiles.
    Only TYPE tokens consume from ms_side.
    """
    out = set()

    for p in paths:
        core = [x for x in p if x not in (S, T)]  # keep type + concrete

        def rec(i, ms, built):
            if i == len(core):
                out.add(",".join(built))
                return

            lab = core[i]
            for tok in label_choices(lab, ms):
                # If lab is TYPE token, we must consume tok from ms
                if is_type_token(lab):
                    if ms.get(tok, 0) <= 0:
                        continue
                    ms[tok] -= 1
                    if ms[tok] == 0:
                        del ms[tok]

                    rec(i + 1, ms, built + [tok])

                    ms[tok] = ms.get(tok, 0) + 1  # restore
                else:
                    # lab is pinned concrete: free, no consumption
                    rec(i + 1, ms, built + [tok])

        rec(0, ms_side.copy(), [])

    return out


# ============================================================
# 6) End-to-end: NOW accepts LHS/RHS fixed-position filters
# ============================================================

def generate_all_equations(
    inverted_G,          # (optional) LHS tree source
    custom_G,            # (optional) RHS tree source
    tiles_arr,
    T, S,
    lhs_level_filter=None,   # e.g. [S,6,None,...] length 16 (like your tree builder)
    rhs_level_filter=None,   # e.g. [S,6,None,...]
    special_sep="(=)"
):
    """
    If lhs_level_filter / rhs_level_filter are provided, you should pass in
    graphs already built with those filters (recommended), OR you can rebuild
    them outside and pass the built graphs here.

    Output format example:
      a,b,c,6,(=),6,d,e,f
    where the 6's are fixed because the path had concrete 6 labels.
    """
    full_counts = tiles_to_counts(tiles_arr)
    full_ms = tiles_to_multiset(tiles_arr)

    part_types = [O, M, W, Z, DASH, DIVIDE, EQ]
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

        if left_counts.get(Z, 0):
            if not take_n(lambda t: t == "0", left_counts[Z]): return None, None
        if left_counts.get(W, 0):
            if not take_n(lambda t: t.isdigit() and 1 <= int(t) <= 9, left_counts[W]): return None, None
        if left_counts.get(M, 0):
            if not take_n(lambda t: t.isdigit() and 10 <= int(t) <= 20, left_counts[M]): return None, None
        if left_counts.get(DASH, 0):
            if not take_n(lambda t: t == "-", left_counts[DASH]): return None, None
        if left_counts.get(DIVIDE, 0):
            if not take_n(lambda t: t == "/", left_counts[DIVIDE]): return None, None
        if left_counts.get(EQ, 0):
            if not take_n(lambda t: t == "=", left_counts[EQ]): return None, None
        if left_counts.get(O, 0):
            if not take_n(lambda t: t in OPS, left_counts[O]): return None, None

        right_ms = ms
        return left_ms, right_ms

    equations = set()

    for left_counts, right_counts in unordered_partitions(part_count_map, require_nonempty=True):
        left_ms, right_ms = split_multiset(full_ms, left_counts)
        if left_ms is None:
            continue

        lhs_prune_counts = {
            O: left_counts.get(O, 0),
            M: left_counts.get(M, 0),
            W: left_counts.get(W, 0),
            Z: left_counts.get(Z, 0),
            DASH: left_counts.get(DASH, 0),
            DIVIDE: left_counts.get(DIVIDE, 0),
            EQ: left_counts.get(EQ, 0),
        }
        rhs_prune_counts = {
            O: right_counts.get(O, 0),
            M: right_counts.get(M, 0),
            W: right_counts.get(W, 0),
            Z: right_counts.get(Z, 0),
            DASH: right_counts.get(DASH, 0),
            DIVIDE: right_counts.get(DIVIDE, 0),
            EQ: right_counts.get(EQ, 0),
        }

        lhs_G = prune_tree_by_counts(inverted_G, lhs_prune_counts, T, S)
        rhs_G = prune_tree_by_counts(custom_G, rhs_prune_counts, T, S)

        lhs_paths = get_terminal_paths_graph(lhs_G, T, S)
        rhs_paths = get_terminal_paths_graph(rhs_G, T, S)

        lhs_exprs = paths_to_expressions(lhs_paths, left_ms)
        rhs_exprs = paths_to_expressions(rhs_paths, right_ms)

        for le in lhs_exprs:
            for re in rhs_exprs:
                le_reversed = ",".join(le.split(",")[::-1])
                equations.add(f"{le_reversed},{special_sep},{re}")

    return sorted(equations)

# ============================================================
# HOW TO USE WITH FIXED POSITIONS
# ============================================================

# 1) Build filtered trees using YOUR build functions (recommended):
# lhs_filter = [S, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]
# rhs_filter = [S, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]
# inverted_G, _ = build_inverted_tree(lhs_filter)
# custom_G, _   = build_custom_tree(rhs_filter)

# tiles_arr = ['+', '-', 0, '4', '12', 3, '*', '=']   # ✅ no 6,6
# eqs = generate_all_equations(inverted_G, custom_G, tiles_arr, T=T, S=S)
# print(eqs[:20], "total:", len(eqs))


# import random
# import time

# tile_choices = list(range(0, 21)) + ['*', '=', '-', '/', '+']
# num_iterations = 1000
# total_time = 0

# for _ in range(num_iterations):
#     # Randomize tiles_arr to length 8, only 0-20 and specified ops
#     tiles_arr = random.choices(tile_choices, k=8)
#     start_time = time.time()
#     eqs = generate_all_equations(
#         inverted_G=inverted_G,
#         custom_G=custom_G,
#         tiles_arr=tiles_arr,
#         T=T, S=S, DASH=DASH, EQ=EQ, DIVIDE=DIVIDE
#     )
#     end_time = time.time()
#     total_time += (end_time - start_time)

# avg_time = total_time / num_iterations
# print(f"Average time to generate equations (10 runs): {avg_time:.4f} seconds")

# Average time to generate equations (10 runs): 0.0150 seconds




# from simpleeval import simple_eval
# import re
# def eval_eq(s):
#     s1 = re.sub(',','',s)
#     s2 = re.sub('\(=\)', '=', s1) 
#     s3 = re.sub('=', '==', s2)   
#     return simple_eval(s3)  
#     # return s3     

# correct_eqs = [s for s in eqs if eval_eq(s)]
# # For every equation in correct_eqs ("lhs,(=),rhs"), add both lhs,(=),rhs and rhs,(=),lhs as unique forms
# mirrored_eqs = set()
# for eq in correct_eqs:
#     lhs, rhs = eq.split('(=)')
#     lhs = lhs.strip(',') 
#     rhs = rhs.strip(',')
#     mirrored = f"{rhs},(=),{lhs}"
#     mirrored_eqs.add(mirrored)
#     mirrored_eqs.add(eq)
# sorted(mirrored_eqs)


# def constraint_eq(s, lhs_len, rhs_len):
#     a, b = s.split('(=)')[0], s.split('(=)')[1]
#     a = [x for x in re.split(',', a) if x]
#     b = [x for x in re.split(',', b) if x]
#     return len(a) <= lhs_len and len(b) <= rhs_len

# constrained_eq = [s for s in mirrored_eqs if constraint_eq(s, 3, 16)]