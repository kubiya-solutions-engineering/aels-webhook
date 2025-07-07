import datetime as dt
import argparse
import json


def format_timestamp(timestamp: str | None) -> str:
    """Format ISO timestamp to human-readable format."""
    if not timestamp or timestamp == "<no value>":
        timestamp = dt.datetime.now(dt.UTC).isoformat() + "Z"

    try:
        # Parse ISO format
        dt_string = dt.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt_string.strftime("%b %d, %Y at %I:%M %p UTC")
    except (ValueError, AttributeError):
        return timestamp


def create_teams_payload(
    pr_title: str,
    pr_url: str,
    workflow_url: str,
    author: str,
    gh_summary_url: str,
    triggered_at: str | None = None,
) -> dict:
    """Create the Teams MessageCard payload."""

    # Process variables
    formatted_time = format_timestamp(triggered_at)
    
    # Create the payload
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "FF0000",
        "summary": pr_title,
        "sections": [{
            "activityTitle": f"🚨 {pr_title}",
            "activitySubtitle": f"Workflow failed at {formatted_time}",
            "facts": [
                {
                    "name": "👤 Author",
                    "value": author,
                },
                {
                    "name": "Pull Request URL",
                    "value": pr_url,
                },
                {
                    "name": "Failed Workflow URL",
                    "value": workflow_url,
                },
            ],
            "markdown": True,
        }],
        "potentialAction": [
            {
                "@type": "OpenUri",
                "name": "View PR",
                "targets": [{
                    "os": "default",
                    "uri": pr_url,
                }]
            },
            {
                "@type": "OpenUri",
                "name": "View PR Analysis",
                "targets": [{
                    "os": "default",
                    "uri": gh_summary_url,
                }]
            },
            {
                "@type": "OpenUri",
                "name": "View Failed Workflow",
                "targets": [{
                    "os": "default",
                    "uri": workflow_url,
                }]
            }
        ]
    }
    
    return payload


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Create Teams MessageCard payload for workflow summary")
    
    # Required arguments
    parser.add_argument("pr_title", help="Title of the pull request")
    parser.add_argument("pr_url", help="URL of the pull request")
    parser.add_argument("author", help="Author of the pull request")
    parser.add_argument("workflow_url", help="GitHub summary URL")
    parser.add_argument("gh_summary_url", help="Stack trace URL")
    
    # Optional argument
    parser.add_argument("--triggered-at", help="Timestamp when the workflow was triggered (ISO format)")
    
    args = parser.parse_args()
    
    # Create the Teams payload
    payload = create_teams_payload(
        pr_title=args.pr_title,
        pr_url=args.pr_url,
        author=args.author,
        gh_summary_url=args.gh_summary_url,
        workflow_url=args.workflow_url,
        triggered_at=args.triggered_at
    )
    
    # Output the JSON payload
    print(json.dumps(payload))


if __name__ == "__main__":
    main() 