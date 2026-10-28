import json

# Simulate the MCP tools discovered by your agent.
mcp_tools = {
    "search_repositories": object(),
    "list_issues": object(),
    "search_issues": object(),
    "issue_read": object(),
}


def validate_tool_request(name, raw_arguments):
    """Validate a model-generated tool name and JSON arguments."""
    # 1. Check that the requested tool is allowed.
    if name not in mcp_tools:
        return False, None, f"Unknown tool: {name}"

    # 2. Parse the JSON arguments.
    try:
        arguments = json.loads(raw_arguments)
    except (json.JSONDecodeError, TypeError):
        return False, None, "Tool arguments are not valid JSON"

    # 3. Ensure the parsed arguments are a JSON object / Python dict.
    if not isinstance(arguments, dict):
        return False, None, "Tool arguments must be a JSON object"

    return True, arguments, "Validation passed"


def run_test(test_name, name, raw_arguments, expected_valid):
    valid, arguments, message = validate_tool_request(name, raw_arguments)
    passed = valid == expected_valid

    print(f"\n{test_name}")
    print(f"  Tool name: {name}")
    print(f"  Raw arguments: {raw_arguments}")
    print(f"  Result: {'PASS' if passed else 'FAIL'}")
    print(f"  Validation message: {message}")
    if arguments is not None:
        print(f"  Parsed arguments: {arguments}")

    return passed


if __name__ == "__main__":
    results = [
        run_test(
            "TEST 1 — Valid tool name and valid JSON",
            "search_repositories",
            '{"query": "MCP language:python", "perPage": 5}',
            expected_valid=True,
        ),
        run_test(
            "TEST 2 — Unknown tool name",
            "delete_repository",
            '{"owner": "example", "repo": "demo"}',
            expected_valid=False,
        ),
        run_test(
            "TEST 3 — Invalid JSON arguments",
            "search_repositories",
            '{"query": "MCP", "perPage": }',
            expected_valid=False,
        ),
    ]

    print("\n" + "=" * 45)
    print(f"Tests passed: {sum(results)}/{len(results)}")
    print("=" * 45)

    if not all(results):
        raise SystemExit(1)
