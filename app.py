from pydantic_settings import BaseSettings, SettingsConfigDict
from kubiya_workflow_sdk import execute_workflow, validate_workflow_definition

from workflow import build_workflow


class WorkflowRunnerSettings(BaseSettings):
    runner: str = 'demo'

    KUBIYA_HOST: str = ''
    KUBIYA_API_KEY: str = ''

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')


if __name__ == '__main__':
    config = WorkflowRunnerSettings()

    payload = {
        'pipeline_name': '',
        'pr_title': '',
        'pr_url': '',
        'repo_url': '',
        'pr_number': '',
        'workflow_run_id': '',
        'author': '',
        'workflow_url': '',
        'triggered_at': '',
    }

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
