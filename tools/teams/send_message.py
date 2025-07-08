import argparse
import json

import httpx
from .webhook_config import DEFAULT_WEBHOOK_URL, PIPELINE_WEBHOOK_MAPPING


def send_message(webhook_url: str, message: str) -> None:
    response = httpx.post(
        webhook_url,
        json=message,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()


def main(
    pipeline_webhook_mapping: dict[str, str],
    default_webhook_url: str,
) -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Send message to Teams webhook for a given pipeline"
    )
    parser.add_argument(
        "pipeline_name", help="Name of the pipeline to get webhook URL for"
    )
    parser.add_argument("payload", help="JSON string with message payload")

    args = parser.parse_args()
    pipeline_name = args.pipeline_name
    payload = args.payload

    if webhook_url := pipeline_webhook_mapping.get(pipeline_name, default_webhook_url):
        print(f"Sending message to webhook for pipeline: {pipeline_name}")
        print(f"Webhook URL: {webhook_url}")
    else:
        raise ValueError(f"No Teams webhook configured for pipeline: {pipeline_name}")

    # Parse JSON payload
    try:
        message_payload = json.loads(payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON payload: {e}")

    send_message(webhook_url=webhook_url, message=message_payload)
    print("Message sent successfully!")


if __name__ == "__main__":
    main(
        pipeline_webhook_mapping=PIPELINE_WEBHOOK_MAPPING,
        default_webhook_url=DEFAULT_WEBHOOK_URL,
    )
