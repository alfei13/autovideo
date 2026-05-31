import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from openai import OpenAI

from autovideo.config import Config
from autovideo.core.models import Scene, SceneStatus


class ImageGenerator:
    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI(
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
        )

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
                response = self.client.images.generate(
                    model=self.config.image.model,
                    prompt=prompt,
                    size=self.config.image.size,
                    quality=self.config.image.quality,
                    style=self.config.image.style,
                    n=1,
                )
                image_url = response.data[0].url
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                with httpx.Client(timeout=60) as http_client:
                    img_response = http_client.get(image_url)
                    img_response.raise_for_status()
                    with open(output_path, "wb") as f:
                        f.write(img_response.content)
                return output_path
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = self.config.pipeline.retry_delay * (2 ** attempt)
                    time.sleep(delay)
        raise RuntimeError(
            f"图片生成失败，重试{max_retries}次后仍出错: {last_error}"
        )
