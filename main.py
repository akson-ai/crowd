import json
import uuid

from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.event import ServerSentEvent
from sse_starlette.sse import EventSourceResponse
from starlette.requests import ClientDisconnect

import registry
from framework import Assistant, Chat, ChatState
from loader import load_assistants
from logger import logger

load_dotenv()

assistants = load_assistants()
# TODO find a way to make default assistant configurable
default_assistant = "chatgpt"

for name, assistant in assistants.items():
    registry.register(name, assistant)


# Need to keep a single instance of each chat in memory in order to do pub/sub on queue
# TODO try streaming response
chats: dict[str, Chat] = {}


def _get_chat_state(chat_id: str) -> ChatState:
    try:
        return ChatState.load_from_disk(chat_id)
    except FileNotFoundError:
        return ChatState.create_new(chat_id, default_assistant)


def _get_chat(chat_id: str) -> Chat:
    try:
        return chats[chat_id]
    except KeyError:
        state = _get_chat_state(chat_id)
        chat = Chat(state)
        chats[chat_id] = chat
        return chat


app = FastAPI()


@app.get("/", include_in_schema=False)
async def index():
    """Redirect to the chat app."""
    return RedirectResponse(f"/chat?id={uuid.uuid4()}")


@app.get("/chat", include_in_schema=False)
async def get_chat_app():
    """Serve the chat web app."""
    return FileResponse("web/chat.html")


@app.get("/assistants")
async def get_assistants():
    """Return a list of available assistants."""
    return list({"name": name} for name in sorted(assistants.keys()))


@app.get("/{chat_id}/state")
async def get_chat_state(state: ChatState = Depends(_get_chat_state)):
    """Return the state of a chat session."""
    return state


def get_assistant(name: str = Body(alias="assistant")) -> Assistant:
    return assistants[name]


@app.post("/{chat_id}/message")
async def handle_message(
    request: Request,
    content: str = Body(...),
    assistant: Assistant = Depends(get_assistant),
    chat: Chat = Depends(_get_chat),
):
    """Handle a message from the client."""

    chat.state.messages.append({"role": "user", "content": content})

    chat._request = request
    try:
        if content.strip() == "/clear":
            chat.state.messages.clear()
            chat.state.save_to_disk()
            logger.info("Chat cleared")
            await chat._send_control("clear")
            return
        await assistant.run(chat)
    except ClientDisconnect:
        # TODO save interrupted messages
        logger.info("Client disconnected")
    finally:
        chat._request = None
        chat.state.save_to_disk()


@app.get("/{chat_id}/events")
async def stream_events(chat: Chat = Depends(_get_chat)):
    """Stream events to the client."""

    async def generate_events():
        while True:
            message = await chat._queue.get()
            yield ServerSentEvent(json.dumps(message))

    return EventSourceResponse(generate_events())


# Must be mounted after above handlers
app.mount("/", StaticFiles(directory="web/static"))
