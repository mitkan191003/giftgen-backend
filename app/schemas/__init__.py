from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import ShareType, Visibility


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserRead(APIModel):
    id: str
    email: str
    display_name: str | None = None


class ThreadCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class ChatMessageRead(APIModel):
    id: str
    role: str
    content: str
    metadata_json: dict[str, object]
    created_at: datetime


class ThreadRead(APIModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime


class ThreadDetail(ThreadRead):
    messages: list[ChatMessageRead]


class MessageExchangeRead(BaseModel):
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead
    suggested_prompt: str


class CreationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=2000)
    source_thread_id: str | None = None
    visibility: Visibility = Visibility.private


class AssetRead(APIModel):
    id: str
    asset_type: str
    storage_bucket: str
    storage_key: str
    mime_type: str
    file_size: int
    download_url: str | None = None
    created_at: datetime


class GenerationJobRead(APIModel):
    id: str
    provider: str
    provider_job_id: str | None
    model_name: str
    input_payload: dict[str, object]
    status: str
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class CreationRead(APIModel):
    id: str
    title: str
    final_prompt: str
    status: str
    visibility: str
    created_at: datetime
    updated_at: datetime
    last_accessed_at: datetime | None
    assets: list[AssetRead] = []


class CreationEnvelope(BaseModel):
    creation: CreationRead
    job: GenerationJobRead


class ShareCreate(BaseModel):
    creation_id: str
    share_type: ShareType = ShareType.unlisted


class ShareRead(APIModel):
    id: str
    creation_id: str
    share_type: str
    share_slug: str
    is_active: bool
    created_at: datetime
    revoked_at: datetime | None
    public_url: str


class PublicShareRead(BaseModel):
    title: str
    prompt: str
    visibility: str
    share_type: str
    owner_display_name: str | None
    assets: list[AssetRead]
