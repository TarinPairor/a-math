from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from typing import Iterable, Literal, TypedDict

try:
    from .v4 import Piece, _make_expression_solver, _normalize_tile, _tile_options
except ImportError:  # pragma: no cover - supports running from inside vibes/
    from v4 import Piece, _make_expression_solver, _normalize_tile, _tile_options


def _operator_tile_masks(options: list[tuple[str, ...]], op: str) -> list[int]:
    return [1 << i for i, opts in enumerate(options) if op in opts]


def _has_connector_pair(
    first_masks: list[int],
    second_masks: list[int],
    used_mask: int,
) -> bool:
    for first in first_masks:
        if first & used_mask:
            continue
        for second in second_masks:
            if second & used_mask or second == first:
                continue
            return True
    return False


def _has_connector(connector_masks: list[int], used_mask: int) -> bool:
    return any(not (mask & used_mask) for mask in connector_masks)


def _is_nonnegative_single_term(piece: Piece) -> bool:
    return len(piece.pos) == 1 and not piece.neg and not piece.text.startswith("-")


ExtensionSide = Literal["front", "back"]
Extension = tuple[ExtensionSide, str]


class AdditiveZeroExtensions(TypedDict):
    front: list[str]
    back: list[str]


def _is_legal_extension(side: ExtensionSide, text: str) -> bool:
    if not text:
        return False

    if side == "front":
        if text.startswith("+") or not text.endswith("+"):
            return False
    elif side == "back":
        if text[0] not in "+-":
            return False
    else:
        return False

    body = text[:-1] if side == "front" else text[1:]
    if not body or body.startswith("+"):
        return False
    if body.startswith("0") and len(body) > 1 and body[1].isdigit():
        return False

    return not any(
        bad in text
        for bad in (
            "++",
            "+-",
            "-+",
            "--",
            "*+",
            "*-",
            "/+",
            "/-",
        )
    )


def _pieces_by_value(options: list[tuple[str, ...]]) -> dict[Fraction, list[Piece]]:
    expressions = _make_expression_solver(options)
    full_mask = (1 << len(options)) - 1
    by_value: dict[Fraction, dict[tuple[int, tuple], Piece]] = defaultdict(dict)

    for mask in range(1, full_mask + 1):
        for piece in expressions(mask):
            by_value[piece.value].setdefault((piece.mask, piece.key), piece)

    return {value: list(pieces.values()) for value, pieces in by_value.items()}


def _same_value_disjoint_pairs(
    by_value: dict[Fraction, list[Piece]],
) -> Iterable[tuple[Piece, Piece]]:
    for pieces in by_value.values():
        ordered = sorted(pieces, key=lambda p: (p.key, p.mask))
        for i, left in enumerate(ordered):
            for right in ordered[i + 1 :]:
                if left.mask & right.mask:
                    continue
                yield left, right


# Case 1 + 3:
def generate_zero_extensions(
    tiles: list[object],
    *,
    include_front: bool = True,
    include_back: bool = True,
    max_results: int | None = None,
) -> AdditiveZeroExtensions:
    """Generate zero-valued extension chunks from a rack of A-Math tiles.

    Returns ``{"front": [...], "back": [...]}``. The key tells the caller where
    each chunk can be attached to an existing board expression:

    - back extensions start with a connector, e.g. ``+5-5`` or ``-5+5``
    - front extensions end with a connector, e.g. ``5-5+``

    The search follows the same tile normalization, blank handling, flexible
    operator handling, number combining, and expression evaluation rules as
    ``v4.generate_equations``. Expressions are generated once by value/mask,
    then equal-valued expressions with disjoint masks are paired to produce
    zero-valued additive extensions.
    """
    options = [_tile_options(_normalize_tile(tile)) for tile in tiles]
    plus_masks = _operator_tile_masks(options, "+")
    minus_masks = _operator_tile_masks(options, "-")
    if not plus_masks or not minus_masks:
        return {"front": [], "back": []}

    extensions: set[Extension] = set()
    by_value = _pieces_by_value(options)

    def add(side: ExtensionSide, text: str) -> None:
        if _is_legal_extension(side, text):
            extensions.add((side, text))

    for piece in by_value.get(Fraction(0, 1), []):
        if include_back and not piece.text.startswith("-"):
            if _has_connector(plus_masks, piece.mask):
                add("back", f"+{piece.text}")

        if include_front:
            if _has_connector(plus_masks, piece.mask):
                add("front", f"{piece.text}+")

        if max_results is not None and len(extensions) >= max_results:
            break

    for left, right in _same_value_disjoint_pairs(by_value):
        used_mask = left.mask | right.mask

        if _has_connector_pair(plus_masks, minus_masks, used_mask):
            if include_back:
                add("back", f"+{left.text}-{right.text}")

            if include_front:
                add("front", f"{left.text}-{right.text}+")

        if include_back and _is_nonnegative_single_term(left):
            if _has_connector_pair(minus_masks, plus_masks, used_mask):
                add("back", f"-{left.text}+{right.text}")

        if max_results is not None and len(extensions) >= max_results:
            break

    results = sorted(extensions, key=lambda item: (len(item[1]), item))
    if max_results is not None:
        results = results[:max_results]

    grouped: AdditiveZeroExtensions = {"front": [], "back": []}
    for side, text in results:
        grouped[side].append(text)
    return grouped
