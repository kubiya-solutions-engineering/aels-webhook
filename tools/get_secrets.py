import os
from urllib.parse import urljoin

import httpx


def get_github_vendor_id(kubiya_api_key: str, kubiya_host: str, integration_name: str) -> str:
    path = f'api/v2/integrations/{integration_name}'
    url = urljoin(kubiya_host, path)
    resp = httpx.get(url, headers={'Authorization': f'UserKey {kubiya_api_key}'})
    vendor_id = resp.json()['configs'][0]['vendor_specific']['id']
    return vendor_id


def get_github_token(kubiya_api_key: str, kubiya_host: str, integration_name: str, vendor_id: str) -> str:
    path = f'api/v1/integration/{integration_name}/token/{vendor_id}'
    url = urljoin(kubiya_host, path)
    resp = httpx.get(url, headers={'Authorization': f'UserKey {kubiya_api_key}'})
    token = resp.json()['token']
    return token


if __name__ == '__main__':
    kubiya_host = os.environ.get('KUBIYA_HOST')
    kubiya_api_key = os.environ.get('KUBIYA_API_KEY')
    integration_name = os.environ.get('INTEGRATION_NAME')

    vendor_id = get_github_vendor_id(
        kubiya_host=kubiya_host,
        kubiya_api_key=kubiya_api_key,
        integration_name=integration_name,
    )
    token = get_github_token(
        kubiya_host=kubiya_host,
        kubiya_api_key=kubiya_api_key,
        integration_name=integration_name,
        vendor_id=vendor_id,
    )

    print(token)
