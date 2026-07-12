from pydantic import BaseModel, Field
from dataclasses import dataclass
import datetime
import uuid


class PresignedURLRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(default="application/pdf")
    file_size_bytes: int = Field(..., gt=0)


class PresignedURLResponse(BaseModel):
    upload_url: str  # actual MinIO POST endpoint URL
    upload_fields: dict[str, str]  # auth fields to include in multipart form
    object_key: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class DocumentRow:
    id: uuid.UUID
    filename: str
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    s3_key: str
    error: str | None


class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    s3_key: str
    error: str | None = None
