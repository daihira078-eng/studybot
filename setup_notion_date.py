import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()
notion = Client(auth=os.environ["NOTION_TOKEN"])
LOG_DATABASE_ID = os.environ["NOTION_LOG_DATABASE_ID"]

notion.databases.update(
    database_id=LOG_DATABASE_ID,
    properties={"勉強時間(分)": {"number": {"format": "number"}}},
)
print("勉強時間(分)プロパティを追加しました")
