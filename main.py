import os
from logging import getLogger
from typing import Annotated, Never

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request, status
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhook import WebhookParser
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# official sample code
# https://github.com/line/line-bot-sdk-python

load_dotenv()
logger = getLogger(__name__)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(LINE_CHANNEL_SECRET)

HEADER = Annotated[str | None, Header()]


@app.post("/callback")
async def callback(request: Request, x_line_signature: HEADER = None) -> str:
    if x_line_signature is None:
        _bad_request("Missing Signature")

    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")

    try:
        events = parser.parse(body_str, x_line_signature)
    except InvalidSignatureError as err:
        _bad_request("Invalid Signature", err)

    if not isinstance(events, list):
        _bad_request("Events not found")

    async with AsyncApiClient(configuration) as api_client:
        line_bot_api = AsyncMessagingApi(api_client)

        for event in events:
            await handle_message(event, line_bot_api)

    return "OK"


async def handle_message(event: MessageEvent, line_bot_api: AsyncMessagingApi) -> None:
    if not event.reply_token:
        logger.warning("Empty reply_token")
        return

    if not isinstance(event.message, TextMessageContent):
        return

    reply_text = f"Pythonから返信: {event.message.text}"
    message = TextMessage(
        text=reply_text,
        quickReply=None,
        quoteToken=None,
    )

    await line_bot_api.reply_message(
        ReplyMessageRequest(
            replyToken=event.reply_token,
            messages=[message],
            notificationDisabled=None,
        ),
    )


def _bad_request(message: str, e: Exception | None = None) -> Never:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from e
