import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()
notion = Client(auth=os.environ["NOTION_TOKEN"])
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
LOG_DATABASE_ID = os.environ["NOTION_LOG_DATABASE_ID"]

notion.databases.update(
    database_id=DATABASE_ID,
    properties={"試験日": {"date": {}}},
)
print("試験日プロパティを追加しました")
