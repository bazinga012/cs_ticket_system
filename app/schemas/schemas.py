from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional, List
from enum import Enum
from fastapi import Form, UploadFile


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"
    REOPENED = "REOPENED"


class MessageType(str, Enum):
    CUSTOMER = "CUSTOMER"
    CS_REP = "CS_REP"
    SYSTEM = "SYSTEM"


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str
    is_cs_rep: bool = False


class User(UserBase):
    id: int
    is_cs_rep: bool

    model_config = ConfigDict(from_attributes=True)


class AttachmentBase(BaseModel):
    filename: str
    content_type: str


class AttachmentCreate(AttachmentBase):
    pass


class Attachment(AttachmentBase):
    id: int
    file_path: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageBase(BaseModel):
    content: str


class MessageCreate(MessageBase):
    attachments: List[UploadFile] = []

    @classmethod
    def as_form(
            cls,
            content: str = Form(...),
            attachments: List[UploadFile] = []
    ):
        return cls(content=content, attachments=attachments)


class Message(MessageBase):
    id: int
    message_type: MessageType
    created_at: datetime
    user_id: int
    attachments: List[Attachment] = []

    model_config = ConfigDict(from_attributes=True)


class TicketBase(BaseModel):
    title: str
    description: str


class TicketCreate(TicketBase):
    attachments: List[UploadFile] = []

    @classmethod
    def as_form(
            cls,
            title: str = Form(...),
            description: str = Form(...),
            attachments: List[UploadFile] = []
    ):
        return cls(title=title, description=description, attachments=attachments)


class Ticket(TicketBase):
    id: int
    status: TicketStatus
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    user_id: int
    messages: List[Message] = []

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
