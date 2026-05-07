import argparse
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - fallback for offline environments
    yaml = None


def _parse_inline_value(value: str):
    value = value.strip()
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_inline_value(part.strip()) for part in inner.split(",")]
    if value.startswith("{") and value.endswith("}"):
        inner = value[1:-1].strip()
        if not inner:
            return {}
        result = {}
        for segment in inner.split(","):
            key, _, val = segment.partition(":")
            result[key.strip()] = _parse_inline_value(val.strip())
        return result
    return value.strip("\"'")


def simple_yaml_load(text: str):  # pragma: no cover - used when PyYAML is unavailable
    lines = [line.rstrip("\n") for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]

    def parse_block(start: int, indent: int):
        i = start
        mapping = {}
        sequence = []
        is_list = None

        while i < len(lines):
            line = lines[i]
            current_indent = len(line) - len(line.lstrip(" "))
            if current_indent < indent:
                break
            stripped = line.strip()

            if stripped.startswith("-"):
                if is_list is False:
                    raise ValueError("Mixed mapping and list at same indentation level")
                is_list = True
                content = stripped[1:].strip()
                if content:
                    if ":" in content:
                        key, _, rest = content.partition(":")
                        entry = {key.strip(): _parse_inline_value(rest.strip())} if rest.strip() else {}
                        value, i = parse_block(i + 1, indent + 2)
                        if isinstance(value, dict):
                            entry.update(value)
                        elif value:
                            raise ValueError("Expected mapping content in list item")
                        sequence.append(entry)
                        continue
                    sequence.append(_parse_inline_value(content))
                    i += 1
                    continue
                value, i = parse_block(i + 1, indent + 2)
                sequence.append(value)
                continue

            if is_list is True:
                raise ValueError("Mixed mapping and list at same indentation level")
            is_list = False
            key, _, rest = stripped.partition(":")
            if rest.strip():
                mapping[key.strip()] = _parse_inline_value(rest.strip())
                i += 1
                continue
            value, i = parse_block(i + 1, indent + 2)
            mapping[key.strip()] = value

        return (sequence if is_list else mapping), i

    result, _ = parse_block(0, 0)
    return result


@dataclass
class OutputConfig:
    out_dir: Path
    file_prefix: str


@dataclass
class WorksheetConfig:
    header_left_label: str
    header_right_label: str
    tasks: List[Dict]
    page_title: str = ""


@dataclass
class Config:
    base_seed: int
    worksheet_count: int
    output: OutputConfig
    worksheet: WorksheetConfig


def load_config(path: Path) -> Config:
    with path.open("r", encoding="utf-8") as f:
        content = f.read()
        if yaml:
            raw = yaml.safe_load(content)
        else:
            raw = simple_yaml_load(content)

    output_cfg = raw.get("output", {})
    worksheet_cfg = raw.get("worksheet", {})

    return Config(
        base_seed=int(raw.get("base_seed", 0)),
        worksheet_count=int(raw.get("worksheet_count", 1)),
        output=OutputConfig(
            out_dir=Path(output_cfg.get("out_dir", "out")),
            file_prefix=str(output_cfg.get("file_prefix", "worksheet")),
        ),
        worksheet=WorksheetConfig(
            header_left_label=str(worksheet_cfg.get("header_left_label", "Name")),
            header_right_label=str(worksheet_cfg.get("header_right_label", "Datum")),
            tasks=list(worksheet_cfg.get("tasks", [])),
            page_title=str(worksheet_cfg.get("page_title", "")),
        ),
    )


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ---------- Task generation helpers ----------

def generate_number_dictation(data: Dict, rng: random.Random) -> Dict:
    box_count = int(data.get("box_count", 10))
    numbers = [rng.randint(20, 100) for _ in range(box_count)]
    return {
        "box_count": box_count,
        "numbers": numbers,
        "show_helper_numbers": bool(data.get("show_helper_numbers", False)),
        "title": data.get("title", "Zahlendiktat"),
    }


def generate_compare_numbers(data: Dict, rng: random.Random) -> Dict:
    item_count = int(data.get("item_count", 6))
    min_value = max(0, int(data.get("min_value", 0)))
    max_value = min(100, int(data.get("max_value", 100)))
    if min_value > max_value:
        min_value, max_value = max_value, min_value
    columns = int(data.get("columns", 3))
    equal_probability = max(0.0, min(1.0, float(data.get("equal_probability", 0.05))))

    items = []
    for _ in range(item_count):
        if rng.random() < equal_probability:
            value = rng.randint(min_value, max_value)
            items.append((value, value, "="))
            continue

        a = rng.randint(min_value, max_value)
        b = rng.randint(min_value, max_value)
        while a == b:
            b = rng.randint(min_value, max_value)
        items.append((a, b, "<" if a < b else ">"))

    return {
        "title": data.get("title", "Vergleiche! <, >, ="),
        "items": items,
        "columns": columns,
    }


def _choose_middle_value(rng: random.Random, min_value: int, max_value: int) -> int:
    if max_value - min_value < 2:
        raise ValueError("Range too small for predecessor/successor table")
    return rng.randint(min_value + 1, max_value - 1)


def generate_pre_succ_table(data: Dict, rng: random.Random) -> Dict:
    row_count = int(data.get("row_count", 6))
    min_value = max(10, int(data.get("min_value", 10)))
    max_value = min(100, int(data.get("max_value", 100)))
    if min_value > max_value:
        min_value, max_value = max_value, min_value
    given_field = data.get("given_field", "middle")

    min_value = max(min_value, 10)
    max_value = min(max_value, 100)
    if max_value - min_value < 2:
        raise ValueError("Range too small for predecessor/successor table")

    rows = []
    for _ in range(row_count):
        middle_value = _choose_middle_value(rng, min_value, max_value)
        current_given = given_field
        if given_field == "mixed":
            current_given = rng.choice(["left", "middle", "right"])
        predecessor = middle_value - 1
        successor = middle_value + 1
        rows.append({
            "given_field": current_given,
            "values": {
                "left": predecessor,
                "middle": middle_value,
                "right": successor,
            },
        })

    return {
        "title": data.get("title", "Vorgänger / Zahl / Nachfolger"),
        "rows": rows,
    }


def generate_arithmetic_list(data: Dict, rng: random.Random) -> Dict:
    item_count = int(data.get("item_count", 8))
    operations = data.get("operations", ["+", "-"])
    min_value = int(data.get("min_value", 0))
    max_value = int(data.get("max_value", 20))
    allow_negative = bool(data.get("allow_negative_results", False))
    columns = int(data.get("columns", 2))
    cross_ten_probability = max(0.0, min(1.0, float(data.get("cross_ten_probability", 1.0))))
    max_second_operand = max(0, min(int(data.get("max_second_operand", 10)), max_value))
    min_second_operand = max(0, int(data.get("min_second_operand", 0)))
    if min_second_operand > max_second_operand:
        min_second_operand = max_second_operand
    answer_cells = max(1, int(data.get("answer_cells", 1)))
    extra_rows = max(0, int(data.get("extra_rows", 0)))
    result_max_raw = data.get("result_max")
    result_max = int(result_max_raw) if result_max_raw is not None else None
    cell_question = bool(data.get("cell_question", False))
    total_cells_raw = data.get("total_cells")
    total_cells = int(total_cells_raw) if total_cells_raw is not None else None
    fixed_operand_values = data.get("fixed_operand_values")
    if fixed_operand_values is not None:
        fixed_operand_values = [int(v) for v in fixed_operand_values]
    fixed_operand_position = data.get("fixed_operand_position", "any")  # "a", "b", "any"

    def is_crossing_ten_add(x: int, y: int) -> bool:
        ones_sum = (x % 10) + (y % 10)
        return ones_sum > 10

    def is_crossing_ten_subtract(x: int, y: int) -> bool:
        minuend_ones = x % 10
        if minuend_ones == 0:
            return False
        return minuend_ones < (y % 10)

    def generate_candidate(op_symbol: str, require_cross: bool) -> Optional[Tuple[int, int, int]]:
        max_attempts = 500
        for _ in range(max_attempts):
            if fixed_operand_values:
                if fixed_operand_position == "a":
                    a = rng.choice(fixed_operand_values)
                    b = rng.randint(min_second_operand, max_second_operand)
                elif fixed_operand_position == "b":
                    a = rng.randint(min_value, max_value)
                    b = rng.choice(fixed_operand_values)
                else:  # any -> randomly pick which side gets the fixed value
                    if rng.random() < 0.5:
                        a = rng.choice(fixed_operand_values)
                        b = rng.randint(min_second_operand, max_second_operand)
                    else:
                        a = rng.randint(min_value, max_value)
                        b = rng.choice(fixed_operand_values)
            else:
                a = rng.randint(min_value, max_value)
                b = rng.randint(min_second_operand, max_second_operand)
            if op_symbol == "+":
                result = a + b
            elif op_symbol == "-":
                result = a - b
            elif op_symbol == "·":
                result = a * b
            else:
                raise ValueError(f"Unsupported operation: {op_symbol}")

            if not allow_negative and result < 0:
                continue
            if op_symbol in ("+", "-"):
                if result < min_value or result > max_value:
                    continue
            if result_max is not None and result > result_max:
                continue

            if op_symbol in ("+", "-"):
                crossing = is_crossing_ten_add(a, b) if op_symbol == "+" else is_crossing_ten_subtract(a, b)
                if require_cross and not crossing:
                    continue
                if not require_cross and crossing:
                    continue
            return a, b, result
        return None

    items: List[Tuple[int, str, int, int]] = []
    while len(items) < item_count:
        op = rng.choice(operations)
        wants_cross = rng.random() < cross_ten_probability
        candidate = generate_candidate(op, wants_cross)

        if candidate is None:
            # try the opposite crossing requirement to avoid getting stuck
            candidate = generate_candidate(op, not wants_cross)
        if candidate is None:
            raise ValueError("Unable to generate arithmetic item with given constraints")

        a, b, result = candidate
        items.append((a, op, b, result))

    return {
        "title": data.get("title", "Rechne! Achte auf das Rechenzeichen!"),
        "items": items,
        "columns": columns,
        "answer_cells": answer_cells,
        "extra_rows": extra_rows,
        "cell_question": cell_question,
        "total_cells": total_cells,
        "compact": bool(data.get("compact", False)),
    }


GERMAN_UNDER_20 = [
    "null",
    "eins",
    "zwei",
    "drei",
    "vier",
    "fünf",
    "sechs",
    "sieben",
    "acht",
    "neun",
    "zehn",
    "elf",
    "zwölf",
    "dreizehn",
    "vierzehn",
    "fünfzehn",
    "sechzehn",
    "siebzehn",
    "achtzehn",
    "neunzehn",
]

TENS = {
    20: "zwanzig",
    30: "dreißig",
    40: "vierzig",
    50: "fünfzig",
    60: "sechzig",
    70: "siebzig",
    80: "achtzig",
    90: "neunzig",
}


def number_to_word(value: int) -> str:
    if value < 20:
        return GERMAN_UNDER_20[value]
    tens = value // 10 * 10
    ones = value % 10
    if ones == 0:
        return TENS[tens]
    if ones == 1:
        return f"einund{TENS[tens]}"
    return f"{GERMAN_UNDER_20[ones]}und{TENS[tens]}"


def underline_and_segment(word: str) -> str:
    return word.replace("und", "<span class='number-word-and'>und</span>")


def _dice_svg(face_value: int) -> str:
    pip_positions = {
        1: [(50, 50)],
        2: [(25, 25), (75, 75)],
        3: [(25, 25), (50, 50), (75, 75)],
        4: [(25, 25), (75, 25), (25, 75), (75, 75)],
        5: [(25, 25), (75, 25), (50, 50), (25, 75), (75, 75)],
        6: [(25, 25), (75, 25), (25, 50), (75, 50), (25, 75), (75, 75)],
    }
    circles = "".join(
        f"<circle cx='{x}' cy='{y}' r='8' />" for x, y in pip_positions.get(face_value, [])
    )
    return "<svg class='dice-svg' viewBox='0 0 100 100' role='img' aria-label='Würfel'>" f"{circles}</svg>"


def _dot_group_svg(size: int) -> str:
    width = 100
    height = 80
    if size <= 0:
        return f"<svg class='dot-group-svg' viewBox='0 0 {width} {height}'></svg>"
    cols = math.ceil(size / 2) if size > 4 else size
    rows = 2 if size > 4 else 1
    inner_left = 14
    inner_right = width - 14
    inner_top = 14
    inner_bottom = height - 14
    cell_w = (inner_right - inner_left) / max(cols, 1)
    cell_h = (inner_bottom - inner_top) / max(rows, 1)
    parts: List[str] = [
        f"<rect x='6' y='6' width='{width - 12}' height='{height - 12}' rx='14' ry='14' "
        f"fill='none' stroke='#000' stroke-width='2'/>"
    ]
    items_in_top_row = cols if rows == 2 else size
    for i in range(size):
        if rows == 2:
            r_idx = 0 if i < items_in_top_row else 1
            c_idx = i if r_idx == 0 else (i - items_in_top_row)
            row_count = items_in_top_row if r_idx == 0 else (size - items_in_top_row)
        else:
            r_idx = 0
            c_idx = i
            row_count = size
        cell_w_row = (inner_right - inner_left) / max(row_count, 1)
        cx = inner_left + cell_w_row * (c_idx + 0.5)
        cy = inner_top + cell_h * (r_idx + 0.5)
        parts.append(f"<circle cx='{cx:.1f}' cy='{cy:.1f}' r='5' fill='#000'/>")
    return (
        f"<svg class='dot-group-svg' viewBox='0 0 {width} {height}' role='img' aria-label='Punktgruppe'>"
        f"{''.join(parts)}</svg>"
    )


def _placeholder_dice_svg() -> str:
    return (
        "<svg class='dice-svg dice-placeholder' viewBox='0 0 100 100' role='presentation'>"
        "<rect x='0' y='0' width='100' height='100' fill='#fff' stroke='#fff' /></svg>"
    )


def _tally_svg(count: int) -> str:
    if count <= 0:
        return ""

    top_margin = 5
    line_height = 90
    bottom_margin = 5
    line_spacing = 10
    group_gap = 16

    groups: List[int] = []
    remaining = count
    while remaining > 0:
        groups.append(min(5, remaining))
        remaining -= groups[-1]

    x = 5
    lines = []
    for idx, group_size in enumerate(groups):
        for _ in range(group_size):
            lines.append(
                f"<line x1='{x}' y1='{top_margin}' x2='{x}' y2='{top_margin + line_height}' class='tally-line' />"
            )
            x += line_spacing
        if idx < len(groups) - 1:
            x += group_gap

    width = x + 5
    height = top_margin + line_height + bottom_margin
    return (
        f"<svg class='tally-svg' viewBox='0 0 {width} {height}' role='img' aria-label='Zehner-Striche'>"
        f"{''.join(lines)}</svg>"
    )


def _ones_as_dice_faces(ones: int) -> List[str]:
    faces: List[str] = []
    while ones >= 5:
        faces.append(_dice_svg(5))
        ones -= 5
    if ones:
        faces.append(_dice_svg(ones))
    return faces


def dice_representation(value: int) -> str:
    tens = value // 10
    ones = value % 10
    tally_svg = _tally_svg(tens)
    dice_faces = _ones_as_dice_faces(ones)
    if not dice_faces:
        dice_faces.append(_placeholder_dice_svg())

    tally_html = f"<span class='tallies'>{tally_svg}</span>" if tally_svg else ""
    dice_html = "".join(f"<span class='dice-face'>{face}</span>" for face in dice_faces)

    if tally_html and dice_html:
        return f"<div class='dice-combo'>{tally_html}<span class='dice-faces'>{dice_html}</span></div>"
    if tally_html:
        return f"<div class='dice-combo'>{tally_html}</div>"
    return f"<div class='dice-combo'><span class='dice-faces'>{dice_html}</span></div>"


def generate_number_word_table(data: Dict, rng: random.Random) -> Dict:
    first_row_example = bool(data.get("first_row_example", True))
    example_number = int(data.get("example_number", 49))
    row_count = int(data.get("row_count", 5))
    min_value = max(21, int(data.get("min_value", 21)))
    max_value = min(99, int(data.get("max_value", 99)))
    given_columns = data.get("given_columns", ["word"])

    if min_value > max_value:
        min_value, max_value = max_value, min_value

    valid_values = [v for v in range(min_value, max_value + 1) if v >= 21 and v % 10 != 0]
    if not valid_values:
        raise ValueError("No valid values available for number word table")

    if example_number < 21 or example_number % 10 == 0:
        example_number = rng.choice(valid_values)

    rows = []
    if first_row_example:
        example_word = underline_and_segment(number_to_word(example_number))
        rows.append({
            "number": example_number,
            "word": example_word,
            "dice": dice_representation(example_number),
            "given": ["word", "dice", "number"],
        })

    while len(rows) < row_count + (1 if first_row_example else 0):
        value = rng.choice(valid_values)
        word = underline_and_segment(number_to_word(value))
        rows.append({
            "number": value,
            "word": word,
            "dice": dice_representation(value),
            "given": given_columns,
        })

    placeholder_dice = dice_representation(example_number)

    return {
        "title": data.get("title", "Zahlwort – Würfelbild – Zahl"),
        "rows": rows,
        "placeholder_dice": placeholder_dice,
    }


def generate_ordering(data: Dict, rng: random.Random) -> Dict:
    set_size = int(data.get("set_size", 5))
    min_value = int(data.get("min_value", 0))
    max_value = int(data.get("max_value", 50))
    order = data.get("order", "increasing")
    show_symbols = bool(data.get("show_comparison_symbols", False))

    numbers: List[int] = []
    while len(numbers) < set_size:
        candidate = rng.randint(min_value, max_value)
        if candidate not in numbers:
            numbers.append(candidate)

    sorted_numbers = sorted(numbers)
    if order == "decreasing":
        sorted_numbers = list(reversed(sorted_numbers))

    return {
        "title": data.get(
            "title",
            "Ordne! Beginne mit der kleinsten Zahl!" if order == "increasing" else "Ordne! Beginne mit der größten Zahl!",
        ),
        "numbers": numbers,
        "sorted_numbers": sorted_numbers,
        "order": order,
        "show_symbols": show_symbols,
    }


def parse_header_sequence(values: Sequence[int] | Dict[str, int]) -> List[int]:
    if isinstance(values, dict):
        start = int(values.get("start", 0))
        end = int(values.get("end", start))
        step = int(values.get("step", 1))
        if step <= 0:
            raise ValueError("step must be positive")
        if end < start:
            start, end = end, start
        return list(range(start, end + 1, step))
    return [int(v) for v in values]


def _enforce_tens_headers(headers: List[int]) -> List[int]:
    enforced: List[int] = []
    seen = set()
    for value in headers:
        if value % 10 == 0:
            adjusted = value
        else:
            adjusted = int(math.copysign(math.ceil(abs(value) / 10) * 10, value))
        if adjusted < 10:
            adjusted = 10
        if adjusted not in seen:
            enforced.append(adjusted)
            seen.add(adjusted)
    return enforced


def _generate_random_headers(
    operation: str,
    row_count: int,
    col_count: int,
    rng: random.Random,
    min_result: int,
    max_result: int,
    row_pool: Optional[Sequence[int]] = None,
    col_pool: Optional[Sequence[int]] = None,
) -> Tuple[List[int], List[int]]:
    default_pool = list(range(10, 101, 10))
    rows_pool = list(row_pool) if row_pool else default_pool
    cols_pool = list(col_pool) if col_pool else default_pool

    def pick_values(pool: List[int], count: int) -> List[int]:
        if count <= len(pool):
            return rng.sample(pool, count)
        choices = [rng.choice(pool) for _ in range(count)]
        rng.shuffle(choices)
        return choices

    for _ in range(1000):
        rows = pick_values(rows_pool, row_count)
        cols = pick_values(cols_pool, col_count)

        valid = True
        for r in rows:
            for c in cols:
                result = r + c if operation == "+" else r - c
                if operation == "+" and result > 100:
                    valid = False
                    break
                if operation == "-" and result < 0:
                    valid = False
                    break
                if result < min_result or result > max_result:
                    valid = False
                    break
            if not valid:
                break

        if valid:
            return rows, cols

    raise ValueError("Unable to generate headers that satisfy all constraints")


def generate_operation_table(data: Dict, rng: random.Random) -> Dict:
    result_range = data.get("result_range")
    if not result_range or "min" not in result_range or "max" not in result_range:
        raise ValueError("result_range with min and max is required for operation_table")
    min_result = int(result_range["min"])
    max_result = int(result_range["max"])
    default_step = int(data.get("header_step", data.get("step", 1)))
    default_row_count = int(data.get("row_count", 2))
    default_col_count = int(data.get("col_count", 2))
    provided_tables = data.get("tables", [])
    if not provided_tables:
        provided_tables = [
            {
                "operation": "+",
                "row_headers": [10, 10 + default_step],
                "col_headers": [10, 10 + default_step],
                "given_cells": "none",
            },
            {
                "operation": "-",
                "row_headers": [10, 10 + default_step],
                "col_headers": [10, 10 + default_step],
                "given_cells": "none",
            },
        ]

    tables_data = []
    for table in provided_tables:
        operation = table.get("operation", "+")
        row_step = int(table.get("row_step", table.get("step", default_step)))
        col_step = int(table.get("col_step", table.get("step", default_step)))
        row_count = int(table.get("row_count", default_row_count))
        col_count = int(table.get("col_count", default_col_count))

        header_mode = table.get("header_mode", data.get("header_mode", "tens"))
        row_pool: Optional[List[int]] = None
        col_pool: Optional[List[int]] = None
        enforce_row_tens = True
        enforce_col_tens = True
        if header_mode == "small_cols":
            row_pool = [v for v in range(20, 100) if v % 10 != 0]
            col_pool = list(range(1, 10))
            enforce_row_tens = False
            enforce_col_tens = False

        row_headers_source = table.get("row_headers")
        col_headers_source = table.get("col_headers")
        if row_headers_source is None and col_headers_source is None:
            row_headers, col_headers = _generate_random_headers(
                operation, row_count, col_count, rng, min_result, max_result,
                row_pool=row_pool, col_pool=col_pool,
            )
        else:
            if not row_headers_source:
                row_headers_source = [10, 10 + row_step]
            if not col_headers_source:
                col_headers_source = [10, 10 + col_step]

            if isinstance(row_headers_source, dict) and "step" not in row_headers_source:
                row_headers_source = {**row_headers_source, "step": row_step}
            if isinstance(col_headers_source, dict) and "step" not in col_headers_source:
                col_headers_source = {**col_headers_source, "step": col_step}

            row_headers = parse_header_sequence(row_headers_source)
            col_headers = parse_header_sequence(col_headers_source)
            if enforce_row_tens:
                row_headers = _enforce_tens_headers(row_headers)
            if enforce_col_tens:
                col_headers = _enforce_tens_headers(col_headers)
            if not row_headers or not col_headers:
                raise ValueError("Row and column headers must contain at least one value")
        given_cells = table.get("given_cells", "none")

        # validate results
        results: List[List[int]] = []
        for r in row_headers:
            row = []
            for c in col_headers:
                result = r + c if operation == "+" else r - c
                if result < min_result or result > max_result:
                    raise ValueError(
                        f"Result {result} outside allowed range [{min_result}, {max_result}] for {r} {operation} {c}"
                    )
                if operation == "+" and result > 100:
                    raise ValueError(
                        f"Result {result} is above the allowed maximum of 100 for {r} {operation} {c}"
                    )
                if operation == "-" and result < 0:
                    raise ValueError(
                        f"Result {result} is below the allowed minimum of 0 for {r} {operation} {c}"
                    )
                row.append(result)
            results.append(row)

        revealed: List[Tuple[int, int]] = []
        if isinstance(given_cells, str):
            if given_cells == "diagonal":
                revealed = [(i, i) for i in range(min(len(row_headers), len(col_headers)))]
            elif given_cells.startswith("random_"):
                try:
                    count = int(given_cells.split("_", 1)[1])
                except ValueError:
                    count = 0
                all_cells = [(r_idx, c_idx) for r_idx in range(len(row_headers)) for c_idx in range(len(col_headers))]
                rng.shuffle(all_cells)
                revealed = all_cells[:count]
        else:
            for cell in given_cells:
                revealed.append((int(cell[0]), int(cell[1])))

        tables_data.append({
            "operation": operation,
            "row_headers": row_headers,
            "col_headers": col_headers,
            "results": results,
            "revealed": revealed,
        })

    return {
        "title": data.get("title", "Achte auf das Rechenzeichen!"),
        "tables": tables_data,
    }


def generate_number_line(data: Dict, rng: random.Random) -> Dict:
    start = int(data.get("start", 0))
    end = int(data.get("end", 100))
    major_tick = max(1, int(data.get("major_tick_interval", 10)))
    explicit_values = data.get("values")
    value_count = int(data.get("value_count", data.get("values_count", 5)))
    if explicit_values is None:
        possible_numbers = [number for number in range(start, end + 1) if number % major_tick != 0]
        if value_count > len(possible_numbers):
            raise ValueError("Not enough non-major numbers available for number line values")
        values = sorted(rng.sample(possible_numbers, value_count))
    else:
        values = [int(v) for v in explicit_values]
    return {
        "title": data.get(
            "title", "Trage zuerst die Zehnerzahlen an den Zahlenstrahl. Trage dann die Zahlen ein."
        ),
        "start": start,
        "end": end,
        "major_tick": major_tick,
        "values": values,
    }


def generate_dice_plus_mal(data: Dict, rng: random.Random) -> Dict:
    title = data.get("title", "Schreibe jeweils eine Plus- und eine Malaufgabe!")
    rows: List[Dict] = []

    dice_count_min = int(data.get("dice_count_min", data.get("dice_count", 4)))
    dice_count_max = int(data.get("dice_count_max", data.get("dice_count", dice_count_min)))
    if dice_count_min > dice_count_max:
        dice_count_min, dice_count_max = dice_count_max, dice_count_min
    dice_count = rng.randint(dice_count_min, dice_count_max)

    dice_face_min = max(1, int(data.get("dice_face_min", 2)))
    dice_face_max = min(6, int(data.get("dice_face_max", 6)))
    if dice_face_min > dice_face_max:
        dice_face_min, dice_face_max = dice_face_max, dice_face_min
    dice_face = rng.randint(dice_face_min, dice_face_max)
    rows.append({"kind": "dice", "count": dice_count, "size": dice_face})

    group_count_min = int(data.get("group_count_min", data.get("group_count", 6)))
    group_count_max = int(data.get("group_count_max", data.get("group_count", group_count_min)))
    if group_count_min > group_count_max:
        group_count_min, group_count_max = group_count_max, group_count_min
    group_count = rng.randint(group_count_min, group_count_max)

    group_size_min = max(1, int(data.get("group_size_min", 3)))
    group_size_max = max(group_size_min, int(data.get("group_size_max", 5)))
    group_size = rng.randint(group_size_min, group_size_max)
    rows.append({"kind": "dots", "count": group_count, "size": group_size})

    return {"title": title, "rows": rows}


def generate_number_sequence(data: Dict, rng: random.Random) -> Dict:
    title = data.get("title", "Setze die Zahlenfolgen fort!")
    sequences_cfg = data.get("sequences", [])
    sequences_data: List[Dict] = []
    used_steps: List[int] = []
    used_givens: List[str] = []
    for seq in sequences_cfg:
        length = max(2, int(seq.get("length", 10)))
        step_choices = seq.get("step_choices")
        if step_choices:
            step_choices = [int(s) for s in step_choices if int(s) != 0]
            if not step_choices:
                raise ValueError("number_sequence step_choices must not be empty/zero")
            # Avoid repeating the same step across sequences if alternatives exist.
            remaining = [s for s in step_choices if s not in used_steps] or step_choices
            step = rng.choice(remaining)
            used_steps.append(step)
        else:
            step = int(seq.get("step", 1))
            if step == 0:
                raise ValueError("number_sequence step must not be zero")
        if seq.get("start_at_step"):
            start_min = step
            start_max = step
        else:
            start_min = int(seq.get("start_min", 0))
            start_max = int(seq.get("start_max", start_min))
        if start_min > start_max:
            start_min, start_max = start_max, start_min
        given_choices = seq.get("given_choices")
        if given_choices:
            given_choices = list(given_choices)
            # Alternate first/last across sequences to ensure both directions appear.
            remaining = [g for g in given_choices if g not in used_givens] or given_choices
            given = rng.choice(remaining)
            used_givens.append(given)
        else:
            given = seq.get("given", "first")
        given_count = max(1, int(seq.get("given_count", 3)))

        values: List[int] = []
        for _ in range(200):
            start = rng.randint(start_min, start_max)
            candidate = [start + step * i for i in range(length)]
            if all(0 <= v <= 200 for v in candidate):
                values = candidate
                break
        if not values:
            raise ValueError("Cannot generate number sequence within [0, 200]")

        sequences_data.append({
            "values": values,
            "given": given,
            "given_count": min(given_count, length),
        })
    return {"title": title, "sequences": sequences_data}


def generate_number_triangle(data: Dict, rng: random.Random) -> Dict:
    title = data.get("title", "Rechne!")
    triangle_count = max(1, int(data.get("triangle_count", 2)))
    inner_min = max(0, int(data.get("inner_min", 1)))
    inner_max = max(inner_min, int(data.get("inner_max", 20)))
    outer_max_raw = data.get("outer_max")
    outer_max = int(outer_max_raw) if outer_max_raw is not None else None
    given_pattern = data.get("given_pattern", "inner_all")

    single_two_digit_inner = bool(data.get("single_two_digit_inner", False))
    min_crossing_outer = int(data.get("min_crossing_outer", 0))
    one_digit_min = max(inner_min, 1)
    one_digit_max = min(inner_max, 9)
    two_digit_min = max(inner_min, 10)
    two_digit_max = inner_max

    def _crosses_ten(x: int, y: int) -> bool:
        return (x % 10) + (y % 10) > 10

    triangles: List[Dict] = []
    for _ in range(triangle_count):
        for _ in range(2000):
            if single_two_digit_inner:
                if two_digit_max < 10 or one_digit_max < one_digit_min:
                    raise ValueError(
                        "single_two_digit_inner requires inner_min<=9 and inner_max>=10"
                    )
                two_digit_idx = rng.randint(0, 2)
                values = []
                for idx in range(3):
                    if idx == two_digit_idx:
                        values.append(rng.randint(two_digit_min, two_digit_max))
                    else:
                        values.append(rng.randint(one_digit_min, one_digit_max))
                i1, i2, i3 = values
            else:
                i1 = rng.randint(inner_min, inner_max)
                i2 = rng.randint(inner_min, inner_max)
                i3 = rng.randint(inner_min, inner_max)
            outer = [i1 + i2, i2 + i3, i1 + i3]
            if outer_max is not None and max(outer) > outer_max:
                continue
            if min_crossing_outer > 0:
                crossings = sum(
                    1 for (x, y) in [(i1, i2), (i2, i3), (i1, i3)] if _crosses_ten(x, y)
                )
                if crossings < min_crossing_outer:
                    continue
            break
        else:
            raise ValueError("Cannot generate number triangle within constraints")

        if given_pattern == "outer_all":
            given_inner: List[int] = []
            given_outer: List[int] = [0, 1, 2]
        elif given_pattern == "mixed":
            given_inner = sorted(rng.sample([0, 1, 2], 1))
            given_outer = sorted(rng.sample([0, 1, 2], 2))
        else:  # inner_all (default)
            given_inner = [0, 1, 2]
            given_outer = []

        triangles.append({
            "inner": [i1, i2, i3],
            "outer": outer,
            "given_inner": given_inner,
            "given_outer": given_outer,
        })

    return {"title": title, "triangles": triangles}


MONEY_DENOMINATIONS = {
    1: ("coin", "01_cent.gif"),
    2: ("coin", "02_cent.gif"),
    5: ("coin", "05_cent.gif"),
    10: ("coin", "10_cent.gif"),
    20: ("coin", "20_cent.gif"),
    50: ("coin", "50_cent.gif"),
    100: ("coin", "1_euro.gif"),
    200: ("coin", "2_euro.jpg"),
    500: ("note", "5_euro.jpg"),
    1000: ("note", "10_euro.jpg"),
    2000: ("note", "20_euro.jpg"),
    5000: ("note", "50_euro.jpg"),
    10000: ("note", "100_euro.jpg"),
}


def _money_has_carry(items_cents: List[int]) -> bool:
    """Returns True if the column-wise digit sum of items has any carry (>9)."""
    digits_per_place: Dict[int, int] = {}
    for v in items_cents:
        s = str(v)
        for i, ch in enumerate(reversed(s)):
            digits_per_place[i] = digits_per_place.get(i, 0) + int(ch)
    return any(total > 9 for total in digits_per_place.values())


_EURO_DENOMS_CENTS = [v for v in MONEY_DENOMINATIONS if v >= 100]
_CENT_DENOMS_CENTS = [v for v in MONEY_DENOMINATIONS if v < 100]


def generate_money(data: Dict, rng: random.Random) -> Dict:
    title = data.get("title", "Wie viel Geld ist es? Achte auf € und ct.")
    default_min_total = int(data.get("min_total_cents", 100))
    default_max_total = int(data.get("max_total_cents", 10000))
    default_item_min = max(1, int(data.get("item_count_min", 3)))
    default_item_max = max(default_item_min, int(data.get("item_count_max", 6)))

    allowed = data.get("allowed_denominations_cents")
    if allowed:
        default_denoms = [int(v) for v in allowed if int(v) in MONEY_DENOMINATIONS]
    else:
        default_denoms = list(MONEY_DENOMINATIONS.keys())
    if not default_denoms:
        raise ValueError("No valid money denominations configured")

    purses_cfg = data.get("purses")
    if purses_cfg:
        purse_specs = list(purses_cfg)
    else:
        purse_count = max(1, int(data.get("purse_count", 2)))
        purse_specs = [{} for _ in range(purse_count)]

    purses: List[Dict] = []
    for spec in purse_specs:
        mode = spec.get("mode")
        if mode == "euro_only":
            denoms = _EURO_DENOMS_CENTS[:]
            min_total = int(spec.get("min_total_cents", 200))
            max_total = int(spec.get("max_total_cents", 10000))
        elif mode == "cent_only":
            denoms = _CENT_DENOMS_CENTS[:]
            min_total = int(spec.get("min_total_cents", 5))
            max_total = int(spec.get("max_total_cents", 99))
        else:
            denoms = list(spec.get("allowed_denominations_cents", default_denoms))
            min_total = int(spec.get("min_total_cents", default_min_total))
            max_total = int(spec.get("max_total_cents", default_max_total))

        item_min = int(spec.get("item_count_min", default_item_min))
        item_max = max(item_min, int(spec.get("item_count_max", default_item_max)))
        no_carry = bool(spec.get("no_carry", False))
        coin_scale = spec.get("coin_scale")  # optional CSS hint, e.g., "large"

        items: List[int] = []
        for _ in range(500):
            count = rng.randint(item_min, item_max)
            attempt = sorted([rng.choice(denoms) for _ in range(count)], reverse=True)
            total = sum(attempt)
            if not (min_total <= total <= max_total):
                continue
            if no_carry and _money_has_carry(attempt):
                continue
            items = attempt
            break
        if not items:
            raise ValueError("Cannot generate money purse within constraints")
        purses.append({
            "items": items,
            "total": sum(items),
            "coin_scale": coin_scale,
        })

    return {"title": title, "purses": purses}


TASK_GENERATORS = {
    "number_dictation": generate_number_dictation,
    "compare_numbers": generate_compare_numbers,
    "pre_succ_table": generate_pre_succ_table,
    "arithmetic_list": generate_arithmetic_list,
    "number_word_table": generate_number_word_table,
    "ordering": generate_ordering,
    "operation_table": generate_operation_table,
    "number_line": generate_number_line,
    "dice_plus_mal": generate_dice_plus_mal,
    "number_sequence": generate_number_sequence,
    "number_triangle": generate_number_triangle,
    "money": generate_money,
}


# ---------- Rendering helpers ----------

def render_number_boxes(count: int, content: Optional[List[str]] = None) -> str:
    boxes = []
    for i in range(count):
        text = content[i] if content and i < len(content) else ""
        boxes.append(f"<span class='number-box'>{text}</span>")
    return "".join(boxes)


def render_number_dictation(data: Dict, solution: bool) -> str:
    content = None
    if solution:
        generated_numbers = [str(number) for number in data.get("numbers", [])]
        if generated_numbers:
            content = generated_numbers
        elif data.get("show_helper_numbers"):
            content = [str(i + 1) for i in range(data["box_count"])]
    boxes = render_number_boxes(data["box_count"], content)
    return f"""<div class='task'>
  <div class='task-title'>{data['title']}</div>
  <div class='number-dictation'>{boxes}</div>
</div>"""


def render_compare_numbers(data: Dict, solution: bool) -> str:
    items_html = []
    for a, b, symbol in data["items"]:
        sign = symbol if solution else ""
        items_html.append(
            f"<div class='compare-item'><span class='compare-number'>{a}</span>"
            f"<span class='compare-circle'>{sign}</span><span class='compare-number'>{b}</span></div>"
        )
    column_class = f"cols-{data['columns']}"
    return f"""<div class='task'>
  <div class='task-title'>{data['title']}</div>
  <div class='compare-grid {column_class}'>
    {''.join(items_html)}
  </div>
</div>"""


def render_pre_succ_table(data: Dict, solution: bool) -> str:
    rows_html = []
    for row in data["rows"]:
        values = row["values"]
        given = row["given_field"]
        def cell_content(key: str) -> str:
            if solution or given == key:
                return str(values[key])
            return ""
        rows_html.append(
            "<tr>" + "".join(f"<td>{cell_content(key)}</td>" for key in ["left", "middle", "right"]) + "</tr>"
        )
    return f"""<div class='task'>
  <div class='task-title'>{data['title']}</div>
  <table class='simple-table'>
    <thead><tr><th>Vorgänger</th><th>Zahl</th><th>Nachfolger</th></tr></thead>
    <tbody>{''.join(rows_html)}</tbody>
  </table>
</div>"""


def _result_digits_for_cells(result: int, answer_cells: int) -> List[str]:
    if answer_cells == 1:
        return [str(result)]
    raw = list(str(result))
    if len(raw) >= answer_cells:
        return raw[-answer_cells:]
    return [""] * (answer_cells - len(raw)) + raw


def _render_arithmetic_item_grid(a: int, op: str, b: int, result: int,
                                 answer_cells: int, extra_rows: int, solution: bool,
                                 total_cells: Optional[int] = None,
                                 grid_extra_class: str = "") -> str:
    tokens = list(str(a)) + [op] + list(str(b)) + ["="]
    if total_cells is not None:
        effective_answer_cells = max(answer_cells, total_cells - len(tokens))
    else:
        effective_answer_cells = answer_cells
    if solution:
        digits = _result_digits_for_cells(result, effective_answer_cells)
    else:
        digits = [""] * effective_answer_cells
    total_cols = len(tokens) + effective_answer_cells

    head_cells = "".join(f"<td class='ag-q'>{t}</td>" for t in tokens)
    head_cells += "".join(f"<td class='ag-a'>{d}</td>" for d in digits)
    rows = [f"<tr>{head_cells}</tr>"]
    if extra_rows > 0:
        empty = "".join("<td class='ag-x'></td>" for _ in range(total_cols))
        for _ in range(extra_rows):
            rows.append(f"<tr>{empty}</tr>")
    return f"<table class='arith-grid{grid_extra_class}'>{''.join(rows)}</table>"


def _render_arithmetic_item_inline(a: int, op: str, b: int, result: int,
                                   answer_cells: int, extra_rows: int, solution: bool) -> str:
    if solution:
        digits = _result_digits_for_cells(result, answer_cells)
    else:
        digits = [""] * answer_cells
    boxes_html = "".join(f"<span class='number-box'>{d}</span>" for d in digits)
    wrapper_class = "answer-cells single" if answer_cells == 1 else "answer-cells"
    boxes_wrapper = f"<span class='{wrapper_class}'>{boxes_html}</span>"
    extra_html = ""
    if extra_rows > 0:
        row_boxes = "".join("<span class='number-box'></span>" for _ in range(answer_cells))
        extra_html = "<div class='arithmetic-extra-rows'>" + "".join(
            f"<div class='arithmetic-extra-row'>{row_boxes}</div>" for _ in range(extra_rows)
        ) + "</div>"
    return (
        f"<div class='arithmetic-item'>"
        f"<div class='arithmetic-question'>"
        f"<span class='arithmetic-equation'>{a}&nbsp;{op}&nbsp;{b}&nbsp;=</span>"
        f"{boxes_wrapper}"
        f"</div>"
        f"{extra_html}"
        f"</div>"
    )


def render_arithmetic_list(data: Dict, solution: bool) -> str:
    answer_cells = int(data.get("answer_cells", 1))
    extra_rows = int(data.get("extra_rows", 0))
    cell_question = bool(data.get("cell_question", False))
    total_cells = data.get("total_cells")
    compact = bool(data.get("compact", False))
    items_html: List[str] = []
    grid_extra = " arith-grid-compact" if compact else ""
    for a, op, b, result in data["items"]:
        if cell_question:
            items_html.append(
                _render_arithmetic_item_grid(a, op, b, result, answer_cells, extra_rows, solution, total_cells, grid_extra)
            )
        else:
            items_html.append(
                _render_arithmetic_item_inline(a, op, b, result, answer_cells, extra_rows, solution)
            )
    column_class = f"cols-{data['columns']}"
    return f"""<div class='task'>
  <div class='task-title'>{data['title']}</div>
  <div class='arithmetic-grid {column_class}'>
    {''.join(items_html)}
  </div>
</div>"""


def render_number_word_table(data: Dict, solution: bool) -> str:
    rows_html = []
    placeholder = ""
    if not solution and data.get("placeholder_dice"):
        placeholder = f"<span class='dice-sample-placeholder'>{data['placeholder_dice']}</span>"
    for row in data["rows"]:
        given_cols = set(row["given"] if not solution else ["word", "dice", "number"])
        word_cell = row["word"] if "word" in given_cols else ""
        dice_cell = row["dice"] if "dice" in given_cols else placeholder
        number_cell = str(row["number"]) if "number" in given_cols else ""
        rows_html.append(
            f"<tr><td>{word_cell}</td><td class='dice-cell'>{dice_cell}</td><td>{number_cell}</td></tr>"
        )
    return f"""<div class='task'>
  <div class='task-title'>{data['title']}</div>
  <table class='simple-table'>
    <thead><tr><th>Zahlwort</th><th>Würfelbild</th><th>Zahl</th></tr></thead>
    <tbody>{''.join(rows_html)}</tbody>
  </table>
</div>"""


def render_ordering(data: Dict, solution: bool) -> str:
    numbers_str = ", ".join(str(n) for n in data["numbers"])
    comparison_symbol = "<" if data["order"] == "increasing" else ">"

    def cells_for_number(chars: List[str]) -> List[str]:
        return [f"<td class='ordering-cell'>{digit}</td>" for digit in chars]

    def cells_for_comparator() -> str:
        symbol = comparison_symbol if data["show_symbols"] else ""
        return f"<td class='ordering-cell comparator'>{symbol}</td>"

    row_cells: List[str] = []
    for idx, value in enumerate(data["sorted_numbers"]):
        digits = list(str(value)) if solution else ["" for _ in str(value)]
        row_cells.extend(cells_for_number(digits))
        if idx < len(data["sorted_numbers"]) - 1:
            row_cells.append(cells_for_comparator())

    table_html = f"<table class='ordering-table'><tr>{''.join(row_cells)}</tr></table>"
    return f"""<div class='task'>
  <div class='task-title'>{data['title']}</div>
  <div class='ordering-numbers'>{numbers_str}</div>
  {table_html}
</div>"""


def render_operation_table(data: Dict, solution: bool) -> str:
    tables_html = []
    for table in data["tables"]:
        header_cells = f"<th class='operation-symbol'>{table['operation']}</th>" + "".join(
            f"<th>{c}</th>" for c in table["col_headers"]
        )
        body_rows = []
        for r_idx, row_header in enumerate(table["row_headers"]):
            cells = [f"<th>{row_header}</th>"]
            for c_idx, result in enumerate(table["results"][r_idx]):
                reveal = solution or (r_idx, c_idx) in table["revealed"]
                cells.append(f"<td>{result if reveal else ''}</td>")
            body_rows.append("<tr>" + "".join(cells) + "</tr>")
        tables_html.append(
            f"""
<div class='operation-table'>
  <table class='simple-table'>
    <thead><tr>{header_cells}</tr></thead>
    <tbody>{''.join(body_rows)}</tbody>
  </table>
</div>"""
        )
    return f"""<div class='task'>
  <div class='task-title'>{data['title']}</div>
  <div class='operation-table-grid'>
    {''.join(tables_html)}
  </div>
</div>"""


def render_number_line(data: Dict, solution: bool) -> str:
    start = data["start"]
    end = data["end"]
    major = data["major_tick"]
    total_range = max(1, end - start)

    width = 1000
    height = 220
    left_margin = 50
    right_margin = 50
    usable_width = width - left_margin - right_margin
    axis_y = 150
    tick_height_major = 48
    tick_height_mid = 32
    tick_height_minor = 18
    label_offset = 18

    tick_elements = []
    tick_tops: Dict[int, float] = {}
    for value in range(start, end + 1):
        x = left_margin + ((value - start) / total_range) * usable_width
        is_major = (value - start) % major == 0
        is_mid_major = major % 2 == 0 and not is_major and (value - start) % major == major // 2
        if is_major:
            tick_height = tick_height_major
        elif is_mid_major:
            tick_height = tick_height_mid
        else:
            tick_height = tick_height_minor
        y_top = axis_y - tick_height / 2
        y_bottom = axis_y + tick_height / 2
        tick_tops[value] = y_top
        tick_elements.append(
            f"<line x1='{x:.2f}' y1='{y_top:.2f}' x2='{x:.2f}' y2='{y_bottom:.2f}' class='tick-line{' major' if is_major else ' mid' if is_mid_major else ''}' />"
        )
        if is_major and solution:
            tick_elements.append(
                f"<text x='{x:.2f}' y='{y_top - label_offset:.2f}' class='tick-label'>{value}</text>"
            )

    value_elements = []
    if data["values"]:
        box_width = 70
        box_height = 36
        box_y = 24
        min_gap = 12
        max_offset = 40

        placements: List[Tuple[int, float, float]] = []
        previous_right = left_margin - min_gap

        for value in sorted(data["values"]):
            tick_x = left_margin + ((value - start) / total_range) * usable_width
            desired_center = tick_x
            min_center = previous_right + box_width / 2 + min_gap
            box_center_x = max(desired_center, min_center)

            if abs(box_center_x - desired_center) > max_offset:
                direction = 1 if box_center_x > desired_center else -1
                box_center_x = desired_center + direction * max_offset
                box_center_x = max(box_center_x, min_center)

            box_center_x = min(
                max(box_center_x, left_margin + box_width / 2),
                width - right_margin - box_width / 2,
            )

            placements.append((value, box_center_x, tick_x))
            previous_right = box_center_x + box_width / 2

        for value, box_center_x, tick_x in placements:
            tick_target_y = tick_tops.get(value, axis_y - tick_height_minor / 2)
            value_elements.append(
                f"<line x1='{box_center_x:.2f}' y1='{box_y + box_height}' x2='{tick_x:.2f}' y2='{tick_target_y:.2f}' class='connector-line' />"
            )
            box_value = str(value) if solution else ""
            value_elements.append(
                f"<rect x='{box_center_x - box_width / 2:.2f}' y='{box_y}' width='{box_width}' height='{box_height}' rx='4' class='number-line-rect' />"
                f"<text x='{box_center_x:.2f}' y='{box_y + box_height / 2 + 5:.2f}' class='number-line-text'>{box_value}</text>"
            )

    svg_content = "".join(tick_elements + value_elements)
    axis_line = f"<line x1='{left_margin}' y1='{axis_y}' x2='{width - right_margin}' y2='{axis_y}' class='axis-line' />"

    return f"""<div class='task'>
  <div class='task-title'>{data['title']}</div>
  <div class='number-line-container'>
    <svg class='number-line-svg' viewBox='0 0 {width} {height}' preserveAspectRatio='none'>
      {axis_line}
      {svg_content}
    </svg>
  </div>
</div>"""


def _apple_heap_html(count: int) -> str:
    """Arrange apples as a narrow heap (max 2 wide) so groups fit next to each other in a row."""
    if count <= 0:
        return ""
    if count == 1:
        rows = [1]
    elif count == 2:
        rows = [1, 1]
    elif count == 3:
        rows = [1, 2]
    elif count == 4:
        rows = [2, 2]
    elif count == 5:
        rows = [1, 2, 2]
    elif count == 6:
        rows = [2, 2, 2]
    else:
        # General: pyramid-ish with width capped at 2.
        rows = []
        remaining = count
        if remaining % 2 == 1:
            rows.append(1)
            remaining -= 1
        while remaining > 0:
            rows.append(2)
            remaining -= 2
    parts = []
    for n in rows:
        parts.append(
            "<span class='dpm-apple-row'>"
            + "".join("<span class='dpm-apple'>🍎</span>" for _ in range(n))
            + "</span>"
        )
    return "".join(parts)


def render_dice_plus_mal(data: Dict, solution: bool) -> str:
    visual_groups: List[str] = []
    per_row_formulas: List[List[str]] = []
    for row in data["rows"]:
        if row["kind"] == "dice":
            visuals = "".join(
                f"<span class='dpm-item dpm-dice'>{_dice_svg(row['size'])}</span>"
                for _ in range(row["count"])
            )
        else:
            visuals = "".join(
                "<span class='dpm-item dpm-group'>"
                + _apple_heap_html(row["size"])
                + "</span>"
                for _ in range(row["count"])
            )
        visual_groups.append(f"<span class='dpm-visual-group'>{visuals}</span>")

        plus_terms = " + ".join(str(row["size"]) for _ in range(row["count"]))
        total = row["count"] * row["size"]
        per_row_formulas.append([
            f"{plus_terms} = {total}",
            f"{row['count']} · {row['size']} = {total}",
        ])

    visuals_html = (
        "<div class='dice-plus-mal-row'>"
        + "<span class='dpm-visual-sep'></span>".join(visual_groups)
        + "</div>"
    )
    if solution:
        columns_html = "".join(
            "<div class='dpm-answer-col'>"
            + "".join(
                f"<div class='dpm-line dpm-line-solved'>{f}</div>" for f in formulas
            )
            + "</div>"
            for formulas in per_row_formulas
        )
        lines_html = f"<div class='dpm-answers-cols'>{columns_html}</div>"
    else:
        max_lines = max((len(f) for f in per_row_formulas), default=2)
        lines_html = "".join(
            "<div class='dpm-line'></div>" for _ in range(max_lines)
        )
    return f"""<div class='task'>
  <div class='task-title'>{data['title']}</div>
  {visuals_html}
  <div class='dpm-answers'>{lines_html}</div>
</div>"""


def render_number_sequence(data: Dict, solution: bool) -> str:
    rows_html: List[str] = []
    for seq in data["sequences"]:
        values = seq["values"]
        n = len(values)
        if seq["given"] == "first":
            shown = set(range(min(seq["given_count"], n)))
        else:
            shown = set(range(max(0, n - seq["given_count"]), n))

        radius = 22
        spacing = 60
        margin = radius + 4
        total_w = (n - 1) * spacing + 2 * margin
        total_h = 2 * margin

        parts: List[str] = []
        for i in range(n - 1):
            x1 = margin + i * spacing + radius
            x2 = margin + (i + 1) * spacing - radius
            y = total_h / 2
            parts.append(
                f"<line x1='{x1:.1f}' y1='{y:.1f}' x2='{x2:.1f}' y2='{y:.1f}' "
                f"stroke='#000' stroke-width='1.5'/>"
            )
        for i in range(n):
            cx = margin + i * spacing
            cy = total_h / 2
            parts.append(
                f"<circle cx='{cx:.1f}' cy='{cy:.1f}' r='{radius}' fill='#fff' "
                f"stroke='#000' stroke-width='2'/>"
            )
            label = str(values[i]) if (solution or i in shown) else ""
            if label:
                parts.append(
                    f"<text x='{cx:.1f}' y='{cy:.1f}' text-anchor='middle' "
                    f"dominant-baseline='central' font-size='16' font-family='Zain, sans-serif'>{label}</text>"
                )
        svg = (
            f"<svg class='number-sequence-svg' viewBox='0 0 {total_w:.0f} {total_h:.0f}' "
            f"preserveAspectRatio='xMidYMid meet'>{''.join(parts)}</svg>"
        )
        rows_html.append(f"<div class='number-sequence-row'>{svg}</div>")

    return f"""<div class='task'>
  <div class='task-title'>{data['title']}</div>
  {''.join(rows_html)}
</div>"""


def render_number_triangle(data: Dict, solution: bool) -> str:
    import math

    triangles_html: List[str] = []
    for tri in data["triangles"]:
        inner = tri["inner"]
        outer = tri["outer"]
        given_inner = set(tri["given_inner"])
        given_outer_field = tri["given_outer"]
        given_outer = set(given_outer_field) if isinstance(given_outer_field, list) else {given_outer_field}

        # Equilateral triangle, larger than before.
        side = 220.0
        height = side * math.sqrt(3) / 2.0
        margin_x = 60.0
        margin_top = 25.0
        margin_bottom = 70.0  # space for bottom result box
        w = side + 2 * margin_x
        h = height + margin_top + margin_bottom

        top = (w / 2.0, margin_top)
        bl = (top[0] - side / 2.0, top[1] + height)
        br = (top[0] + side / 2.0, top[1] + height)

        # Centroid (= incenter for equilateral)
        cx_t = (top[0] + bl[0] + br[0]) / 3.0
        cy_t = (top[1] + bl[1] + br[1]) / 3.0

        # Side midpoints. Indices align with outer:
        # 0 = left side (top↔bl), 1 = bottom side (bl↔br), 2 = right side (top↔br)
        mids = [
            ((top[0] + bl[0]) / 2.0, (top[1] + bl[1]) / 2.0),
            ((bl[0] + br[0]) / 2.0, (bl[1] + br[1]) / 2.0),
            ((top[0] + br[0]) / 2.0, (top[1] + br[1]) / 2.0),
        ]

        parts: List[str] = [
            f"<polygon points='{top[0]:.2f},{top[1]:.2f} {bl[0]:.2f},{bl[1]:.2f} "
            f"{br[0]:.2f},{br[1]:.2f}' fill='none' stroke='#000' stroke-width='2'/>"
        ]

        # Trennlinien: from each side midpoint, perpendicular to the side, meeting at centroid.
        for mx, my in mids:
            parts.append(
                f"<line x1='{mx:.2f}' y1='{my:.2f}' x2='{cx_t:.2f}' y2='{cy_t:.2f}' "
                f"stroke='#000' stroke-width='1.2'/>"
            )

        # Inner numbers placed in each of the three sub-regions defined by the Trennlinien.
        # Each sub-region is bounded by two Trennlinien and one vertex.
        # Place inner number near its vertex, slightly inward toward the centroid.
        vertices = [top, bl, br]
        inner_anchors = []
        for vx, vy in vertices:
            # Move from vertex toward centroid by ~38% of the distance.
            ax = vx + (cx_t - vx) * 0.38
            ay = vy + (cy_t - vy) * 0.38
            inner_anchors.append((ax, ay))

        for idx, (px, py) in enumerate(inner_anchors):
            if solution or idx in given_inner:
                parts.append(
                    f"<text x='{px:.2f}' y='{py:.2f}' text-anchor='middle' "
                    f"dominant-baseline='central' font-size='26' font-weight='bold' "
                    f"font-family='Zain, sans-serif'>{inner[idx]}</text>"
                )

        # Outer result boxes: just outside each side, with a gap (~ height of a number)
        # along the outward normal.
        box_w, box_h = 50.0, 36.0
        gap = 20.0
        for idx, (mx, my) in enumerate(mids):
            # Outward normal from midpoint = unit vector from centroid to midpoint.
            dx = mx - cx_t
            dy = my - cy_t
            length = math.hypot(dx, dy) or 1.0
            nx, ny = dx / length, dy / length
            offset = gap + box_h / 2.0
            cx_box = mx + nx * offset
            cy_box = my + ny * offset
            x = cx_box - box_w / 2.0
            y = cy_box - box_h / 2.0
            parts.append(
                f"<rect x='{x:.2f}' y='{y:.2f}' width='{box_w}' height='{box_h}' "
                f"rx='6' ry='6' fill='#fff' stroke='#000' stroke-width='1.5'/>"
            )
            if solution or idx in given_outer:
                parts.append(
                    f"<text x='{cx_box:.2f}' y='{cy_box:.2f}' text-anchor='middle' "
                    f"dominant-baseline='central' font-size='18' "
                    f"font-family='Zain, sans-serif'>{outer[idx]}</text>"
                )

        svg = (
            f"<svg class='rechendreieck-svg' viewBox='0 0 {w:.2f} {h:.2f}' "
            f"preserveAspectRatio='xMidYMid meet'>{''.join(parts)}</svg>"
        )
        triangles_html.append(f"<div class='rechendreieck'>{svg}</div>")

    return f"""<div class='task'>
  <div class='task-title'>{data['title']}</div>
  <div class='triangle-grid'>{''.join(triangles_html)}</div>
</div>"""


def _format_money_amount(total_cents: int) -> str:
    euros = total_cents // 100
    cents = total_cents % 100
    if euros and cents:
        return f"{euros} € {cents} ct"
    if euros:
        return f"{euros} €"
    return f"{cents} ct"


def render_money(data: Dict, solution: bool) -> str:
    purses_html: List[str] = []
    for purse in data["purses"]:
        items_html_parts: List[str] = []
        for value in purse["items"]:
            kind, filename = MONEY_DENOMINATIONS[value]
            sub = "coins" if kind == "coin" else "banknotes"
            extra_class = f" money-{kind}-{value}"
            items_html_parts.append(
                f"<img class='money-{kind}{extra_class}' src='../assets/euro/{sub}/{filename}' "
                f"alt='{value} ct'/>"
            )
        items_html = "".join(items_html_parts)
        if solution:
            answer = f"<div class='money-answer'>= <strong>{_format_money_amount(purse['total'])}</strong></div>"
        else:
            answer = "<div class='money-answer'>= <span class='money-line'></span></div>"
        cell_extra = ""
        scale = purse.get("coin_scale")
        if scale:
            cell_extra = f" money-cell-scale-{scale}"
        purses_html.append(
            f"<div class='money-cell{cell_extra}'>"
            f"<div class='money-purse'>"
            f"<div class='money-content'>{items_html}</div>"
            f"</div>"
            f"{answer}"
            f"</div>"
        )
    return f"""<div class='task'>
  <div class='task-title'>{data['title']}</div>
  <div class='money-grid'>{''.join(purses_html)}</div>
</div>"""


TASK_RENDERERS = {
    "number_dictation": render_number_dictation,
    "compare_numbers": render_compare_numbers,
    "pre_succ_table": render_pre_succ_table,
    "arithmetic_list": render_arithmetic_list,
    "number_word_table": render_number_word_table,
    "ordering": render_ordering,
    "operation_table": render_operation_table,
    "number_line": render_number_line,
    "dice_plus_mal": render_dice_plus_mal,
    "number_sequence": render_number_sequence,
    "number_triangle": render_number_triangle,
    "money": render_money,
}


STYLE_BLOCK = """
<style>
  @page {
    size: A4 portrait;
    margin: 0.8cm;
  }

  html, body {
    margin: 0;
    padding: 0;
  }
  body {
    font-family: 'Zain', sans-serif;
    font-size: 11pt;
    background: #e0e0e0;
  }

  .worksheet, .worksheet-page {
    box-sizing: border-box;
    width: 210mm;
    min-height: 297mm;
    padding: 0.8cm;
    margin: 0.5cm auto;
    background: #fff;
    box-shadow: 0 0.2cm 0.6cm rgba(0, 0, 0, 0.15);
    page-break-after: always;
    break-after: page;
  }
  .worksheet:last-child, .worksheet-page:last-child {
    page-break-after: auto;
    break-after: auto;
  }

  @media print {
    body {
      background: #fff;
    }
    .worksheet, .worksheet-page {
      width: auto;
      min-height: 0;
      padding: 0;
      margin: 0;
      box-shadow: none;
    }
  }

  .header {
    display: flex;
    justify-content: space-between;
    border-bottom: 1px solid #000;
    padding-bottom: 0.15cm;
    margin-bottom: 0.25cm;
  }

  .header-field {
    flex: 0 0 48%;
  }

  .task {
    border: 1px solid #000;
    padding: 0.3cm 0.35cm;
    margin-bottom: 0.4cm;
  }

  .task-title {
    font-weight: bold;
    margin-bottom: 0.2cm;
  }

  .number-box {
    display: inline-block;
    width: 0.8cm;
    height: 0.8cm;
    border: 1px solid #000;
    margin-right: 0.1cm;
    text-align: center;
    vertical-align: middle;
    line-height: 0.8cm;
  }

  .compare-grid, .arithmetic-grid {
    display: grid;
    gap: 0.15cm 0.4cm;
  }

  .arith-grid {
    border-collapse: collapse;
    margin: 0;
  }
  .arith-grid td {
    width: 0.6cm;
    height: 0.6cm;
    border: 1px solid #000;
    text-align: center;
    vertical-align: middle;
    font-size: 11pt;
    line-height: 1;
    padding: 0;
  }
  .arith-grid td.ag-q {
    border-color: #000;
  }
  .arith-grid td.ag-pad {
    border: none;
  }
  table.arith-grid.arith-grid-compact {
    table-layout: fixed;
    width: 4.7cm;
  }
  table.arith-grid.arith-grid-compact td {
    width: 0.585cm !important;
    min-width: 0.585cm;
    max-width: 0.585cm;
    height: 0.78cm;
    font-size: 13pt;
  }
  .compare-grid.cols-2, .arithmetic-grid.cols-2 { grid-template-columns: repeat(2, 1fr); }
  .compare-grid.cols-3, .arithmetic-grid.cols-3 { grid-template-columns: repeat(3, 1fr); }
  .compare-grid.cols-4, .arithmetic-grid.cols-4 { grid-template-columns: repeat(4, 1fr); }

  .compare-item {
    display: flex;
    align-items: center;
    gap: 0.2cm;
  }

  .arithmetic-item {
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .arithmetic-question {
    display: flex;
    align-items: center;
    gap: 0.15cm;
    white-space: nowrap;
  }
  .arithmetic-question .number-box {
    margin-right: 0;
  }

  .arithmetic-equation {
    white-space: nowrap;
  }

  .answer-cells {
    display: inline-flex;
  }
  .answer-cells .number-box {
    margin-right: 0;
    border-right-width: 0;
  }
  .answer-cells .number-box:last-child {
    border-right-width: 1px;
  }
  .answer-cells.single .number-box {
    width: 1.4cm;
    border-right-width: 1px;
  }

  .arithmetic-extra-rows {
    display: flex;
    flex-direction: column;
  }

  .arithmetic-extra-row {
    display: flex;
  }
  .arithmetic-extra-row .number-box {
    margin-right: 0;
    border-right-width: 0;
    border-top-width: 0;
  }
  .arithmetic-extra-row .number-box:last-child {
    border-right-width: 1px;
  }

  .compare-circle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1cm;
    height: 1cm;
    border: 1px solid #000;
    border-radius: 50%;
    font-size: 14pt;
  }

  .boxed-number {
    display: inline-block;
    min-width: 1.2cm;
    padding: 0.1cm 0.2cm;
    border: 1px solid #000;
    text-align: center;
  }

  .compare-number {
    display: inline-block;
    min-width: 1.2cm;
    padding: 0.1cm 0.2cm;
    text-align: center;
  }

  .simple-table {
    width: 100%;
    border-collapse: collapse;
  }
  .simple-table th, .simple-table td {
    border: 1px solid #000;
    padding: 0.2cm;
    text-align: center;
  }
  .simple-table th {
    background: #f5f5f5;
  }

  .dice-cell {
    font-size: 18pt;
    line-height: 1.6cm;
    min-height: 1.6cm;
  }
  .dice-combo {
    display: inline-flex;
    align-items: center;
    gap: 0.15cm;
  }
  .tallies {
    display: inline-flex;
    align-items: center;
  }
  .tally-svg {
    height: 1cm;
    width: auto;
  }
  .tally-line {
    stroke: #000;
    stroke-width: 5;
    stroke-linecap: round;
  }
  .dice-faces {
    display: inline-flex;
    gap: 0.1cm;
    vertical-align: middle;
  }
  .dice-face {
    display: inline-block;
  }
  .dice-svg {
    width: 0.9cm;
    height: 0.9cm;
  }
  .dice-svg.dice-placeholder {
    visibility: hidden;
  }
  .dice-svg circle {
    fill: #000;
  }
  .dice-sample-placeholder {
    display: inline-block;
  }
  .dice-sample-placeholder .dice-svg circle,
  .dice-sample-placeholder .dice-svg rect,
  .dice-sample-placeholder .tally-line {
    stroke: #fff;
    fill: #fff;
  }

  .number-word-and {
    text-decoration: underline;
    text-decoration-thickness: 0.08em;
  }

  .ordering-numbers {
    margin-bottom: 0.3cm;
  }
  .ordering-table {
    border-collapse: collapse;
    width: 100%;
  }
  .ordering-cell {
    border: 1px solid #000;
    width: 0.8cm;
    height: 0.8cm;
    text-align: center;
    vertical-align: middle;
    font-size: 12pt;
  }
  .ordering-cell.comparator {
    width: 0.6cm;
  }

  .operation-table-grid {
    display: grid;
    gap: 0.5cm;
    grid-template-columns: repeat(auto-fit, minmax(6cm, 1fr));
    align-items: start;
  }
  .operation-table {
    border: 1px solid #000;
    padding: 0.2cm;
  }
  .operation-symbol {
    background: #f5f5f5;
    font-weight: bold;
  }

  .number-line-container {
    width: 100%;
  }
  .number-line-svg {
    width: 100%;
    height: auto;
  }
  .axis-line, .tick-line, .connector-line {
    stroke: #000;
    stroke-width: 2;
  }
  .tick-line.major {
    stroke-width: 3;
  }
  .tick-line.mid {
    stroke-width: 2.5;
  }
  .tick-label {
    font-size: 10pt;
    text-anchor: middle;
  }
  .number-line-rect {
    fill: #fff;
    stroke: #000;
    stroke-width: 2;
  }
  .number-line-text {
    font-size: 12pt;
    text-anchor: middle;
    dominant-baseline: middle;
  }

  .number-dictation {
    display: flex;
    gap: 0.1cm;
  }

  .worksheet-title {
    text-align: center;
    font-weight: bold;
    font-size: 14pt;
    border: 1px solid #000;
    padding: 0.1cm;
    margin-bottom: 0.25cm;
  }

  .dice-plus-mal-row {
    display: flex;
    flex-wrap: nowrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.4cm;
    margin-bottom: 0.15cm;
  }
  .dpm-visual-group {
    display: inline-flex;
    flex-wrap: nowrap;
    align-items: center;
    gap: 0.15cm;
  }
  .dpm-visual-sep {
    flex: 0 0 0.5cm;
  }
  .dpm-item {
    display: inline-flex;
    align-items: center;
  }
  .dpm-dice .dice-svg {
    width: 1.1cm;
    height: 1.1cm;
    border: 1.5px solid #000;
    border-radius: 4px;
  }
  .dpm-group {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0;
    padding: 0.05cm 0.08cm;
    border: 1px dashed #888;
    border-radius: 4px;
  }
  .dpm-apple-row {
    display: inline-flex;
    flex-wrap: nowrap;
    gap: 0;
    line-height: 0.85;
  }
  .dpm-apple {
    font-size: 12pt;
    line-height: 0.9;
  }
  .dpm-answers {
    display: flex;
    flex-direction: column;
    gap: 0.25cm;
    margin-top: 0.7cm;
  }
  .dpm-answers-cols {
    display: flex;
    justify-content: space-between;
    gap: 0.6cm;
    width: 100%;
  }
  .dpm-answer-col {
    display: flex;
    flex-direction: column;
    gap: 0.25cm;
    flex: 1 1 0;
  }
  .dpm-answer-col:first-child .dpm-line-solved {
    text-align: left;
  }
  .dpm-answer-col:last-child .dpm-line-solved {
    text-align: right;
  }
  .dpm-line {
    border-bottom: 1px solid #000;
    height: 1cm;
  }
  .dpm-line-solved {
    font-weight: bold;
    text-align: center;
    border-bottom-color: transparent;
  }

  .number-sequence-row {
    margin-bottom: 0.15cm;
  }
  .number-sequence-svg {
    width: 100%;
    max-height: 1.2cm;
  }

  .money-grid {
    display: flex;
    gap: 0.6cm;
    justify-content: center;
    align-items: flex-start;
  }
  .money-cell {
    flex: 0 1 8.8cm;
    display: flex;
    flex-direction: column;
    align-items: center;
    break-inside: avoid;
    page-break-inside: avoid;
  }
  .money-purse {
    position: relative;
    width: 100%;
    height: 2.8cm;
    border: 2px solid #000;
    border-radius: 0.3cm 0.3cm 1.1cm 1.1cm;
    padding: 0.35cm 0.35cm 0.5cm;
    margin-top: 0.3cm;
    background: #fff;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .money-purse::before {
    content: "";
    position: absolute;
    top: -0.32cm;
    left: 50%;
    transform: translateX(-50%);
    width: 1.2cm;
    height: 0.35cm;
    background: #fff;
    border: 2px solid #000;
    border-bottom: none;
    border-radius: 0.55cm 0.55cm 0 0;
  }
  .money-content {
    display: flex;
    flex-wrap: wrap;
    gap: 0.2cm 0.22cm;
    align-items: center;
    justify-content: center;
    width: 100%;
  }
  .money-coin {
    object-fit: contain;
  }
  /* Münzgrößen relativ zu echten Durchmessern (mm × 0.04 = cm Darstellung) */
  .money-coin-1    { width: 0.65cm; height: 0.65cm; }   /* 1 ct  – 16.25mm */
  .money-coin-2    { width: 0.75cm; height: 0.75cm; }   /* 2 ct  – 18.75mm */
  .money-coin-5    { width: 0.85cm; height: 0.85cm; }   /* 5 ct  – 21.25mm */
  .money-coin-10   { width: 0.79cm; height: 0.79cm; }   /* 10 ct – 19.75mm */
  .money-coin-20   { width: 0.89cm; height: 0.89cm; }   /* 20 ct – 22.25mm */
  .money-coin-50   { width: 0.97cm; height: 0.97cm; }   /* 50 ct – 24.25mm */
  .money-coin-100  { width: 0.93cm; height: 0.93cm; }   /* 1 €   – 23.25mm */
  .money-coin-200  { width: 1.03cm; height: 1.03cm; }   /* 2 €   – 25.75mm */
  /* Cent-Münzen größer skaliert in cent-only Geldbeuteln (gleiche Verhältnisse) */
  .money-cell-scale-large .money-coin-1   { width: 0.85cm; height: 0.85cm; }
  .money-cell-scale-large .money-coin-2   { width: 0.98cm; height: 0.98cm; }
  .money-cell-scale-large .money-coin-5   { width: 1.11cm; height: 1.11cm; }
  .money-cell-scale-large .money-coin-10  { width: 1.03cm; height: 1.03cm; }
  .money-cell-scale-large .money-coin-20  { width: 1.16cm; height: 1.16cm; }
  .money-cell-scale-large .money-coin-50  { width: 1.27cm; height: 1.27cm; }
  .money-note {
    object-fit: contain;
    border: 1px solid #999;
  }
  /* Scheingrößen: real 120×62 (5€), 127×67 (10€), 133×72 (20€), 140×77 (50€), 147×82 (100€) */
  .money-note-500   { width: 1.55cm; height: 0.80cm; }  /* 5 €   */
  .money-note-1000  { width: 1.65cm; height: 0.87cm; }  /* 10 €  */
  .money-note-2000  { width: 1.73cm; height: 0.94cm; }  /* 20 €  */
  .money-note-5000  { width: 1.82cm; height: 1.00cm; }  /* 50 €  */
  .money-note-10000 { width: 1.91cm; height: 1.07cm; }  /* 100 € */
  .money-answer {
    margin-top: 0.35cm;
    font-size: 12pt;
    text-align: center;
    width: 100%;
  }
  .money-line {
    display: inline-block;
    border-bottom: 1px solid #000;
    width: 5cm;
    height: 0.7cm;
    vertical-align: bottom;
  }

  .triangle-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5cm;
    justify-content: space-around;
  }
  .rechendreieck {
    flex: 0 0 auto;
  }
  .rechendreieck-svg {
    width: 7.5cm;
    height: 6.5cm;
  }

  .page-title {
    font-size: 16pt;
    font-weight: bold;
    margin-bottom: 0.2cm;
  }
</style>
"""


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang='de'>
<head>
  <meta charset='utf-8'>
  <title>{title}</title>
  <link rel='preconnect' href='https://fonts.googleapis.com'>
  <link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>
  <link href='https://fonts.googleapis.com/css2?family=Zain:ital,wght@0,200;0,300;0,400;0,700;0,800;0,900;1,300;1,400&display=swap' rel='stylesheet'>
  {styles}
</head>
<body>
  {worksheet_body}
</body>
</html>
"""


COMBINED_TEMPLATE = """<!DOCTYPE html>
<html lang='de'>
<head>
  <meta charset='utf-8'>
  <title>{title}</title>
  <link rel='preconnect' href='https://fonts.googleapis.com'>
  <link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>
  <link href='https://fonts.googleapis.com/css2?family=Zain:ital,wght@0,200;0,300;0,400;0,700;0,800;0,900;1,300;1,400&display=swap' rel='stylesheet'>
  {styles}
</head>
<body>
  {pages}
</body>
</html>
"""


def generate_tasks(task_configs: List[Dict], rng: random.Random) -> List[Tuple[str, Dict]]:
    generated = []
    for task in task_configs:
        task_type = task.get("type")
        if task_type not in TASK_GENERATORS:
            raise ValueError(f"Unsupported task type: {task_type}")
        generator = TASK_GENERATORS[task_type]
        result = generator(task, rng)
        if task.get("page_break_before"):
            result["_page_break_before"] = True
        generated.append((task_type, result))
    return generated


def render_tasks_pages(tasks: List[Tuple[str, Dict]], solution: bool) -> List[str]:
    """Split tasks into pages whenever a task has _page_break_before set.

    Returns a list of HTML strings, one per page.
    """
    pages: List[List[str]] = [[]]
    for task_type, data in tasks:
        renderer = TASK_RENDERERS[task_type]
        html = renderer(data, solution)
        if data.get("_page_break_before") and pages[-1]:
            pages.append([])
        pages[-1].append(html)
    return ["\n".join(page) for page in pages]


def render_tasks(tasks: List[Tuple[str, Dict]], solution: bool) -> str:
    return "\n".join(render_tasks_pages(tasks, solution))


def render_worksheet_body(left_label: str, right_label: str, pages_html: List[str],
                          page_title: str = "") -> str:
    title_html = f"<div class='worksheet-title'>{page_title}</div>" if page_title else ""
    header_html = (
        f"<div class='header'>"
        f"<div class='header-field'>{left_label}</div>"
        f"<div class='header-field'>{right_label}</div>"
        f"</div>"
    )
    pages: List[str] = []
    for idx, page_content in enumerate(pages_html):
        if idx == 0:
            inner = f"{header_html}\n    {title_html}\n    {page_content}"
        else:
            inner = page_content
        pages.append(f"  <div class='worksheet'>\n    {inner}\n  </div>")
    return "\n".join(pages)


def build_html(title: str, worksheet_body: str) -> str:
    return HTML_TEMPLATE.format(
        title=title,
        styles=STYLE_BLOCK,
        worksheet_body=worksheet_body,
    )


def build_combined_document(title: str, pages: List[Tuple[str, str]]) -> str:
    combined_pages = []
    for page_title, body in pages:
        combined_pages.append(f"<div class='worksheet-page'><div class='page-title'>{page_title}</div>{body}</div>")
    return COMBINED_TEMPLATE.format(title=title, styles=STYLE_BLOCK, pages="\n".join(combined_pages))


def generate_single_worksheet(cfg: Config, index: int) -> Tuple[str, str, str, str]:
    rng = random.Random(cfg.base_seed + index)
    tasks_data = generate_tasks(cfg.worksheet.tasks, rng)

    worksheet_pages = render_tasks_pages(tasks_data, solution=False)
    solution_pages = render_tasks_pages(tasks_data, solution=True)

    worksheet_body = render_worksheet_body(
        cfg.worksheet.header_left_label,
        cfg.worksheet.header_right_label,
        worksheet_pages,
        cfg.worksheet.page_title,
    )

    solution_body = render_worksheet_body(
        cfg.worksheet.header_left_label,
        cfg.worksheet.header_right_label,
        solution_pages,
        cfg.worksheet.page_title,
    )

    worksheet_html = build_html(
        title=f"Arbeitsblatt {index + 1}",
        worksheet_body=worksheet_body,
    )

    solution_html = build_html(
        title=f"Arbeitsblatt {index + 1} – Lösung",
        worksheet_body=solution_body,
    )

    return worksheet_html, solution_html, worksheet_body, solution_body


def write_files(cfg: Config, index: int, worksheet_html: str, solution_html: str) -> None:
    ensure_output_dir(cfg.output.out_dir)
    worksheet_path = cfg.output.out_dir / f"{cfg.output.file_prefix}_{index + 1:03d}.html"
    solution_path = cfg.output.out_dir / f"{cfg.output.file_prefix}_{index + 1:03d}_loesung.html"
    worksheet_path.write_text(worksheet_html, encoding="utf-8")
    solution_path.write_text(solution_html, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate printable math worksheets")
    parser.add_argument("--config", type=Path, required=True, help="Path to config.yaml")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    combined_pages: List[Tuple[str, str]] = []
    for i in range(cfg.worksheet_count):
        worksheet_html, solution_html, worksheet_body, solution_body = generate_single_worksheet(cfg, i)
        write_files(cfg, i, worksheet_html, solution_html)
        combined_pages.append((f"Arbeitsblatt {i + 1}", worksheet_body))
        combined_pages.append((f"Arbeitsblatt {i + 1} – Lösung", solution_body))

    if combined_pages:
        combined_html = build_combined_document(
            title=f"{cfg.output.file_prefix} – Gesamtpaket",
            pages=combined_pages,
        )
        combined_path = cfg.output.out_dir / f"{cfg.output.file_prefix}_gesamt.html"
        ensure_output_dir(cfg.output.out_dir)
        combined_path.write_text(combined_html, encoding="utf-8")

    print(f"Generated {cfg.worksheet_count} worksheets in {cfg.output.out_dir}")


if __name__ == "__main__":
    main()
