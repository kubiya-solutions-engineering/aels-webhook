import argparse
import os
import sys

import requests


def get_pr_diff(access_token: str, repository_url: str, pull_request_number: int):
    """
    Fetches the diff for a specific pull request using the PyGithub library.

    Args:
        access_token: Your GitHub Personal Access Token.
        repository_url: The full URL of the GitHub repository (e.g., "https://github.com/owner/repo").
        pull_request_number: The number of the pull request.
    """
    if not access_token:
        raise ValueError(
            "GitHub token not found. Please set the GITHUB_TOKEN environment variable."
        )

    diff_url = f"https://github.com/{repository_url}/pull/{pull_request_number}.diff"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3.diff",  # Best practice to specify the media type
    }

    response = requests.get(diff_url, headers=headers)
    response.raise_for_status()

    print("\n--- PULL REQUEST DIFF ---")
    print(response.text)


def main():
    """
    Parses command-line arguments and orchestrates fetching the PR diff.
    """
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="Rewrite of 'gh pr diff' using the PyGithub SDK. Fetches the diff of a GitHub Pull Request.",
        epilog="Note: Your GitHub token must be available in the GH_TOKEN environment variable.",
    )
    parser.add_argument(
        "repo_url",
        help="The full URL of the GitHub repository (e.g., 'https://github.com/owner/repo').",
    )
    parser.add_argument("pr_number", type=int, help="The number of the pull request.")
    args = parser.parse_args()

    # --- Token and Input Validation ---
    token = os.getenv("GH_TOKEN")
    if not token:
        print("Error: The GH_TOKEN environment variable is not set.", file=sys.stderr)
        print("Please set it to your GitHub Personal Access Token.", file=sys.stderr)
        sys.exit(1)

    # --- Execute Core Logic ---
    try:
        get_pr_diff(token, args.repo_url, args.pr_number)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
