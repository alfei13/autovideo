import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from autovideo.config import Config
from autovideo.core.models import Scene, SceneStatus

DASHSCOPE_BASE = "https://dashscope.aliyuncs.com"


class ImageGenerator:
    def __init__(self, config: Config):
        self.config = config
        self.api_key = config.image.api_key or os.getenv("DASHSCOPE_API_KEY", "")
        self.model = config.image.model
        self.size = config.image.size
        self.n = config.image.n
        self.style = config.image.style

    def generate(self, prompt: str, output_path: str) -> str:
        return self._generate_with_retry(
            prompt, output_path, max_retries=self.config.pipeline.max_retries
        )

    def generate_batch(self, scenes: list[Scene], output_dir: str) -> list[Scene]:
        os.makedirs(output_dir, exist_ok=True)
        updated_scenes = list(scenes)
        max_workers = self.config.pipeline.concurrent_images

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {}
            for scene in updated_scenes:
                if scene.status in (SceneStatus.PENDING, SceneStatus.SCRIPT_DONE):
                    output_path = os.path.join(output_dir, f"scene_{scene.id}.png")
                    future = executor.submit(
                        self._generate_with_retry,
                        scene.image_prompt,
                        output_path,
                        self.config.pipeline.max_retries,
                    )
                    future_to_index[future] = scene.id

            for future in as_completed(future_to_index):
                scene_id = future_to_index[future]
                try:
                    image_path = future.result()
                    for scene in updated_scenes:
                        if scene.id == scene_id:
                            scene.image_path = image_path
                            scene.status = SceneStatus.IMAGE_DONE
                            break
                except Exception as e:
                    for scene in updated_scenes:
                        if scene.id == scene_id:
                            scene.status = SceneStatus.FAILED
                            break
                    print(f"场景 {scene_id} 图片生成失败: {e}")

        return updated_scenes

    def _generate_with_retry(
        self, prompt: str, output_path: str, max_retries: int = 3
    ) -> str:
        last_error = None
        for attempt in range(max_retries):
            try:
                image_url = self._submit_and_poll(prompt)
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                with httpx.Client(timeout=120) as http_client:
                    img_response = http_client.get(image_url)
                    img_response.raise_for_status()
                    with open(output_path, "wb") as f:
                        f.write(img_response.content)
                return output_path
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = self.config.pipeline.retry_delay * (2 ** attempt)
                    print(f"  图片生成重试 {attempt + 1}/{max_retries}，等待{delay}秒...")
                    time.sleep(delay)
        raise RuntimeError(
            f"图片生成失败，重试{max_retries}次后仍出错: {last_error}"
        )

    def _submit_and_poll(self, prompt: str) -> str:
        task_id = self._create_task(prompt)
        return self._poll_task(task_id)

    def _create_task(self, prompt: str) -> str:
        url = f"{DASHSCOPE_BASE}/api/v1/services/aigc/text2image/image-synthesis"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-DashScope-Async": "enable",
        }
        body = {
            "model": self.model,
            "input": {
                "prompt": prompt,
            },
            "parameters": {
                "size": self.size,
                "n": self.n,
                "style": self.style,
            },
        }

        with httpx.Client(timeout=60) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()

        if "output" not in data:
            raise RuntimeError(f"创建图片生成任务失败: {data}")

        task_id = data["output"].get("task_id")
        if not task_id:
            raise RuntimeError(f"未获取到task_id: {data}")

        return task_id

    def _poll_task(self, task_id: str, max_wait: int = 300, interval: int = 3) -> str:
        url = f"{DASHSCOPE_BASE}/api/v1/tasks/{task_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        elapsed = 0
        while elapsed < max_wait:
            with httpx.Client(timeout=30) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

            status = data.get("output", {}).get("task_status", "")

            if status == "SUCCEEDED":
                results = data["output"].get("results", [])
                if not results:
                    raise RuntimeError(f"任务成功但无结果: {data}")
                image_url = results[0].get("url")
                if not image_url:
                    raise RuntimeError(f"结果中无图片URL: {data}")
                return image_url

            elif status == "FAILED":
                error_msg = data.get("output", {}).get("message", "未知错误")
                raise RuntimeError(f"图片生成任务失败: {error_msg}")

            elif status in ("PENDING", "RUNNING"):
                time.sleep(interval)
                elapsed += interval
            else:
                time.sleep(interval)
                elapsed += interval

        raise RuntimeError(f"图片生成任务超时({max_wait}秒)")
