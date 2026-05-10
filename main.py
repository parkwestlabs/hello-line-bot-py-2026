import logging
import os
from collections import deque
from dataclasses import dataclass
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
    StickerMessage,
    TextMessage,
)
from linebot.v3.webhook import WebhookParser
from linebot.v3.webhooks import (
    ApiException,
    MessageEvent,
    TextMessageContent,
    UserSource,
)

# official sample code
# https://github.com/line/line-bot-sdk-python

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)
logger.setLevel(logging.INFO)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(LINE_CHANNEL_SECRET)

HEADER = Annotated[str | None, Header()]

# グローバル変数に webhook_event_id を簡易 cache する (1つのインスタンス前提)
processed_event_ids = deque(maxlen=1000)


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
    logger.info(
        "MessageEvent: source.type=%s, message.type=%s, webhook_event_id=%s",
        event.source.type if event.source else "NoneSource",
        event.message.type,
        event.webhook_event_id,
    )

    if not _should_process_event(event.webhook_event_id):
        return

    # UserSource TextMessageContent 以外はスルー
    user_text = parse_user_text(event)

    if user_text:
        await handle_user_interaction(user_text, line_bot_api)


def _should_process_event(webhook_id: str) -> bool:
    """
    reply_message で replyToken が重複して Bad Request になり
    {"message":"Invalid reply token"} が出ることの防止用
    """
    if webhook_id in processed_event_ids:
        logger.info("Duplicate event ignored: %s", webhook_id)
        return False

    # キャッシュに追加
    processed_event_ids.append(webhook_id)
    return True


async def handle_user_interaction(msg: UserText, api: AsyncMessagingApi) -> None:
    user_name = await find_user_name(msg.user_id, api)

    reply_text = f"{user_name}さんは「{msg.text}」と言いましたね？"
    message = TextMessage(text=reply_text, quickReply=None, quoteToken=None)

    # LINE公式のスタンプ一覧から無料で使えるスタンプIDを取得する
    # https://developers.line.biz/ja/docs/messaging-api/sticker-list/
    sticker = StickerMessage(
        packageId="446", stickerId="1988", quickReply=None, quoteToken=None
    )

    await reply_message([message, sticker], msg.reply_token, api)


async def find_user_name(user_id: str, api: AsyncMessagingApi) -> str:
    try:
        profile = await api.get_profile(user_id)
        user_name = profile.display_name
    except ApiException:
        logger.exception("Error get_profile: %s", user_id)
        user_name = "ユーザー"

    return user_name


async def reply_message(
    messages: list, reply_token: str, api: AsyncMessagingApi
) -> None:
    await api.reply_message(
        ReplyMessageRequest(
            replyToken=reply_token,
            messages=messages,
            notificationDisabled=None,
        ),
    )


def _bad_request(message: str, e: Exception | None = None) -> Never:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from e


# MessageEvent の種別を source と message で判別して、必要な値だけを抜き出す
# Source は3種類:
#   UserSource, GroupSource, RoomSource
# MessageContent は7種類:
#   TextMessageContent, ImageMessageContent,
#   VideoMessageContent, AudioMessageContent,
#   LocationMessageContent, StickerMessageContent, FileMessageContent


@dataclass(frozen=True)
class UserText:
    user_id: str
    text: str
    reply_token: str


def parse_user_text(event: MessageEvent) -> UserText | None:
    if not isinstance(event.source, UserSource):
        return None
    if not isinstance(event.message, TextMessageContent):
        return None

    if not event.reply_token:
        logger.warning("Empty reply_token")
        return None

    if not event.source.user_id:
        logger.warning("Empty user_id")
        return None

    return UserText(
        user_id=event.source.user_id,
        text=event.message.text,
        reply_token=event.reply_token,
    )
