def handler(event, context):
    """
    Simple example handler.

    - event: dict with keys {method, path, query, headers, body}
    - context: dict with metadata like {function}

    Return either:
    - dict with keys {statusCode, headers, body}
    - any JSON-serializable object (becomes JSON body)
    - str (becomes text body)
    """
    name = context.get("function", "fn")
    if event.get("method") == "GET":
        who = event.get("query", {}).get("name", "world")
        return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": {"hello": who, "from": name}}
    else:
        return {"statusCode": 200, "headers": {"Content-Type": "text/plain"}, "body": f"Handled {event.get('method')} on {event.get('path')}"}

