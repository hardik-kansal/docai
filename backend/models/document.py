from pydantic import BaseModel, Field


class PresignedURLRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(default="application/pdf")
    file_size_bytes: int = Field(..., gt=0)


class PresignedURLResponse(BaseModel):
    upload_url: str
    object_key: str
    expires_in: int
