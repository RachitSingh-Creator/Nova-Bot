# Nova Bot

Full stack AI chatbot with FastAPI, React, PostgreSQL, JWT auth, OpenAI streaming, usage tracking, and Docker deployment.

## Stack

- Backend: Python, FastAPI, SQLAlchemy, Alembic, Uvicorn
- AI: OpenAI Chat Completions API with streaming (SSE)
- Database: PostgreSQL (prod), SQLite (fallback)
- Frontend: React + Vite + Tailwind
- Infra: Docker, Docker Compose, Nginx

## Project Structure

```text
backend/
  main_voice.py
  app/
    main.py
    api/
      auth_routes.py
      chat_routes.py
      user_routes.py
    core/
      config.py
      security.py
      llm_client.py
    models/
    schemas/
    services/
    db/
      session.py
      base.py
  alembic/
  nova/
    voice/
      speech_to_text.py
      text_to_speech.py
      command_handler.py
      assistant_controller.py
  requirements.txt
  Dockerfile
frontend/
  src/
    components/
      ChatWindow.jsx
      Sidebar.jsx
      MessageBubble.jsx
      Navbar.jsx
    pages/
      Login.jsx
      Signup.jsx
      Chat.jsx
    services/api.js
    hooks/
    App.jsx
docker-compose.yml
nginx/default.conf
```

## Features

- JWT auth: signup/login/refresh
- Protected user and chat routes
- Multi-chat: create, rename, delete, list
- Conversation memory using last N messages
- Streaming tokens from OpenAI to UI
- Markdown + code block rendering
- Copy response, regenerate response, stop generation
- Model selector, system prompt, temperature/max tokens
- Usage tracking: token totals + estimated cost
- Rate limiting (in-memory per user)
- Dark/light mode + responsive layout
- Voice assistant mode (wake word + Deepgram STT + TTS)

## API Endpoints

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/users/me`
- `GET /api/users/usage/summary`
- `POST /api/chat/new`
- `GET /api/chat/list`
- `PATCH /api/chat/{chat_id}`
- `DELETE /api/chat/{chat_id}`
- `GET /api/chat/history/{chat_id}`
- `POST /api/chat/send`
- `POST /api/chat/send/stream`

Swagger docs: `http://localhost:8000/docs`

## Environment Variables

### Backend (`backend/.env`)

Copy from `backend/.env.example`:

```env
SECRET_KEY=replace-with-a-secure-random-key
DATABASE_URL=postgresql+asyncpg://nova:nova@db:5432/nova_bot
OPENAI_API_KEY=sk-your-key
GEMINI_API_KEY=your-gemini-key
DEEPGRAM_API_KEY=your-deepgram-key
OPENAI_MODEL=gpt-4o-mini
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=700
CORS_ORIGINS=http://localhost:5173,http://localhost
RATE_LIMIT_PER_MINUTE=60
VOICE_BACKEND_URL=http://localhost
VOICE_USER_EMAIL=your-login-email@example.com
VOICE_USER_PASSWORD=your-login-password
VOICE_WAKE_WORD=hey nova
VOICE_DEFAULT_MODEL=gemini-2.5-flash
VOICE_TTS_VOICE=alloy
VOICE_TTS_SPEED=1.0
```

### Frontend (`frontend/.env`)

Copy from `frontend/.env.example`:

```env
VITE_API_URL=http://localhost/api
```

## Local Dev (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

App: `http://localhost:5173`

## Voice Assistant (Deepgram)

Run this after backend API is up:

```bash
cd backend
python main_voice.py
```

Example commands:

- `hey nova open youtube`
- `hey nova open google`
- `hey nova open notepad`
- `hey nova what time is it`
- `hey nova switch to gemini`
- `hey nova switch to openai`
- `hey nova exit`

## Docker Deploy

1. Copy env files:

```bash
copy backend\.env.example backend\.env
copy frontend\.env.example frontend\.env
```

2. Set `OPENAI_API_KEY` in `backend/.env`.
3. Build and run:

```bash
docker compose up --build
```

4. Access:
- App (via Nginx): `http://localhost`
- Backend docs: `http://localhost:8000/docs`

## Notes

- This project stores costs as rough estimates in `usage_logs`.
- Rate limiting is in-memory; use Redis for distributed environments.
- For file upload, voice input, TTS, and RAG, extend routes/services in a separate module.
- `asyncio` is built into Python, so no separate package install is required.
