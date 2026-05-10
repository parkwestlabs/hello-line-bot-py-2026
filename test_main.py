import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from linebot.v3.messaging.models.user_profile_response import UserProfileResponse
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.webhooks.models.delivery_context import DeliveryContext
from linebot.v3.webhooks.models.source import Source

from main import app

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.asyncio
async def test_callback_no_signature() -> None:
    # 署名がないリクエストを送った時に 400 (Bad Request) になるかテスト
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        response = await ac.post("/callback", content="test body")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Missing Signature"}


@pytest.mark.asyncio
async def test_callback_invalid_signature() -> None:
    # 適当な署名で送った時に 400 になるかテスト
    headers = {"X-Line-Signature": "invalid_sig"}
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        response = await ac.post("/callback", content='{"events":[]}', headers=headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Invalid Signature"}


@pytest.mark.asyncio
async def test_callback_success(mocker: MockerFixture) -> None:
    # 1. 署名とボディの準備
    headers = {"X-Line-Signature": "dummy_sig"}
    body_dict = {
        "events": [
            {
                "type": "message",
                "replyToken": "test_token",
                "message": {"type": "text", "text": "こんにちは"},
            },
        ],
    }
    body = json.dumps(body_dict)

    # 2. WebhookParser の parse メソッドを Mock化
    # 署名検証をスキップし、自作の MessageEvent を返すようにします
    mock_event = MessageEvent(
        replyToken="test_token",
        source=Source.from_dict({"type": "user", "userId": "USERID"}),
        message=TextMessageContent.from_dict(
            {
                "id": "msg_id",
                "type": "text",
                "text": "こんにちは",
                "quoteToken": "dummy",
            },
        ),
        mode="active",
        webhookEventId="evt_id",
        timestamp=0,
        deliveryContext=DeliveryContext(isRedelivery=False),
    )
    mocker.patch("main.parser.parse", return_value=[mock_event])

    # 3. AsyncMessagingApi の Mock 設定
    # これにより、実際に LINE サーバーへリクエストが飛ばなくなります

    # get_profile メソッドを Mock化
    mock_profile = mocker.patch(
        "linebot.v3.messaging.AsyncMessagingApi.get_profile",
        new_callable=AsyncMock,
    )
    mock_profile.return_value = UserProfileResponse(
        displayName="山田",
        userId="USERID",
        pictureUrl="",
        statusMessage="",
        language="",
    )

    # reply_message メソッドを Mock化
    mock_reply = mocker.patch(
        "linebot.v3.messaging.AsyncMessagingApi.reply_message",
        new_callable=AsyncMock,
    )

    # 4. テスト実行 (AsyncClient を使用)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        response = await ac.post("/callback", content=body, headers=headers)

    # 5. 検証
    assert response.status_code == status.HTTP_200_OK

    # API profile response の確認
    assert mock_profile.await_count == 1

    args, _ = mock_profile.call_args
    request_user_id = args[0]
    assert request_user_id == "USERID"

    # API reply_message の確認
    assert mock_reply.await_count == 1

    args, _ = mock_reply.call_args
    request_obj = args[0]
    assert request_obj.reply_token == "test_token"

    assert request_obj.messages[0].type == "text"
    assert request_obj.messages[0].text == "山田さんは「こんにちは」と言いましたね？"

    assert request_obj.messages[1].type == "sticker"
    assert request_obj.messages[1].package_id == "446"
    assert request_obj.messages[1].sticker_id == "1988"
