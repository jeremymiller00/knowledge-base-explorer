import os
import sys
import json
import asyncio

from storage.database import Database
from utils.config import DB_CONN_STRING, DATA_DIR
from utils.logger import configure_logging

logger = configure_logging()


async def main(data_dir: str):
    if not data_dir:
        print("Must specify a data directory")
        sys.exit(1)

    # Initialize database
    db = Database(
        # connection_string="postgresql://postgres:postgres@localhost:5432/knowledge_base"
        connection_string=DB_CONN_STRING
    )

    # loop through directories in data_dir
    for subdir, dirs, files in os.walk(data_dir):
        for file in files:
            file_path = os.path.join(subdir, file)
            if file_path.endswith(".json"):
                # print(os.path.join(subdir, file))
                logger.info(f"Accessed {file_path}")
                with open(file_path) as file:
                    data = json.load(file)
                content_id = await db.store_content(data)
                logger.info(f"Populated database with {content_id}")


if __name__ == '__main__':
    print("you are here")
    # asyncio.run(main(data_dir=DATA_DIR))