from datetime import datetime, timedelta

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum as SQLEnum, Text, Boolean
from sqlalchemy.orm import relationship

from ..core.database import Base
from ..schemas.schemas import TicketStatus, MessageType


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_cs_rep = Column(Boolean, default=False)
    messages = relationship("Message", back_populates="user")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(Text)
    status = Column(SQLEnum(TicketStatus), default=TicketStatus.OPEN)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True, default=None)
    user_id = Column(Integer, ForeignKey("users.id"))
    category = Column(String, nullable=True)

    user = relationship("User")
    messages = relationship("Message", back_populates="ticket", order_by="Message.created_at")

    def can_reopen(self) -> bool:
        if self.status != TicketStatus.CLOSED or not self.closed_at:
            return False
        return (datetime.utcnow() - self.closed_at) <= timedelta(days=7)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    message_type = Column(SQLEnum(MessageType))
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    user_id = Column(Integer, ForeignKey("users.id"))

    ticket = relationship("Ticket", back_populates="messages")
    user = relationship("User", back_populates="messages")
    attachments = relationship("Attachment", back_populates="message")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    file_path = Column(String)
    content_type = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    message_id = Column(Integer, ForeignKey("messages.id"))
    message = relationship("Message", back_populates="attachments")
