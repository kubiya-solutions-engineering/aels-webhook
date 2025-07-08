from pydantic_settings import BaseSettings, SettingsConfigDict
from kubiya_workflow_sdk import execute_workflow, validate_workflow_definition

from workflow import build_workflow


class WorkflowRunnerSettings(BaseSettings):
    runner: str = "demo"

    KUBIYA_HOST: str = ""
    KUBIYA_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


def parse_webhook_payload(raw_payload: dict) -> dict:
    payload = {
        "workflow_run_id": raw_payload["workflow_run"]["id"],
        "workflow_name": raw_payload["workflow_run"]["name"],
        "workflow_url": raw_payload["workflow_run"]["url"],
        "pr_title": raw_payload["workflow_run"]["display_title"],
        "pr_url": raw_payload["workflow_run"]["pull_requests"][0]["url"],
        "pr_number": raw_payload["workflow_run"]["pull_requests"][0]["number"],
        "repo_url": raw_payload["repository"]["full_name"],
        "author": raw_payload["workflow_run"]["triggering_actor"]["login"],
        "triggered_at": raw_payload["workflow_run"]["updated_at"],
    }
    return payload


if __name__ == "__main__":
    from gh_payload import raw_payload

    config = WorkflowRunnerSettings()
    payload = parse_webhook_payload(raw_payload=raw_payload)

    workflow = build_workflow(
        kubiya_host=config.KUBIYA_HOST,
        kubiya_api_key=config.KUBIYA_API_KEY,
        **payload,
    )
    workflow_definition = workflow.model_dump(exclude_none=True, exclude_defaults=True)

    validate_workflow_definition(workflow_definition)

    for line in execute_workflow(
        workflow_definition=workflow_definition,
        api_key=config.KUBIYA_API_KEY,
        runner=config.runner,
    ):
        print(line)
