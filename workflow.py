from kubiya_workflow_sdk.dsl_experimental import *  # noqa
import inspect

from kubiya_workflow_sdk.dsl_experimental import WorkflowParams, EnvironmentVariables

from tools.teams import send_message, webhook_config, prepare_summary
from tools.gh import get_diff


def build_workflow(
    kubiya_host: str,
    kubiya_api_key: str,
    workflow_run_id: int,
    workflow_name: str,
    workflow_url: str,
    pr_title: str,
    pr_url: str,
    pr_number: int,
    repo_url: str,
    author: str,
    triggered_at: str,
) -> Workflow:
    param_pipeline_name = Parameter(name="pipeline_name", value=workflow_name)
    param_pr_title = Parameter(name="pr_title", value=pr_title)
    param_pr_url = Parameter(name="pr_url", value=pr_url)
    param_repo_url = Parameter(name="repo_url", value=repo_url)
    param_pr_number = Parameter(name="pr_number", value=pr_number)
    param_author = Parameter(name="author", value=author)
    param_workflow_url = Parameter(name="workflow_url", value=workflow_url)
    param_workflow_run_id = Parameter(name="workflow_run_id", value=workflow_run_id)
    param_triggered_at = Parameter(name="triggered_at", value=triggered_at)

    step_0 = CommandStep(
        name="echo-show-input-params",
        command=f"""echo "Workflow Parameters:"
echo "{param_pipeline_name.name}=${param_pipeline_name.name};" &&  \
echo "{param_pr_title.name}=${param_pr_title.name};" && \
echo "{param_pr_url.name}=${param_pr_url.name};" && \
echo "{param_repo_url.name}=${param_repo_url.name};" && \
echo "{param_pr_number.name}=${param_pr_number.name};" && \
echo "{param_author.name}=${param_author.name};" && \
echo "{param_workflow_url.name}=${param_workflow_url.name};" && \
echo "{param_workflow_run_id.name}=${param_workflow_run_id.name};" && \
echo "{param_triggered_at.name}=${param_triggered_at.name};"
""",
        output="EXAMPLE",
    )

    step_1 = ExecutorStep(
        name="get-github-token",
        description="Get GitHub App token from Kubiya",
        output="GH_TOKEN",
        depends=[step_0.name],
        executor=Executor(
            type=ExecutorType.KUBIYA,
            config=KubiyaExecutorConfig(
                url="api/v1/integration/github_app/token/72636372",
                method=HTTPMethod.GET,
            ),
        ),
    )

    step_2 = ExecutorStep(
        name="get-slack-integration",
        description="Get Slack integration info from Kubiya",
        output="SLACK_TOKEN",
        executor=Executor(
            type=ExecutorType.KUBIYA,
            config=KubiyaExecutorConfig(
                url="api/v2/integrations/slack",
                method=HTTPMethod.GET,
            ),
        ),
    )

    step_3_2 = ExecutorStep(
        name="get-gh-pr-diff",
        description="Get GitHub PR diff",
        output="GH_PR_DIFF",
        depends=[step_1.name],
        executor=Executor(
            type=ExecutorType.TOOL,
            config=ToolExecutorConfig(
                secrets={"GH_TOKEN": f"${step_1.output}"},
                args={
                    "repo": f"${param_repo_url.name}",
                    "number": f"${param_pr_number.name}",
                },
                tool_def=ToolDef(
                    name="github_pr_diff",
                    description="Shows github PR Diff",
                    type="docker",
                    image="python:3.12-slim",
                    secrets=["GH_TOKEN"],
                    content=f"""set -e
pip install -qqq -r /opt/scripts/reqs.txt
python /opt/scripts/get_diff.py $repo $number
""",
                    with_files=[
                        FileDefinition(
                            destination="/opt/scripts/reqs.txt",
                            content="requests==2.32.3",
                        ),
                        FileDefinition(
                            destination="/opt/scripts/get_diff.py",
                            content=inspect.getsource(get_diff),
                        ),
                    ],
                ),
            ),
        ),
    )

    step_3 = ExecutorStep(
        name="get-gh-pr-diff",
        depends=[step_1.name],
        description="Get GitHub PR diff",
        output="GH_PR_DIFF",
        executor=Executor(
            type=ExecutorType.TOOL,
            config=ToolExecutorConfig(
                tool_def=ToolDef(
                    name="github_pr_diff",
                    description="Shows github PR Diff",
                    type="docker",
                    image="maniator/gh:latest",
                    secrets=["GH_TOKEN"],
                    content=f"""set -e
echo "Diff of Pull request # ${param_pr_number.value}"
echo "`gh pr diff --repo $repo_url $pr_number`"
""",
                ),
                secrets={"GH_TOKEN": f"${step_1.output}"},
                args={
                    "repo_url": "${repo_url}",
                    "pr_number": "${pr_number}",
                },
            ),
        ),
    )

    step_4 = ExecutorStep(
        name="failure-analysis",
        description="Analyze the collected data and generate comprehensive failure report",
        depends=[
            step_3.name,
        ],
        output="ANALYSIS_REPORT",
        executor=Executor(
            type=ExecutorType.AGENT,
            config=AgentExecutorConfig(
                agent_name="demo-teammate",
                message=f"""Analyze the CI/CD pipeline failure using the collected data:

PR Files: ${step_3.output}

Your task is to:
1. Highlights key information first:
   - What failed
   - Why it failed 
   - How to fix it

2. Provide a comprehensive analysis of the failure including:
   - Root cause analysis
   - Impact assessment
   - Recommended fixes
   - Prevention strategies

Format your response with clear sections and actionable insights.""",
            ),
        ),
    )

    step_5 = ExecutorStep(
        name="post-pr-summary",
        depends=[step_4.name],
        output="PR_MESSAGE_URL",
        description="Post failure analysis comment on the GitHub PR",
        executor=Executor(
            type=ExecutorType.TOOL,
            config=ToolExecutorConfig(
                tool_def=ToolDef(
                    name="github_pr_comment_workflow_failure",
                    description="Post failure analysis comment on the GitHub PR",
                    type="docker",
                    image="maniator/gh:latest",
                    secrets=["GH_TOKEN"],
                    content="""#!/bin/sh
set -euo pipefail

echo "=== GitHub PR Comment Tool Started ==="
echo "Repo: $repo_url"
echo "PR Number: $pr_number"
echo "Analysis report length: $(echo "$analysis_report" | wc -c) characters"
echo "Failed logs length: $(echo "$failed_logs" | wc -c) characters"

# Check if GH_TOKEN is available
if [ -z "$GH_TOKEN" ]; then
    echo "❌ ERROR: GH_TOKEN is not set"
    exit 1
fi

echo "Token length: ${#GH_TOKEN} characters"
echo "Token preview: ${GH_TOKEN:0:10}..."

# Ensure jq is available
if ! command -v jq >/dev/null 2>&1; then
    echo "Installing jq..."
    apk add --no-cache jq
fi

# Test GitHub API access first
echo "=== Testing GitHub API Access ==="
API_TEST=$(gh api user 2>&1) || {
    echo "❌ GITHUB API ERROR: Failed to authenticate with GitHub API"
    echo "Error: $API_TEST"
    exit 1
}

echo "✅ GitHub API authentication successful"
echo "Authenticated as: $(echo "$API_TEST" | jq -r '.login' 2>/dev/null || echo 'Unknown')"

# Check if PR exists
echo "=== Checking if PR exists ==="
PR_CHECK=$(gh api "repos/$repo_url/pulls/$pr_number" 2>&1) || {
    echo "❌ PR ERROR: Could not find PR #$pr_number in $repo_url"
    echo "Error: $PR_CHECK"
    exit 1
}

echo "✅ PR #$pr_number exists in $repo_url"
echo "PR Title: $(echo "$PR_CHECK" | jq -r '.title' 2>/dev/null || echo 'Unknown')"

# Process analysis report and logs safely
analysis_summary=$(echo "$analysis_report" | head -c 2000 | sed 's/`/\\\\`/g')
log_summary=$(echo "$failed_logs" | head -c 1500 | sed 's/`/\\\\`/g')

# Create the comment content with better formatting
read -r -d '' COMMENT_TEMPLATE << 'EOF' || true
## 🚨 CI/CD Pipeline Failure Analysis

### 📊 Summary
The workflow execution failed during the CI/CD pipeline. Here's the automated analysis:

### 🔍 Root Cause Analysis
```
%s
```

### 📋 Error Details
```
%s
```

### 🔗 Quick Links
- [View Workflow Run](%s)
- [Repository Actions](https://github.com/%s/actions)

---
<sub>🤖 This analysis was automatically generated by the CI/CD failure detection system</sub>
EOF

# Get workflow URL from the run view
workflow_url=$(echo "$workflow_run_view" | grep -o 'https://github.com/[^/]*/[^/]*/actions/runs/[0-9]*' | head -1 || echo "https://github.com/$repo_url/actions")

# Format the comment using printf
COMMENT=$(printf "$COMMENT_TEMPLATE" "$analysis_summary" "$log_summary" "$workflow_url" "$repo_url")

echo "=== Posting PR Comment ==="
echo "Comment length: ${#COMMENT} characters"

# Create a temporary file for the comment to handle special characters properly
COMMENT_FILE=$(mktemp)
echo "$COMMENT" > "$COMMENT_FILE"

# Post the comment and capture response
COMMENT_RESPONSE=$(gh api "repos/$repo_url/issues/$pr_number/comments" \\
    --method POST \\
    --input "$COMMENT_FILE" \\
    --field body=@- 2>&1) || {
    echo "❌ COMMENT ERROR: Failed to post comment to PR #$pr_number"
    echo "Error: $COMMENT_RESPONSE"
    rm -f "$COMMENT_FILE"
    exit 1
}

# Clean up temporary file
rm -f "$COMMENT_FILE"

echo "✅ SUCCESS: Comment posted successfully to PR #$pr_number"
echo "Comment ID: $(echo "$COMMENT_RESPONSE" | jq -r '.id' 2>/dev/null || echo 'Unknown')"
echo "Comment URL: $(echo "$COMMENT_RESPONSE" | jq -r '.html_url' 2>/dev/null || echo 'Unknown')"

echo "=== GitHub PR Comment Tool Completed Successfully ==="
""",
                ),
                args={
                    "repo": "${WORKFLOW_DETAILS.repository_full_name}",
                    "number": "${WORKFLOW_DETAILS.pr_number}",
                },
                env={
                    "analysis_report": "${ANALYSIS_REPORT}",
                    "failed_logs": "${FAILED_LOGS}",
                    "workflow_run_view": "${WORKFLOW_RUN_VIEW}",
                },
                secrets={"GH_TOKEN": f"${step_1.output}"},
            ),
        ),
    )

    step_6 = ExecutorStep(
        name="send-ms-teams-message",
        description="Send message to MS Teams",
        depends=[step_5.name],
        executor=Executor(
            type=ExecutorType.TOOL,
            config=ToolExecutorConfig(
                tool_def=ToolDef(
                    name="send-ms-teams",
                    type="docker",
                    image="python:3.12-slim",
                    content=f"""set -e
pip install -qqq -r /opt/scripts/reqs.txt
export PAYLOAD=$(python /opt/scripts/prepare_summary.py $pr_title $pr_url $author $workflow_url ${step_5.output} --triggered-at "$triggered_at")
python /opt/scripts/send_message.py $pipeline_name $PAYLOAD
""",
                    with_files=[
                        FileDefinition(
                            destination="/opt/scripts/reqs.txt", content="httpx==0.28.1"
                        ),
                        FileDefinition(
                            destination="/opt/scripts/webhook_config.py",
                            content=inspect.getsource(webhook_config),
                        ),
                        FileDefinition(
                            destination="/opt/scripts/send_message.py",
                            content=inspect.getsource(send_message),
                        ),
                        FileDefinition(
                            destination="/opt/scripts/prepare_summary.py",
                            content=inspect.getsource(prepare_summary),
                        ),
                    ],
                ),
            ),
        ),
    )

    workflow = Workflow(
        name="prototype-workflow",
        description="Prototype workflow to demonstrate alternative implementation",
        steps=[
            step_0,
            step_1,
            step_2,
            step_3_2,
        ],
        env=EnvironmentVariables(
            [
                EnvironmentVariable(name="KUBIYA_HOST", value=kubiya_host),
                EnvironmentVariable(name="KUBIYA_API_KEY", value=kubiya_api_key),
            ]
        ),
        params=WorkflowParams(
            [
                param_pipeline_name,
                param_pr_title,
                param_pr_url,
                param_repo_url,
                param_pr_number,
                param_author,
                param_workflow_url,
                param_workflow_run_id,
                param_triggered_at,
            ]
        ),
    )

    return workflow
