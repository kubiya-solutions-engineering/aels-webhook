from kubiya_workflow_sdk.dsl_experimental import *  # noqa
import inspect

from kubiya_workflow_sdk.dsl_experimental import WorkflowParams, WorkflowSecrets, Secret, Volume

from tools.teams import send_message, webhook_config, prepare_summary
from tools.gh import get_diff, post_pr_comment


def build_workflow(
    workflow_run_id: int,
    workflow_name: str,
    workflow_url: str,
    pr_title: str,
    pr_url: str,
    pr_number: int,
    repo_url: str,
    author: str,
    triggered_at: str,
    GH_TOKEN: str,
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

    shared_volume = Volume(name="shared_volume", path="/shared")

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

    step_2 = ExecutorStep(
        name="get-slack-integration",
        description="Get Slack integration info from Kubiya",
        output="SLACK_TOKEN",
        depends=[step_0.name],
        executor=Executor(
            type=ExecutorType.KUBIYA,
            config=KubiyaExecutorConfig(
                url="api/v2/integrations/slack",
                method=HTTPMethod.GET,
            ),
        ),
    )

    # TODO: Replace with implementation
    step_3_1 = ExecutorStep(
        name="get-gh-failed-logs",
        description="Get failed Workflow Run logs from GitHub",
        output="GH_FAILED_LOGS",
        depends=[step_0.name],
        executor=Executor(
            type=ExecutorType.TOOL,
            config=ToolExecutorConfig(
                secrets={"GH_TOKEN": f"$GH_TOKEN"},
                args={
                    "file_path": "/shared/failed_logs.txt",
                },
                tool_def=ToolDef(
                    name="get-gh-failed-logs",
                    type="docker",
                    image="python:3.12-slim",
                    secrets=["GH_TOKEN"],
                    content=f"""echo 'Failed Logs: ...'""",
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
                    with_volumes=[
                        shared_volume,
                    ],
                ),
            ),
        ),
    )

    step_3_2 = ExecutorStep(
        name="get-gh-pr-diff",
        description="Get GitHub PR diff",
        output="GH_PR_DIFF",
        depends=[step_0.name],
        executor=Executor(
            type=ExecutorType.TOOL,
            config=ToolExecutorConfig(
                secrets={"GH_TOKEN": f"$GH_TOKEN"},
                args={
                    "repo": f"${param_repo_url.name}",
                    "number": f"${param_pr_number.name}",
                    "file_path": "/shared/pr_diff.txt",
                },
                tool_def=ToolDef(
                    name="github_pr_diff",
                    description="Shows github PR Diff",
                    type="docker",
                    image="python:3.12-slim",
                    secrets=["GH_TOKEN"],
                    content=f"""set -e
pip install -qqq -r /opt/scripts/reqs.txt
python /opt/scripts/get_diff.py $repo $number $file_path""",
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
                    with_volumes=[
                        shared_volume,
                    ],
                ),
            ),
        ),
    )

    step_4 = ExecutorStep(
        name="failure-analysis",
        description="Analyze the collected data and generate comprehensive failure report",
        depends=[
            step_3_1.name,
            step_3_2.name,
        ],
        output="ANALYSIS_REPORT",
        executor=Executor(
            type=ExecutorType.AGENT,
            config=AgentExecutorConfig(
                agent_name="demo-teammate",
                message=f"""Analyze the CI/CD pipeline failure using the collected data:

PR Failed logs: ${step_3_1.output}
PR Diff: ${step_3_2.output}

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

    step_4_1 = ExecutorStep(
        name="save-pr-summary",
        description="Shows github PR Diff",
        depends=[step_4.name],
        executor=Executor(
            type=ExecutorType.TOOL,
            config=ToolExecutorConfig(
                args={
                    "path": "/shared/analysis.txt",
                },
                tool_def=ToolDef(
                    name="save-pr-summary",
                    description="Shows github PR Diff",
                    type="docker",
                    image="python:3.12-slim",
                    content=f"""python -c 'import os; with open(os.getenv("path"), "w") as f: f.write({step_4.output})'""",
                    with_volumes=[
                        shared_volume,
                    ],
                ),
            ),
        ),
    )

    step_5 = ExecutorStep(
        name="post-pr-summary",
        depends=[step_4_1.name],
        output="PR_MESSAGE_URL",
        description="Post failure analysis comment on the GitHub PR",
        executor=Executor(
            type=ExecutorType.TOOL,
            config=ToolExecutorConfig(
                tool_def=ToolDef(
                    name="github_pr_comment_workflow_failure",
                    description="Post failure analysis comment on the GitHub PR",
                    type="docker",
                    image="python:3.12-slim",
                    secrets=["GH_TOKEN"],
                    content=f"""pip install -qqq -r /opt/scripts/requirements.txt
python /opt/scripts/post_pr_comment.py --repo "$repo" --number "$number" --workflow-run-id "$workflow_run_id" --analysis-path $analysis --failed-logs-path $failed_logs
echo $PR_COMMENT
""",
                    with_files=[
                        FileDefinition(
                            destination="/opt/scripts/requirements.txt",
                            content="requests==2.32.3",
                        ),
                        FileDefinition(
                            destination="/opt/scripts/post_pr_comment.py",
                            content=inspect.getsource(post_pr_comment),
                        ),
                    ],
                    with_volumes=[
                        shared_volume,
                    ],
                ),
                args={
                    "repo": f"${param_repo_url.name}",
                    "number": f"${param_pr_number.name}",
                    "workflow_run_id": f"${param_workflow_run_id.name}",
                    "analysis": "/shared/analysis.txt",
                    "failed_logs": "/shared/failed_logs.txt",
                },
                secrets={"GH_TOKEN": "$GH_TOKEN"},
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
python /opt/scripts/send_message.py $pipeline_name $(python /opt/scripts/prepare_summary.py $pr_title $pr_url $author $workflow_url ${step_5.output} --triggered-at "$triggered_at")
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
            step_2,
            step_3_1,
            step_3_2,
            step_4,
            step_4_1,
            step_5,
        ],
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
        secrets=WorkflowSecrets(
            [
                Secret(name="GH_TOKEN", value=GH_TOKEN),
            ]
        ),
    )

    return workflow
