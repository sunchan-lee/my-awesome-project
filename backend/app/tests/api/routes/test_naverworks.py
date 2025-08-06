from fastapi import HTTPException
import time
import jwt
import os
import requests

from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

# 하드코딩된 값
CLIENT_ID = "cNDdvU4okR4RbxOSkNLp"
CLIENT_SECRET="hXbSjieJ2B"
SERVICE_ACCOUNT = "s733p.serviceaccount@suntest.shop"
PRIVATE_KEY_PATH = "/Users/sunchanlee/Documents/code2/my-awesome-project/private_20250731175819.key"

with open(PRIVATE_KEY_PATH, "rb") as f:
    private_key = f.read()

now = int(time.time())

payload = {
    "iss": CLIENT_ID,
    "sub": SERVICE_ACCOUNT,
    "iat": now,
    "exp": now + 3600
}

token = jwt.encode(payload, private_key, algorithm="RS256")

print("✅ Generated JWT:")
print(token)

def get_access_token():
    try : 
        client_id = CLIENT_ID
        client_secret = CLIENT_SECRET
        service_account = SERVICE_ACCOUNT
        private_key = PRIVATE_KEY_PATH

        with open(PRIVATE_KEY_PATH, "rb") as f:
            private_key = f.read()

        now = int(time.time())
        payload = {
            "iss": client_id,
            "sub": service_account,
            "iat": now,
            "exp": now + 3600,
        }
        assertion = jwt.encode(payload, private_key, algorithm="RS256")

        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "client_id": client_id,
            "client_secret": client_secret,
            "assertion": assertion,
            "scope": "bot user.read board",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }

        token_url = "https://auth.worksmobile.com/oauth2/v2.0/token"

        response = requests.post(token_url, headers=headers, data=data)
        if response.status_code != 200:
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=response.text)

        return response.json()

    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Token request failed: {str(e)}")

def board_write():
    try:
        # 먼저 access 토큰을 확인한다 데이터가 없으면 없다고 표시한다.
        # 뒤의 .get("access_token")을 통해서 access_token만 항목만 따온다
        access_token = get_access_token().get("access_token")
        if not access_token:
            raise Exception("No access token received")

        # Request Body에 들어갈 항목들 추가
        data = {
            "title": "Example title1",
            "body": "<h1>Example</h1> Insert body here.",
            "enableComment": True,
            "mustReadEndDate": "2025-08-30",
            "sendNotifications": True
        }

        # Header에 들어갈 항목. accesstoken을 가져온다
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # post 요청을 날릴 url 주소
        post_url = "https://www.worksapis.com/v1.0/boards/4070000000157722234/posts"

        response = requests.post(post_url, headers=headers, json=data)  # ✅ use `json=`
        if response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Board post failed: {response.text}"
            )
        return response.json()

    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Token request failed: {str(e)}")


if __name__ == "__main__":
    result = get_access_token()
    result2 = board_write()
    print("✅ Access Token Response:")
    print(result)
    print("✅ Board Response:")
    print(result2)



