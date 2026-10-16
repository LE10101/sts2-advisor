"""
GitHub持久化存储模块
将历史对局数据保存到GitHub仓库，防止云端重启丢失
每个对局保存为 data/runs/{user_id}/{run_id}.json
"""
import json
import os
import time
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any


class GitHubStorage:
    """GitHub持久化存储"""

    def __init__(self):
        self.token = os.environ.get("GITHUB_TOKEN", "")
        self.repo = os.environ.get("GITHUB_REPO", "LE10101/sts2-advisor")
        self.branch = os.environ.get("GITHUB_BRANCH", "main")
        self.enabled = bool(self.token and self.repo)
        self._cache = {}
        self._last_sync = 0

    def _api_request(self, path: str, method: str = "GET", data: dict = None) -> Optional[dict]:
        """发送GitHub API请求"""
        if not self.enabled:
            return None
        url = f"https://api.github.com/{path}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        }
        try:
            body = json.dumps(data).encode("utf-8") if data else None
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            print(f"[GitHubStorage] API错误 {e.code}: {e.reason}")
            return None
        except Exception as e:
            print(f"[GitHubStorage] 请求失败: {e}")
            return None

    def save_run(self, run_data: dict, user_id: int = 0) -> bool:
        """保存对局到GitHub"""
        if not self.enabled:
            return False

        run_id = run_data.get("id", f"run_{int(time.time())}")
        path = f"data/runs/{user_id}/{run_id}.json"
        content = json.dumps(run_data, ensure_ascii=False, indent=2)

        # 检查文件是否存在（获取sha用于更新）
        existing = self._api_request(f"repos/{self.repo}/contents/{path}?ref={self.branch}")
        sha = existing.get("sha") if existing else None

        # 编码内容为base64
        import base64
        content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        data = {
            "message": f"保存对局 {run_id}",
            "content": content_b64,
            "branch": self.branch,
        }
        if sha:
            data["sha"] = sha

        result = self._api_request(f"repos/{self.repo}/contents/{path}", "PUT", data)
        if result:
            print(f"[GitHubStorage] 对局已保存: {run_id}")
            return True
        return False

    def load_run(self, run_id: str, user_id: int = 0) -> Optional[dict]:
        """从GitHub加载对局"""
        if not self.enabled:
            return None

        path = f"data/runs/{user_id}/{run_id}.json"
        result = self._api_request(f"repos/{self.repo}/contents/{path}?ref={self.branch}")
        if result and "content" in result:
            import base64
            content = base64.b64decode(result["content"]).decode("utf-8")
            return json.loads(content)
        return None

    def list_runs(self, user_id: int = 0) -> List[dict]:
        """列出用户的所有对局"""
        if not self.enabled:
            return []

        path = f"data/runs/{user_id}"
        result = self._api_request(f"repos/{self.repo}/contents/{path}?ref={self.branch}")
        if not result or not isinstance(result, list):
            return []

        runs = []
        for item in result:
            if item.get("name", "").endswith(".json"):
                run_id = item["name"].replace(".json", "")
                run_data = self.load_run(run_id, user_id)
                if run_data:
                    runs.append({
                        "id": run_data.get("id", run_id),
                        "date": run_data.get("date", ""),
                        "character": run_data.get("character", ""),
                        "ascension": run_data.get("ascension", 0),
                        "floor": run_data.get("max_floor", 0),
                        "result": run_data.get("result", ""),
                        "deck_size": len(run_data.get("deck", [])),
                        "relics": len(run_data.get("relics", [])),
                    })
        runs.sort(key=lambda x: x.get("date", ""), reverse=True)
        return runs

    def sync_all_to_db(self, db_save_func, user_id: int = 0):
        """将GitHub上的所有对局同步到本地数据库"""
        if not self.enabled:
            return 0

        runs = self.list_runs(user_id)
        count = 0
        for run_summary in runs:
            run_data = self.load_run(run_summary["id"], user_id)
            if run_data:
                db_save_func(run_data, user_id)
                count += 1
        print(f"[GitHubStorage] 从GitHub同步了 {count} 局对局")
        return count


# 全局单例
_github_storage = None


def get_github_storage() -> GitHubStorage:
    global _github_storage
    if _github_storage is None:
        _github_storage = GitHubStorage()
    return _github_storage
