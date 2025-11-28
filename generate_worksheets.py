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
    min_value = int(data.get("min_value", 0))
    max_value = int(data.get("max_value", 20))
    columns = int(data.get("columns", 3))
    equal_probability = float(data.get("equal_probability", 0.2))

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
    min_value = int(data.get("min_value", 0))
    max_value = int(data.get("max_value", 100))
    given_field = data.get("given_field", "middle")

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

    items = []
    while len(items) < item_count:
        op = rng.choice(operations)
        a = rng.randint(min_value, max_value)
        b = rng.randint(min_value, max_value)
        result = a + b if op == "+" else a - b

        if not allow_negative and result < 0:
            continue
        if result < min_value or result > max_value:
            continue

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


def dice_representation(value: int) -> str:
    tens = value // 10
    ones = value % 10
    tally_groups = []
    for _ in range(tens):
        tally_groups.append("|||||")
    ones_dice = []
    for _ in range(ones):
        ones_dice.append("●")
    tally_html = " ".join(f"<span class='tally'>{group}</span>" for group in tally_groups)
    ones_html = "".join(ones_dice)
    if tally_html and ones_html:
        return f"<div class='dice-combo'><span class='tallies'>{tally_html}</span> <span class='dice-face'>{ones_html}</span></div>"
    if tally_html:
        return f"<div class='dice-combo'><span class='tallies'>{tally_html}</span></div>"
    return f"<div class='dice-combo'><span class='dice-face'>{ones_html}</span></div>"


def generate_number_word_table(data: Dict, rng: random.Random) -> Dict:
    first_row_example = bool(data.get("first_row_example", True))
    example_number = int(data.get("example_number", 49))
    row_count = int(data.get("row_count", 5))
    min_value = int(data.get("min_value", 11))
    max_value = int(data.get("max_value", 99))
    given_columns = data.get("given_columns", ["word"])

    rows = []
    if first_row_example:
        rows.append({
            "number": example_number,
            "word": number_to_word(example_number),
            "dice": dice_representation(example_number),
            "given": ["word", "dice", "number"],
        })

    while len(rows) < row_count + (1 if first_row_example else 0):
        value = rng.randint(min_value, max_value)
        rows.append({
            "number": value,
            "word": number_to_word(value),
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


def generate_operation_table(data: Dict, rng: random.Random) -> Dict:
    tables_data = []
    result_range = data.get("result_range")
    if not result_range or "min" not in result_range or "max" not in result_range:
        raise ValueError("result_range with min and max is required for operation_table")
    min_result = int(result_range["min"])
    max_result = int(result_range["max"])

    for table in data.get("tables", []):
        operation = table.get("operation", "+")
        row_headers = parse_header_sequence(table.get("row_headers", []))
        col_headers = parse_header_sequence(table.get("col_headers", []))
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
    major_tick = int(data.get("major_tick_interval", 10))
    values = data.get("values")
    if values is None:
        values = []
        possible_numbers = list(range(start, end + 1))
        rng.shuffle(possible_numbers)
        for number in possible_numbers:
            if len(values) >= 5:
                break
            if number % major_tick != 0:
                values.append(number)
        values.sort()
    values = [int(v) for v in values]
    return {
        "title": data.get("title", "Zahlenstrahl"),
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
            f"<div class='compare-item'><span class='boxed-number'>{a}</span>"
            f"<span class='compare-circle'>{sign}</span><span class='boxed-number'>{b}</span></div>"
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
    ordered_strs = [str(n) if solution else "" for n in data["sorted_numbers"]]
    separators = " <span class='compare-symbol'>{}</span> ".format("<" if data["order"] == "increasing" else ">")
    chain_content = separators.join(f"<span class='number-box'>{text}</span>" for text in ordered_strs)
    if not data["show_symbols"]:
        chain_content = "".join(f"<span class='number-box'>{text}</span>" for text in ordered_strs)
    return f"""<div class='task'>
  <div class='task-title'>{data['title']}</div>
  <div class='ordering-numbers'>{numbers_str}</div>
  <div class='ordering-chain'>{chain_content}</div>
</div>"""


def render_operation_table(data: Dict, solution: bool) -> str:
    tables_html = []
    for table in data["tables"]:
        header_cells = "<th></th>" + "".join(f"<th>{c}</th>" for c in table["col_headers"])
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
  <div class='operation-label'>Rechenart: {table['operation']}</div>
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
    ticks = []
    total_range = data["end"] - data["start"]
    for value in range(data["start"], data["end"] + 1):
        major = value % data["major_tick"] == 0
        tick_class = "major" if major else "minor"
        label = str(value) if major else ""
        position = ((value - data["start"]) / total_range) * 100 if total_range else 0
        ticks.append(
            f"<div class='tick {tick_class}' style='left: {position}%'>"
            f"<div class='tick-mark'></div><div class='tick-label'>{label}</div></div>"
        )
    values_html = []
    for v in data["values"]:
        box_value = str(v) if solution else ""
        position = ((v - data["start"]) / total_range) * 100
        values_html.append(
            f"<div class='number-line-box' style='left: {position}%'>"
            f"<span class='number-box'>{box_value}</span><div class='connector'></div></div>"
        )
    return f"""<div class='task'>
  <div class='task-title'>{data['title']}</div>
  <div class='number-line-container'>
    <div class='number-line-track'>
      {''.join(ticks)}
      {''.join(values_html)}
    </div>
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
  }
  .tallies .tally {
    margin-right: 0.1cm;
  }
  .dice-face {
    font-size: 16pt;
    letter-spacing: 0.05cm;
  }

  .ordering-numbers {
    margin-bottom: 0.3cm;
  }
  .ordering-chain {
    display: flex;
    align-items: center;
    gap: 0.2cm;
  }
  .compare-symbol {
    font-size: 14pt;
  }

  .operation-table-grid {
    display: grid;
    gap: 0.5cm;
  }
  .operation-table {
    border: 1px solid #000;
    padding: 0.2cm;
  }
  .operation-label {
    font-weight: bold;
    margin-bottom: 0.2cm;
  }

  .number-line-container {
    position: relative;
    height: 5cm;
  }
  .number-line-track {
    position: absolute;
    bottom: 1cm;
    left: 0;
    right: 0;
    height: 2cm;
    border-bottom: 2px solid #000;
  }
  .tick {
    position: absolute;
    bottom: 0;
    text-align: center;
  }
  .tick-mark {
    width: 2px;
    margin: 0 auto;
    background: #000;
  }
  .tick.major .tick-mark { height: 1cm; }
  .tick.minor .tick-mark { height: 0.6cm; }
  .tick-label {
    margin-top: 0.1cm;
    font-size: 10pt;
  }
  .number-line-box {
    position: absolute;
    bottom: 1.4cm;
    transform: translateX(-50%);
    text-align: center;
  }
  .number-line-box .connector {
    width: 2px;
    height: 0.4cm;
    background: #000;
    margin: 0 auto;
  }

  .number-dictation {
    display: flex;
    gap: 0.1cm;
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
  <div class='worksheet'>
    <div class='header'>
      <div class='header-field'>{left_label}</div>
      <div class='header-field'>{right_label}</div>
    </div>
    {tasks}
  </div>
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


def build_html(title: str, left_label: str, right_label: str, tasks_html: str) -> str:
    return HTML_TEMPLATE.format(
        title=title,
        styles=STYLE_BLOCK,
        left_label=left_label,
        right_label=right_label,
        tasks=tasks_html,
    )


def generate_single_worksheet(cfg: Config, index: int) -> Tuple[str, str]:
    rng = random.Random(cfg.base_seed + index)
    tasks_data = generate_tasks(cfg.worksheet.tasks, rng)

    worksheet_html = build_html(
        title=f"Arbeitsblatt {index + 1}",
        left_label=cfg.worksheet.header_left_label,
        right_label=cfg.worksheet.header_right_label,
        tasks_html=render_tasks(tasks_data, solution=False),
    )

    solution_html = build_html(
        title=f"Arbeitsblatt {index + 1} – Lösung",
        left_label=cfg.worksheet.header_left_label,
        right_label=cfg.worksheet.header_right_label,
        tasks_html=render_tasks(tasks_data, solution=True),
    )

    return worksheet_html, solution_html


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
    for i in range(cfg.worksheet_count):
        worksheet_html, solution_html = generate_single_worksheet(cfg, i)
        write_files(cfg, i, worksheet_html, solution_html)
    print(f"Generated {cfg.worksheet_count} worksheets in {cfg.output.out_dir}")


if __name__ == "__main__":
    main()
