from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
import aiofiles
import os
from datetime import datetime

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.models import Ticket, Message, User, TicketStatus, MessageType, Attachment
from ..schemas.schemas import (
    TicketCreate, Ticket as TicketSchema,
    MessageCreate, Message as MessageSchema
)
from ..core.config import settings

router = APIRouter()


async def save_attachment(file: UploadFile) -> str:
    """Helper function to save an attachment and return its path"""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, f"{datetime.now().timestamp()}_{file.filename}")
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    return file_path


async def delete_attachment(file_path: str):
    """Helper function to delete an attachment file"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error deleting file {file_path}: {str(e)}")

    # Ticket endpoints


@router.post("/tickets/", response_model=TicketSchema)
async def create_ticket(
        title: str = Form(...),
        description: str = Form(...),
        attachments: List[UploadFile] = [],
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Create a new ticket with initial message and optional attachments."""

    # Create the ticket 
    status_value = TicketStatus.OPEN.value
    print(f"Status type: {type(status_value)}, value: {status_value}, string value: {str(status_value)}")

    db_ticket = Ticket(
        title=title,
        description=description,
        user_id=current_user.id
    )
    db.add(db_ticket)
    await db.flush()  # Get the ticket ID without committing 

    # Create the initial message 
    initial_message = Message(
        content=description,
        message_type=MessageType.CUSTOMER,
        ticket_id=db_ticket.id,
        user_id=current_user.id
    )
    db.add(initial_message)
    await db.flush()

    # Handle attachments 
    for file in attachments:
        file_path = await save_attachment(file)
        attachment = Attachment(
            filename=file.filename,
            file_path=file_path,
            content_type=file.content_type,
            message_id=initial_message.id
        )
        db.add(attachment)

    await db.commit()
    await db.refresh(db_ticket)

    # Fetch the complete ticket with relationships 
    query = (
        select(Ticket)
        .options(
            selectinload(Ticket.messages).selectinload(Message.attachments)
        )
        .filter(Ticket.id == db_ticket.id)
    )
    result = await db.execute(query)
    return result.scalar_one()


@router.get("/tickets/", response_model=List[TicketSchema])
async def get_tickets(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
        status: Optional[TicketStatus] = None
):
    """Get all tickets with optional status filter"""
    query = (
        select(Ticket)
        .options(
            selectinload(Ticket.messages).selectinload(Message.attachments)
        )
    )
    if not current_user.is_cs_rep:
        query = query.filter(Ticket.user_id == current_user.id)
    if status:
        query = query.filter(Ticket.status == status)

    result = await db.execute(query)
    return result.scalars().unique().all()


@router.get("/tickets/{ticket_id}", response_model=TicketSchema)
async def get_ticket(
        ticket_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    query = (
        select(Ticket)
        .options(
            selectinload(Ticket.messages).selectinload(Message.attachments)
        )
        .filter(Ticket.id == ticket_id)
    )
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if not current_user or (not current_user.is_cs_rep and ticket.user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this ticket")

    return ticket


@router.post("/tickets/{ticket_id}/messages/", response_model=MessageSchema)
async def create_message(
        ticket_id: int,
        content: str = Form(...),
        attachments: List[UploadFile] = [],
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Add a new message to a ticket with optional attachments."""

    # Verify ticket exists and user has access 
    query = select(Ticket).filter(Ticket.id == ticket_id)
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if not current_user.is_cs_rep and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to respond to this ticket")

    if ticket.status == TicketStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Cannot add messages to a closed ticket")

        # Create the message
    message = Message(
        content=content,
        message_type=MessageType.CS_REP if current_user.is_cs_rep else MessageType.CUSTOMER,
        ticket_id=ticket_id,
        user_id=current_user.id
    )
    db.add(message)
    await db.flush()

    # Handle attachments 
    for file in attachments:
        file_path = await save_attachment(file)
        attachment = Attachment(
            filename=file.filename,
            file_path=file_path,
            content_type=file.content_type,
            message_id=message.id
        )
        db.add(attachment)

        # Update ticket status if CS rep responds
    if current_user.is_cs_rep and ticket.status == TicketStatus.OPEN:
        ticket.status = TicketStatus.IN_PROGRESS

    await db.commit()
    await db.refresh(message)

    # Fetch the complete message with attachments 
    query = (
        select(Message)
        .options(selectinload(Message.attachments))
        .filter(Message.id == message.id)
    )
    result = await db.execute(query)
    return result.scalar_one()


@router.delete("/messages/{message_id}/attachments/{attachment_id}")
async def delete_message_attachment(
        message_id: int,
        attachment_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete an attachment from a message"""
    # First, get the message and verify ownership 
    query = (
        select(Message)
        .options(selectinload(Message.attachments))
        .filter(Message.id == message_id)
    )
    result = await db.execute(query)
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if not current_user.is_cs_rep and message.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this attachment")

        # Find the attachment
    attachment = next((a for a in message.attachments if a.id == attachment_id), None)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

        # Delete the file
    await delete_attachment(attachment.file_path)

    # Remove from database using SQLAlchemy delete
    stmt = delete(Attachment).where(Attachment.id == attachment_id)
    await db.execute(stmt)
    await db.commit()

    return {"message": "Attachment deleted successfully"}


@router.patch("/tickets/{ticket_id}/close")
async def close_ticket(
        ticket_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if not current_user.is_cs_rep:
        raise HTTPException(status_code=403, detail="Only CS representatives can close tickets")

    query = select(Ticket).filter(Ticket.id == ticket_id)
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.status = TicketStatus.CLOSED
    ticket.closed_at = datetime.utcnow()

    # Add system message for ticket closure 
    system_message = Message(
        content="Ticket closed by CS representative",
        message_type=MessageType.SYSTEM,
        ticket_id=ticket_id,
        user_id=current_user.id
    )
    db.add(system_message)

    await db.commit()
    return {"message": "Ticket closed successfully"}


@router.patch("/tickets/{ticket_id}/reopen")
async def reopen_ticket(
        ticket_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    query = select(Ticket).filter(Ticket.id == ticket_id)
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the ticket creator can reopen the ticket")

    if not ticket.can_reopen():
        raise HTTPException(
            status_code=400,
            detail="Ticket cannot be reopened. Either it's not closed or it's been more than 7 days since closure."
        )

    ticket.status = TicketStatus.REOPENED

    # Add system message for ticket reopening 
    system_message = Message(
        content="Ticket reopened by customer",
        message_type=MessageType.SYSTEM,
        ticket_id=ticket_id,
        user_id=current_user.id
    )
    db.add(system_message)

    await db.commit()
    return {"message": "Ticket reopened successfully"}


@router.get("/tickets/{ticket_id}/messages", response_model=List[MessageSchema])
async def get_ticket_messages(
        ticket_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get all messages for a ticket"""
    # First verify ticket access 
    ticket_query = select(Ticket).filter(Ticket.id == ticket_id)
    result = await db.execute(ticket_query)
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if not current_user.is_cs_rep and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this ticket")

        # Get messages with attachments
    query = (
        select(Message)
        .options(selectinload(Message.attachments))
        .filter(Message.ticket_id == ticket_id)
        .order_by(Message.created_at)
    )
    result = await db.execute(query)
    return result.scalars().all()
