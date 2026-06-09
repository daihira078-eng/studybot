import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()
notion = Client(auth=os.environ["NOTION_TOKEN"])
LOG_DATABASE_ID = os.environ["NOTION_LOG_DATABASE_ID"]

notion.databases.update(
    database_id=LOG_DATABASE_ID,
    properties={"記録日": {"date": {}}},
)
print("記録日プロパティを追加しました")
