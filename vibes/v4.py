from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from itertools import permutations
from typing import Iterable


@dataclass(frozen=True)
class Piece:
    mask: int
    text: str
    value: Fraction
    key: tuple
    nums: tuple[str, ...] = ()
    dens: tuple[str, ...] = ()
    pos: tuple[tuple, ...] = ()
    neg: tuple[tuple, ...] = ()


OPS = {"+", "-", "*", "/"}


def _normalize_tile(tile: object) -> str:
    s = str(tile).strip()
    aliases = {
        "×": "*",
        "x": "*",
        "X": "*",
        "÷": "/",
        "±": "+/-",
        "+/": "+/-",
        "*/": "*/",
        "×/÷": "*/",
        "×÷": "*/",
    }
    return aliases.get(s, s)


def _tile_options(tile: object) -> tuple[str, ...]:
    s = _normalize_tile(tile)
    if s == "?":
        return tuple([str(i) for i in range(21)] + ["+", "-", "*", "/", "="])
    if s == "+/-":
        return ("+", "-")
    if s == "*/":
        return ("*", "/")
    return (s,)


def _term_text(nums: tuple[str, ...], dens: tuple[str, ...]) -> str:
    text = "*".join(nums)
    if dens:
        text += "/" + "/".join(dens)
    return text


def _expr_text(pos: tuple[tuple, ...], neg: tuple[tuple, ...]) -> str:
    parts: list[str] = []
    for term_key in pos:
        parts.append(term_key[3])
    for term_key in neg:
        text = term_key[3]
        if parts:
            parts.append("-" + text)
        else:
            parts.append("-" + text)
    return "+".join(parts).replace("+-", "-")


def _build_number_atoms(options: list[tuple[str, ...]]) -> list[Piece]:
    numeric_by_index: list[tuple[int, list[int]]] = []
    for i, opts in enumerate(options):
        nums = sorted({int(o) for o in opts if o.isdigit() and 0 <= int(o) <= 20})
        if nums:
            numeric_by_index.append((i, nums))

    atoms: dict[tuple[int, str], Piece] = {}

    for i, nums in numeric_by_index:
        mask = 1 << i
        for n in nums:
            text = str(n)
            key = ("num", text)
            atoms[(mask, text)] = Piece(
                mask,
                text,
                Fraction(n, 1),
                key,
                nums=(text,),
                pos=(("term", (text,), (), text),),
            )

    digit_choices = [
        (i, [n for n in nums if 0 <= n <= 9]) for i, nums in numeric_by_index
    ]
    digit_choices = [(i, nums) for i, nums in digit_choices if nums]

    for width in (2, 3):
        for chosen in permutations(digit_choices, width):
            indices = [i for i, _ in chosen]
            if len(set(indices)) != width:
                continue

            def rec(pos: int, digits: list[int]) -> None:
                if pos == width:
                    if digits[0] == 0:
                        return
                    text = "".join(str(d) for d in digits)
                    mask = 0
                    for idx in indices:
                        mask |= 1 << idx
                    key = ("num", text)
                    atoms[(mask, text)] = Piece(
                        mask,
                        text,
                        Fraction(int(text), 1),
                        key,
                        nums=(text,),
                        pos=(("term", (text,), (), text),),
                    )
                    return

                for digit in chosen[pos][1]:
                    digits.append(digit)
                    rec(pos + 1, digits)
                    digits.pop()

            rec(0, [])

    minus_indices = [i for i, opts in enumerate(options) if "-" in opts]
    positive_atoms = list(atoms.values())
    for atom in positive_atoms:
        if atom.value == 0:
            continue
        for minus_i in minus_indices:
            minus_mask = 1 << minus_i
            if atom.mask & minus_mask:
                continue
            mask = atom.mask | minus_mask
            text = "-" + atom.text
            key = ("num", text)
            atoms[(mask, text)] = Piece(
                mask,
                text,
                -atom.value,
                key,
                nums=(text,),
                pos=(("term", (text,), (), text),),
            )

    return list(atoms.values())


def _make_expression_solver(options: list[tuple[str, ...]]):
    atoms = _build_number_atoms(options)
    atom_by_mask: dict[int, list[Piece]] = defaultdict(list)
    for atom in atoms:
        atom_by_mask[atom.mask].append(atom)
    atom_masks = sorted(atom_by_mask)

    op_indices: dict[str, list[int]] = {op: [] for op in OPS}
    for i, opts in enumerate(options):
        for op in OPS:
            if op in opts:
                op_indices[op].append(i)

    @lru_cache(maxsize=None)
    def terms(mask: int) -> tuple[Piece, ...]:
        out: dict[tuple[Fraction, tuple], Piece] = {}
        for atom in atom_by_mask.get(mask, []):
            term_key = ("term", atom.nums, atom.dens, atom.text)
            out[(atom.value, term_key)] = Piece(
                atom.mask,
                atom.text,
                atom.value,
                term_key,
                nums=atom.nums,
                dens=atom.dens,
                pos=(term_key,),
            )

        for op in ("*", "/"):
            for op_i in op_indices[op]:
                op_mask = 1 << op_i
                if not (mask & op_mask):
                    continue
                rem = mask ^ op_mask
                for atom_mask in atom_masks:
                    if atom_mask == rem or (atom_mask & rem) != atom_mask:
                        continue
                    left_mask = rem ^ atom_mask
                    if left_mask == 0:
                        continue
                    for atom in atom_by_mask[atom_mask]:
                        if op == "/" and atom.value == 0:
                            continue
                        for left in terms(left_mask):
                            value = (
                                left.value * atom.value
                                if op == "*"
                                else left.value / atom.value
                            )
                            nums = left.nums
                            dens = left.dens
                            if op == "*":
                                nums = tuple(sorted(nums + atom.nums))
                            else:
                                dens = tuple(sorted(dens + atom.nums))
                            text = _term_text(nums, dens)
                            term_key = ("term", nums, dens, text)
                            out.setdefault(
                                (value, term_key),
                                Piece(
                                    mask,
                                    text,
                                    value,
                                    term_key,
                                    nums=nums,
                                    dens=dens,
                                    pos=(term_key,),
                                ),
                            )

        return tuple(out.values())

    @lru_cache(maxsize=None)
    def expressions(mask: int) -> tuple[Piece, ...]:
        out: dict[tuple[Fraction, tuple], Piece] = {}
        for piece in terms(mask):
            expr_key = ("expr", piece.pos, ())
            out[(piece.value, expr_key)] = Piece(
                piece.mask,
                piece.text,
                piece.value,
                expr_key,
                pos=piece.pos,
                neg=(),
            )

        for op in ("+", "-"):
            for op_i in op_indices[op]:
                op_mask = 1 << op_i
                if not (mask & op_mask):
                    continue
                rem = mask ^ op_mask
                sub = rem
                while sub:
                    left_mask = sub
                    term_mask = rem ^ left_mask
                    if term_mask:
                        for term in terms(term_mask):
                            if term.text.startswith("-"):
                                continue
                            for left in expressions(left_mask):
                                value = (
                                    left.value + term.value
                                    if op == "+"
                                    else left.value - term.value
                                )
                                if op == "+":
                                    pos = tuple(sorted(left.pos + term.pos))
                                    neg = left.neg
                                else:
                                    pos = left.pos
                                    neg = tuple(sorted(left.neg + term.pos))
                                text = _expr_text(pos, neg)
                                expr_key = ("expr", pos, neg)
                                out.setdefault(
                                    (value, expr_key),
                                    Piece(mask, text, value, expr_key, pos=pos, neg=neg),
                                )
                    sub = (sub - 1) & rem

        return tuple(out.values())

    return expressions


def _build_expressions(options: list[tuple[str, ...]]) -> dict[Fraction, list[Piece]]:
    expressions = _make_expression_solver(options)
    full_mask = (1 << len(options)) - 1
    by_value: dict[Fraction, list[Piece]] = defaultdict(list)
    for mask in range(1, full_mask + 1):
        for piece in expressions(mask):
            by_value[piece.value].append(piece)

    return by_value


def _iter_submasks(mask: int) -> Iterable[int]:
    sub = mask
    while sub:
        yield sub
        sub = (sub - 1) & mask


def _partitions(mask: int, count: int, min_mask: int = 1) -> Iterable[tuple[int, ...]]:
    if count == 1:
        if mask >= min_mask:
            yield (mask,)
        return

    for sub in _iter_submasks(mask):
        if sub < min_mask:
            continue
        rem = mask ^ sub
        if rem == 0:
            continue
        for rest in _partitions(rem, count - 1, sub + 1):
            yield (sub,) + rest


def _eq_separator_masks(eq_masks: list[int], count: int) -> Iterable[int]:
    def rec(start: int, left: int, mask: int) -> Iterable[int]:
        if left == 0:
            yield mask
            return
        for i in range(start, len(eq_masks) - left + 1):
            yield from rec(i + 1, left - 1, mask | eq_masks[i])

    yield from rec(0, count, 0)


def _ordered_chains(
    pieces: list[Piece],
    eq_masks: list[int],
    full_mask: int,
    use_all: bool,
    max_results: int | None,
) -> Iterable[str]:
    pieces = sorted(pieces, key=lambda p: (p.key, p.mask))
    out_count = 0

    def rec(start: int, chosen: list[Piece], used_mask: int) -> Iterable[str]:
        nonlocal out_count
        available_eq_masks = [mask for mask in eq_masks if not (mask & used_mask)]

        if len(chosen) >= 2:
            eq_needed = len(chosen) - 1
            has_enough_equals = len(available_eq_masks) >= eq_needed
            consumes_all = True
            if use_all:
                unused = full_mask & ~used_mask
                consumes_all = (
                    unused.bit_count() == eq_needed
                    and sum(1 for mask in available_eq_masks if mask & unused)
                    == eq_needed
            )
            if has_enough_equals and consumes_all:
                out_count += 1
                yield "=".join(
                    p.text for p in sorted(chosen, key=lambda p: (p.key, p.mask))
                )
                if max_results is not None and out_count >= max_results:
                    return

        if len(chosen) == len(available_eq_masks) + 1:
            return

        for i in range(start, len(pieces)):
            piece = pieces[i]
            if piece.mask & used_mask:
                continue
            yield from rec(i + 1, chosen + [piece], used_mask | piece.mask)
            if max_results is not None and out_count >= max_results:
                return

    yield from rec(0, [], 0)


def generate_equations(
    tiles: list[object],
    *,
    use_all: bool = True,
    max_results: int | None = None,
) -> list[str]:
    """Generate valid A-Math equations from a rack of tiles.

    The search uses exact Fraction arithmetic and bitmasks to ensure that no
    physical tile is reused. Flexible +/- and */ tiles are resolved lazily by
    checking each tile's legal options. Blank tiles may become 0..20 or an
    operator, but at least one original '=' tile is required by the stated rule.
    """
    if not any(_normalize_tile(tile) == "=" for tile in tiles):
        return []

    options = [_tile_options(tile) for tile in tiles]
    eq_masks = [1 << i for i, opts in enumerate(options) if "=" in opts]
    if not eq_masks:
        return []

    full_mask = (1 << len(tiles)) - 1
    equations: set[str] = set()
    original_eq_mask = 0
    for i, tile in enumerate(tiles):
        if _normalize_tile(tile) == "=":
            original_eq_mask |= 1 << i

    if use_all:
        expressions = _make_expression_solver(options)
        max_sides = len(eq_masks) + 1

        for side_count in range(2, max_sides + 1):
            for sep_mask in _eq_separator_masks(eq_masks, side_count - 1):
                if (sep_mask & original_eq_mask) != original_eq_mask:
                    continue
                expr_mask = full_mask ^ sep_mask
                for masks in _partitions(expr_mask, side_count):
                    side_maps: list[dict[Fraction, list[Piece]]] = []
                    common_values: set[Fraction] | None = None
                    for mask in masks:
                        by_value_for_mask: dict[Fraction, list[Piece]] = defaultdict(
                            list
                        )
                        for piece in expressions(mask):
                            by_value_for_mask[piece.value].append(piece)
                        if not by_value_for_mask:
                            break
                        values = set(by_value_for_mask)
                        common_values = (
                            values
                            if common_values is None
                            else common_values & values
                        )
                        if not common_values:
                            break
                        side_maps.append(by_value_for_mask)
                    else:
                        assert common_values is not None
                        for value in common_values:
                            chosen: list[Piece] = []

                            def rec(i: int) -> bool:
                                if i == len(side_maps):
                                    equation = "=".join(
                                        p.text
                                        for p in sorted(
                                            chosen, key=lambda p: (p.key, p.mask)
                                        )
                                    )
                                    equations.add(equation)
                                    return (
                                        max_results is not None
                                        and len(equations) >= max_results
                                    )

                                for piece in side_maps[i][value]:
                                    chosen.append(piece)
                                    should_stop = rec(i + 1)
                                    chosen.pop()
                                    if should_stop:
                                        return True
                                return False

                            if rec(0):
                                return sorted(equations, key=lambda s: (len(s), s))

        return sorted(equations, key=lambda s: (len(s), s))

    by_value = _build_expressions(options)

    for pieces in by_value.values():
        if len(pieces) < 2:
            continue
        for equation in _ordered_chains(pieces, eq_masks, full_mask, use_all, max_results):
            equations.add(equation)
            if max_results is not None and len(equations) >= max_results:
                return sorted(equations, key=lambda s: (len(s), s))

    return sorted(equations, key=lambda s: (len(s), s))
