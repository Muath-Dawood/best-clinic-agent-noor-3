import os
from agents import FileSearchTool

def build_file_search_tool():
    vs_id = os.getenv("VECTOR_STORE_ID")
    if not vs_id:
        return None
    return FileSearchTool(vector_store_ids=[vs_id])
