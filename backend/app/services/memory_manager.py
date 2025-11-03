import json, os
from typing import Dict, Any

MEMORY_DIR = "data/memory_cache"
os.makedirs(MEMORY_DIR, exist_ok=True)

class ChapterMemoryManager:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.file_path = os.path.join(MEMORY_DIR, f"{project_id}_memory.json")
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def load(self) -> Dict[str, Any]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, data: Dict[str, Any]):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_chapter_summary(self, chapter_id: str) -> str:
        data = self.load()
        return data.get(chapter_id, {}).get("summary", "")

    def get_sibling_summaries(self, parent_id: str, exclude_id: str = None) -> str:
        data = self.load()
        siblings = []
        for cid, val in data.items():
            if cid.startswith(parent_id) and cid != exclude_id:
                if val.get("summary"):
                    siblings.append(f"{val['title']}: {val['summary']}")
        return "\n".join(siblings)

    def save_chapter(self, chapter_id: str, title: str, content: str, summary: str):
        data = self.load()
        data[chapter_id] = {"title": title, "content": content, "summary": summary}
        self.save(data)
