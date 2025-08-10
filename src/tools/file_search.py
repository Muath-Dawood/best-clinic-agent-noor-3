import os
from agents import FileSearchTool


def build_file_search_tool():
    VS_KB = os.getenv("VECTOR_STORE_ID_KB", "").strip()
    if not VS_KB:
        return None
    return FileSearchTool(vector_store_ids=[VS_KB])
