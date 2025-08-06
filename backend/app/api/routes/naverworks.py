# app/api/routes/jwt_token.py

import time
import jwt
import os
import requests
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel
from app.core.config import settings
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

router = APIRouter(prefix="/naverworks", tags=["naverworks"])

# 각 클래스는 SWAGGER UI에서 보여지는 예시 값들 표시
class JWTResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"

class OAuthResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class BoardPostRequest(BaseModel):
    title: str
    body: str
    enableComment: bool = True
    mustReadEndDate: str = "2025-08-30"
    sendNotifications: bool = True

class BoardPatchRequest(BaseModel):
    title: str
    body: str
    enableComment: bool = True
    mustReadEndDate: str = "2025-08-30"
    sendNotifications: bool = True

# JWT 값 발급
@router.get("/generate-jwt", response_model=JWTResponse)
def generate_jwt():
    try:
        client_id = settings.NAVERWORKS_CLIENT_ID
        service_account = settings.NAVERWORKS_SERVICE_ACCOUNT
        private_key_path = settings.NAVERWORKS_PRIVATE_KEY

        print("✔ NAVERWORKS_CLIENT_ID =", client_id)
        print("✔ NAVERWORKS_SERVICE_ACCOUNT =", service_account)
        print("✔ NAVERWORKS_PRIVATE_KEY =", private_key_path)
        print("✔ os.path.exists(key_path) =", os.path.exists(private_key_path))

        if not all([client_id, service_account, private_key_path]):
            raise ValueError("Missing environment variables for JWT")

        with open(private_key_path, "rb") as f:
            private_key = f.read()

        now = int(time.time())
        payload = {
            "iss": client_id,
            "sub": service_account,
            "iat": now,
            "exp": now + 3600
        }

        token = jwt.encode(payload, private_key, algorithm="RS256")

        return JWTResponse(access_token=token)

    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"JWT generation failed: {str(e)}"
        )

# Access_Token 발급
@router.get("/get-access-token", response_model=OAuthResponse)
def get_access_token():
    try:
        client_id = settings.NAVERWORKS_CLIENT_ID
        client_secret = settings.NAVERWORKS_CLIENT_SECRET
        service_account = settings.NAVERWORKS_SERVICE_ACCOUNT
        key_path = settings.NAVERWORKS_PRIVATE_KEY

        if not all([client_id, client_secret, service_account, key_path]):
            raise HTTPException(status_code=400, detail="Missing NAVERWORKS env variables")

        with open(key_path, "rb") as f:
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

# 게시글 작성
@router.post("/board/post")
def board_write(request: BoardPostRequest):  # ✅ 반드시 여기에 있어야 함!
    try:
        token = get_access_token().get("access_token")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        post_url = "https://www.worksapis.com/v1.0/boards/4070000000157722234/posts"
        response = requests.post(post_url, headers=headers, json=request.model_dump())

        if response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Board post failed: {response.status_code} {response.text}"
            )

        return response.json()

    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Request failed: {str(e)}"
        )

# 게시글 목록 조회
@router.get("/board/posts")
def board_get():
    try:
        # 1) 발급받은 access_token 가져오기
        token = get_access_token().get("access_token")
        if not token:
            raise HTTPException(400, "No access token")

        # 2) 헤더 설정 (JSON body 불필요)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # 3) GET으로 게시물 리스트 조회
        board_id = "4070000000157722234"
        get_url = f"https://www.worksapis.com/v1.0/boards/{board_id}/posts"
        response = requests.get(get_url, headers=headers)

        # 4) 상태 코드 확인
        if response.status_code not in (200, 201):
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Fetch failed: {response.status_code} {response.text}"
            )

        # 5) JSON 응답 반환
        return response.json()

    except HTTPException:
        # FastAPI HTTPException은 그대로 다시 던지기
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Request failed: {str(e)}"
        )

# 게시글 수정
# SWAGGER UI에서 board_id, post_id를 입력하기 위한 세팅
# 게시글 목록 조회에서 나오는 밸류값 대신, 실제 네이버웍스 주소창에서 제공되는 주소값을 이용해야 한다.
@router.patch("/board/update/{board_id}/{post_id}")
def board_update(
    post_id: int = Path(..., description="게시물 ID (숫자)"),
    board_id: int = Path(..., description="게시판 ID (숫자)"),
    request: BoardPatchRequest = None,
):
    try:
        # 1) access_token 발급
        access_token = get_access_token().get("access_token")
        print(f"🔑 access_token: {access_token}")
        if not isinstance(access_token, str):
            raise HTTPException(HTTP_500_INTERNAL_SERVER_ERROR, "Invalid access token type")

        # 2) headers 설정
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        print(f"📤 headers: {headers}")

        # 3) PATCH URL 및 Query Params
        patch_url = f"https://www.worksapis.com/v1.0/boards/{board_id}/posts/{post_id}"
        print(f"patch_url: {patch_url}")

        # 4) PATCH 요청
        resp = requests.put(patch_url, headers=headers, json=request.model_dump())
        print(f"✏ PATCH status: {resp.status_code}, body: {resp.text}")

        # 6) 상태 코드 검사
        if resp.status_code not in (200, 201):
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Board update failed: {resp.status_code} {resp.text}",
            )

        return resp.json()

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Exception in board_update: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Request failed: {str(e)}",
        )
    
#게시글 삭제
# SWAGGER UI에서 board_id, post_id를 입력하기 위한 세팅
# 게시글 목록 조회에서 나오는 밸류값 대신, 실제 네이버웍스 주소창에서 제공되는 주소값을 이용해야 한다.
@router.delete("board/delete/{board_id}/{post_id}")
def board_delete(
    post_id: int = Path(..., description="게시물 ID (숫자)"),
    board_id: int = Path(..., description="게시판 ID (숫자)"),
):
    try:
        # 1) access_token 발급
        access_token = get_access_token().get("access_token")
        print(f"🔑 access_token: {access_token}")
        if not isinstance(access_token, str):
            raise HTTPException(HTTP_500_INTERNAL_SERVER_ERROR, "Invalid access token type")

        # 2) headers 설정
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        print(f"📤 headers: {headers}")   

        # 3) PATCH URL 및 Query Params
        delete_url = f"https://www.worksapis.com/v1.0/boards/{board_id}/posts/{post_id}"
        print(f"patch_url: {delete_url}")

        # 4) PATCH 요청
        resp = requests.delete(delete_url, headers=headers)
        print(f"✏ PATCH status: {resp.status_code}, body: {resp.text}")

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Exception in board_update: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Request failed: {str(e)}",
        )