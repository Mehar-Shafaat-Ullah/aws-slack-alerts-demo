import json
import os
import urllib3

http = urllib3.PoolManager()
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

def _post_to_slack(text, blocks=None):
    if not SLACK_WEBHOOK_URL:
        raise RuntimeError("SLACK_WEBHOOK_URL env var is not set")
    payload = {"text": text}
    if blocks:
        payload["blocks"] = blocks
    r = http.request(
        "POST",
        SLACK_WEBHOOK_URL,
        body=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    if r.status >= 300:
        raise RuntimeError(f"Slack webhook returned {r.status}: {r.data}")

def lambda_handler(event, context):
    # Send a compact summary for CodePipeline and CodeBuild events
    detail = event.get("detail", {})
    source = event.get("source")
    detail_type = event.get("detail-type")

    text = f":rocket: *{detail_type}* from `{source}`\n```{json.dumps(detail)}```"
    _post_to_slack(text)
    return {"ok": True}