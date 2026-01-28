import json
from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def _collect_x_mcp_blocks(spec: dict) -> list[dict]:
    blocks = []
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return blocks
    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            x_mcp = operation.get("x-mcp")
            if isinstance(x_mcp, dict):
                blocks.append(x_mcp)
    return blocks


def _assert_no_refs(schema: object) -> None:
    if isinstance(schema, dict):
        assert "$ref" not in schema
        for value in schema.values():
            _assert_no_refs(value)
    elif isinstance(schema, list):
        for item in schema:
            _assert_no_refs(item)


def _load_all_json(path: Path) -> list[dict]:
    content = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    idx = 0
    items: list[dict] = []
    while idx < len(content):
        while idx < len(content) and content[idx].isspace():
            idx += 1
        if idx >= len(content):
            break
        obj, next_idx = decoder.raw_decode(content, idx)
        if isinstance(obj, dict):
            items.append(obj)
        idx = next_idx
    return items


def test_example_configs_valid_json():
    for filename in ["openapi-users-extended.json", "openapi-todo-extended.json"]:
        data_list = _load_all_json(EXAMPLES_DIR / filename)
        assert data_list, f"No JSON documents found in {filename}"
        for data in data_list:
            assert data.get("openapi") == "3.0.0"


def test_x_mcp_schemas_inline():
    for filename in ["openapi-users-extended.json", "openapi-todo-extended.json"]:
        spec_list = _load_all_json(EXAMPLES_DIR / filename)
        for spec in spec_list:
            x_mcp_blocks = _collect_x_mcp_blocks(spec)
            assert x_mcp_blocks, f"No x-mcp blocks found in {filename}"
            for x_mcp in x_mcp_blocks:
                input_schema = x_mcp.get("inputSchema")
                output_schema = x_mcp.get("outputSchema")
                if isinstance(input_schema, dict):
                    _assert_no_refs(input_schema)
                if isinstance(output_schema, dict):
                    _assert_no_refs(output_schema)
