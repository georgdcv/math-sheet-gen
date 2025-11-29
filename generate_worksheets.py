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
        ),
    )


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ---------- Task generation helpers ----------

def generate_number_dictation(data: Dict, rng: random.Random) -> Dict:
    return {
        "box_count": int(data.get("box_count", 10)),
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
    max_second_operand = max(min_value, max(0, min(int(data.get("max_second_operand", 10)), max_value)))

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
            a = rng.randint(min_value, max_value)
            b = rng.randint(min_value, max_second_operand)
            result = a + b if op_symbol == "+" else a - b

            if not allow_negative and result < 0:
                continue
            if result < min_value or result > max_value:
                continue

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
    }
    circles = "".join(
        f"<circle cx='{x}' cy='{y}' r='8' />" for x, y in pip_positions.get(face_value, [])
    )
    return "<svg class='dice-svg' viewBox='0 0 100 100' role='img' aria-label='Würfel'>" f"{circles}</svg>"


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

    return {
        "title": data.get("title", "Zahlwort – Würfelbild – Zahl"),
        "rows": rows,
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
) -> Tuple[List[int], List[int]]:
    possible_values = list(range(10, 101, 10))

    def pick_values(count: int) -> List[int]:
        if count <= len(possible_values):
            return rng.sample(possible_values, count)
        choices = [rng.choice(possible_values) for _ in range(count)]
        rng.shuffle(choices)
        return choices

    for _ in range(1000):
        rows = pick_values(row_count)
        cols = pick_values(col_count)

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

        row_headers_source = table.get("row_headers")
        col_headers_source = table.get("col_headers")
        if row_headers_source is None and col_headers_source is None:
            row_headers, col_headers = _generate_random_headers(
                operation, row_count, col_count, rng, min_result, max_result
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

            row_headers = _enforce_tens_headers(parse_header_sequence(row_headers_source))
            col_headers = _enforce_tens_headers(parse_header_sequence(col_headers_source))
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


TASK_GENERATORS = {
    "number_dictation": generate_number_dictation,
    "compare_numbers": generate_compare_numbers,
    "pre_succ_table": generate_pre_succ_table,
    "arithmetic_list": generate_arithmetic_list,
    "number_word_table": generate_number_word_table,
    "ordering": generate_ordering,
    "operation_table": generate_operation_table,
    "number_line": generate_number_line,
}


# ---------- Rendering helpers ----------

def render_number_boxes(count: int, content: Optional[List[str]] = None) -> str:
    boxes = []
    for i in range(count):
        text = content[i] if content and i < len(content) else ""
        boxes.append(f"<span class='number-box'>{text}</span>")
    return "".join(boxes)


def render_number_dictation(data: Dict, solution: bool) -> str:
    helper_content = None
    if solution and data.get("show_helper_numbers"):
        helper_content = [str(i + 1) for i in range(data["box_count"])]
    boxes = render_number_boxes(data["box_count"], helper_content)
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


def render_arithmetic_list(data: Dict, solution: bool) -> str:
    items_html = []
    for a, op, b, result in data["items"]:
        result_html = str(result) if solution else ""
        items_html.append(f"<div class='arithmetic-item'>{a} {op} {b} = <span class='number-box'>{result_html}</span></div>")
    column_class = f"cols-{data['columns']}"
    return f"""<div class='task'>
  <div class='task-title'>{data['title']}</div>
  <div class='arithmetic-grid {column_class}'>
    {''.join(items_html)}
  </div>
</div>"""


def render_number_word_table(data: Dict, solution: bool) -> str:
    rows_html = []
    for row in data["rows"]:
        given_cols = set(row["given"] if not solution else ["word", "dice", "number"])
        word_cell = row["word"] if "word" in given_cols else ""
        dice_cell = row["dice"] if "dice" in given_cols else ""
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


TASK_RENDERERS = {
    "number_dictation": render_number_dictation,
    "compare_numbers": render_compare_numbers,
    "pre_succ_table": render_pre_succ_table,
    "arithmetic_list": render_arithmetic_list,
    "number_word_table": render_number_word_table,
    "ordering": render_ordering,
    "operation_table": render_operation_table,
    "number_line": render_number_line,
}


STYLE_BLOCK = """
<style>
  @page {
    size: A4 portrait;
    margin: 1.5cm;
  }

  body {
    font-family: 'Zain', sans-serif;
    font-size: 12pt;
  }

  .worksheet {
    page-break-after: always;
  }

  .header {
    display: flex;
    justify-content: space-between;
    border-bottom: 1px solid #000;
    padding-bottom: 0.3cm;
    margin-bottom: 0.5cm;
  }

  .header-field {
    flex: 0 0 48%;
  }

  .task {
    border: 1px solid #000;
    padding: 0.4cm;
    margin-bottom: 0.6cm;
  }

  .task-title {
    font-weight: bold;
    margin-bottom: 0.2cm;
  }

  .number-box {
    display: inline-block;
    width: 1cm;
    height: 1cm;
    border: 1px solid #000;
    margin-right: 0.1cm;
    text-align: center;
    vertical-align: middle;
    line-height: 1cm;
  }

  .compare-grid, .arithmetic-grid {
    display: grid;
    gap: 0.4cm;
  }
  .compare-grid.cols-2, .arithmetic-grid.cols-2 { grid-template-columns: repeat(2, 1fr); }
  .compare-grid.cols-3, .arithmetic-grid.cols-3 { grid-template-columns: repeat(3, 1fr); }
  .compare-grid.cols-4, .arithmetic-grid.cols-4 { grid-template-columns: repeat(4, 1fr); }

  .compare-item, .arithmetic-item {
    display: flex;
    align-items: center;
    gap: 0.2cm;
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

  .worksheet-page {
    page-break-after: always;
    break-after: page;
  }
  .worksheet-page:last-child {
    page-break-after: auto;
    break-after: auto;
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
        generated.append((task_type, generator(task, rng)))
    return generated


def render_tasks(tasks: List[Tuple[str, Dict]], solution: bool) -> str:
    rendered = []
    for task_type, data in tasks:
        renderer = TASK_RENDERERS[task_type]
        rendered.append(renderer(data, solution))
    return "\n".join(rendered)


def render_worksheet_body(left_label: str, right_label: str, tasks_html: str) -> str:
    return f"""  <div class='worksheet'>
    <div class='header'>
      <div class='header-field'>{left_label}</div>
      <div class='header-field'>{right_label}</div>
    </div>
    {tasks_html}
  </div>"""


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

    worksheet_tasks_html = render_tasks(tasks_data, solution=False)
    solution_tasks_html = render_tasks(tasks_data, solution=True)

    worksheet_body = render_worksheet_body(
        cfg.worksheet.header_left_label,
        cfg.worksheet.header_right_label,
        worksheet_tasks_html,
    )

    solution_body = render_worksheet_body(
        cfg.worksheet.header_left_label,
        cfg.worksheet.header_right_label,
        solution_tasks_html,
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
