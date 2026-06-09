import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()
notion = Client(auth=os.environ["NOTION_TOKEN"])
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
LOG_DATABASE_ID = os.environ["NOTION_LOG_DATABASE_ID"]

notion.databases.update(
    database_id=LOG_DATABASE_ID,
    properties={"現在の科目": {"rich_text": {}}},
)
print("現在の科目プロパティを追加しました")
