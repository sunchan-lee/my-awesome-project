from fastapi import APIRouter, UploadFile, File, HTTPException, Query
import boto3
import uuid
import os

router = APIRouter(prefix="/uploads", tags=["uploads"])
# api_router = APIRouter()
# api_router.include_router(upload.router, prefix="/upload", tags=["upload"])  # 추가

# env파일에 있는 키 값 정보값 호출
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-2")

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

import traceback

# 파일 업로드
@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        print(f"📦 file.filename = {file.filename}")
        print(f"📄 type(file.file) = {type(file.file)}")
        print(f"🧪 content_type = {file.content_type}")
        print(f"🪣 AWS_S3_BUCKET_NAME = {AWS_S3_BUCKET_NAME} ({type(AWS_S3_BUCKET_NAME)})")


        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename found.")

        file_ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
        s3_key = f"uploads/{uuid.uuid4()}.{file_ext}"

        content_type = file.content_type
        if not isinstance(content_type, str) or not content_type:
            content_type = "application/octet-stream"

        s3_client.upload_fileobj(
            file.file,
            AWS_S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={
                #"ACL": "public-read",
                "ContentType": content_type
            }
        )

        file_url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        return {"filename": file.filename, "url": file_url}

    except Exception as e:
        print("❌ Upload failed:")
        traceback.print_exc()  # ⬅ 전체 스택 출력
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# 파일 목록
@router.get("/upload/list")
def list_files():
    try:
        response = s3_client.list_objects_v2(Bucket=AWS_S3_BUCKET_NAME, Prefix="uploads/")
        objects = response.get("Contents", [])
        file_keys = [obj["Key"] for obj in objects]
        return {"files": file_keys}
    except Exception as e:
        print("❌ List failed:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"List failed: {str(e)}")

# 파일 삭제
@router.delete("/upload/delete")
def delete_file(key: str = Query(..., description="S3 key of the file to delete")):
    try:
        response = s3_client.delete_object(
            Bucket=AWS_S3_BUCKET_NAME,
            Key=key
        )
        print("🧹 Delete response:", response)  # ✅ response 출력
        return {
            "message": f"Deleted {key}",
            "s3_response": response  # 클라이언트에 반환도 가능
        }
    except Exception as e:
        print("❌ Delete failed:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


