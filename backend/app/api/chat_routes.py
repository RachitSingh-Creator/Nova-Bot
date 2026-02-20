import asyncio
import json
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm_client import LLMClient
from app.core.config import get_settings
from app.db.session import AsyncSessionLocal, get_db
from app.models.chat import Conversation, Message
from app.models.usage import UsageLog
from app.models.user import User
from app.schemas.chat import ChatHistoryResponse, ChatSendRequest, ChatSendResponse, ConversationCreate, ConversationOut, ConversationUpdate
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])
llm_client = LLMClient()
rate_bucket: dict[int, deque[float]] = defaultdict(deque)
rate_lock = asyncio.Lock()
settings = get_settings()


async def check_rate_limit(user_id: int) -> None:
    now = time.time()
    async with rate_lock:
        q = rate_bucket[user_id]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= settings.rate_limit_per_minute:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
        q.append(now)


async def get_conversation_or_404(db: AsyncSession, conversation_id: int, user_id: int) -> Conversation:
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id))
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


async def build_context_messages(db: AsyncSession, conversation: Conversation, user_text: str, max_history: int = 12) -> list[dict[str, str]]:
    result = await db.execute(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at.desc()).limit(max_history))
    history = list(reversed(result.scalars().all()))
    messages = [{"role": "system", "content": conversation.system_prompt}]
    messages.extend({"role": m.role, "content": m.content} for m in history)
    messages.append({"role": "user", "content": user_text})
    return messages


def format_llm_error(exc: Exception) -> str:
    message = str(exc).lower()
    status_code = getattr(exc, "status_code", None)
    if status_code is None:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)

    if "gemini_api_key is missing" in message:
        return "Server AI configuration is missing. Please contact support."
    if status_code == 429 or "too many requests" in message:
        return "AI provider rate limit reached. Please try again shortly."
    if "insufficient_quota" in message or "exceeded your current quota" in message:
        return "AI provider quota exceeded. Please check billing/credits."
    if status_code in {401, 403}:
        return "AI provider authentication failed. Please contact support."
    if status_code == 404:
        return "Selected AI model is unavailable. Please choose another model."
    if status_code and int(status_code) >= 500:
        return "AI provider is temporarily unavailable. Please try again."
    return "AI request failed. Please try again."


@router.post("/new", response_model=ConversationOut)
async def create_chat(payload: ConversationCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    conversation = Conversation(user_id=user.id, title=payload.title, model=payload.model, system_prompt=payload.system_prompt)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.get("/list", response_model=list[ConversationOut])
async def list_chats(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc()))
    return list(result.scalars().all())


@router.patch("/{chat_id}", response_model=ConversationOut)
async def rename_chat(chat_id: int, payload: ConversationUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    conversation = await get_conversation_or_404(db, chat_id, user.id)
    conversation.title = payload.title
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.delete("/{chat_id}")
async def delete_chat(chat_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    conversation = await get_conversation_or_404(db, chat_id, user.id)
    await db.delete(conversation)
    await db.commit()
    return {"ok": True}


@router.get("/history/{chat_id}", response_model=ChatHistoryResponse)
async def chat_history(chat_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    conversation = await get_conversation_or_404(db, chat_id, user.id)
    result = await db.execute(select(Message).where(Message.conversation_id == chat_id).order_by(Message.created_at.asc()))
    return ChatHistoryResponse(conversation=conversation, messages=list(result.scalars().all()))


@router.post("/send", response_model=ChatSendResponse)
async def send_message(payload: ChatSendRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await check_rate_limit(user.id)
    conversation = await get_conversation_or_404(db, payload.conversation_id, user.id)
    context_messages = await build_context_messages(db, conversation, payload.message)

    user_msg = Message(conversation_id=conversation.id, role="user", content=payload.message)
    db.add(user_msg)
    await db.flush()

    try:
        result = await llm_client.complete(
            context_messages,
            model=payload.model or conversation.model,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        )
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=502, detail=format_llm_error(exc)) from exc

    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=result["content"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        total_tokens=result["total_tokens"],
    )
    db.add(assistant_msg)

    usage = UsageLog(
        user_id=user.id,
        conversation_id=conversation.id,
        model=result["model"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        total_tokens=result["total_tokens"],
        estimated_cost_usd=llm_client.estimate_cost(result["model"], result["total_tokens"]),
    )
    db.add(usage)

    if payload.system_prompt:
        conversation.system_prompt = payload.system_prompt
    conversation.model = payload.model or conversation.model

    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(assistant_msg)
    return ChatSendResponse(user_message=user_msg, assistant_message=assistant_msg)


@router.post("/send/stream")
async def send_message_stream(payload: ChatSendRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await check_rate_limit(user.id)
    conversation = await get_conversation_or_404(db, payload.conversation_id, user.id)
    context_messages = await build_context_messages(db, conversation, payload.message)

    user_msg = Message(conversation_id=conversation.id, role="user", content=payload.message)
    db.add(user_msg)
    await db.commit()

    async def event_gen():
        full_text = ""
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        chosen_model = payload.model or conversation.model

        try:
            async for chunk in llm_client.stream(context_messages, model=chosen_model, temperature=payload.temperature, max_tokens=payload.max_tokens):
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    delta = chunk.choices[0].delta.content
                    full_text += delta
                    yield f"data: {json.dumps({'type': 'token', 'value': delta})}\n\n"
                if chunk.usage:
                    prompt_tokens = int(chunk.usage.prompt_tokens or 0)
                    completion_tokens = int(chunk.usage.completion_tokens or 0)
                    total_tokens = int(chunk.usage.total_tokens or 0)

            async with AsyncSessionLocal() as write_db:
                live_conversation = await get_conversation_or_404(write_db, payload.conversation_id, user.id)
                assistant_msg = Message(
                    conversation_id=live_conversation.id,
                    role="assistant",
                    content=full_text,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                )
                write_db.add(assistant_msg)

                usage = UsageLog(
                    user_id=user.id,
                    conversation_id=live_conversation.id,
                    model=chosen_model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    estimated_cost_usd=llm_client.estimate_cost(chosen_model, total_tokens),
                )
                write_db.add(usage)

                if payload.system_prompt:
                    live_conversation.system_prompt = payload.system_prompt
                live_conversation.model = chosen_model

                await write_db.commit()
            yield "data: {\"type\":\"done\"}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'value': format_llm_error(exc)})}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
