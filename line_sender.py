import os
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    BroadcastRequest,
    ReplyMessageRequest,
)
from dotenv import load_dotenv

load_dotenv()

configuration = Configuration(access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"])


def send_broadcast(message):
    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        api.broadcast(BroadcastRequest(messages=[message]))


def send_reply(reply_token: str, message):
    messages = message if isinstance(message, list) else [message]
    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        api.reply_message(ReplyMessageRequest(reply_token=reply_token, messages=messages))
