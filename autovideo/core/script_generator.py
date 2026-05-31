import json
from typing import Optional

from openai import OpenAI

from autovideo.config import Config
from autovideo.core.models import Scene, SceneStatus, VideoProject


class ScriptGenerator:
    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI(
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
        )

    def generate(self, text: str, max_scenes: int = 20) -> VideoProject:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个视频脚本编剧。将用户输入的文本内容拆分为适合制作视频的场景。"
                    "每个场景需要包含：场景标题、旁白文字（50-100字，适合朗读）、"
                    "图片描述（英文，用于AI生成图片，描述画面内容和风格）。"
                    f"最多拆分为{max_scenes}个场景。"
                    "输出JSON格式："
                    '[{"title": "...", "narration": "...", "image_prompt": "..."}]'
                    "只输出JSON数组，不要输出其他内容。"
                ),
            },
            {"role": "user", "content": text},
        ]
        llm_output = self._call_llm(messages)
        scenes = self._parse_scenes(llm_output)
        title = text[:50] + "..." if len(text) > 50 else text
        return VideoProject(title=title, scenes=scenes)

    def _call_llm(self, messages: list[dict]) -> str:
        response = self.client.chat.completions.create(
            model=self.config.llm.model,
            messages=messages,
            max_tokens=self.config.llm.max_tokens,
            temperature=self.config.llm.temperature,
        )
        return response.choices[0].message.content

    def _parse_scenes(self, llm_output: str) -> list[Scene]:
        json_str = llm_output.strip()
        if json_str.startswith("```"):
            first_newline = json_str.index("\n")
            last_backtick = json_str.rindex("```")
            json_str = json_str[first_newline + 1 : last_backtick].strip()
        try:
            scene_data = json.loads(json_str)
        except json.JSONDecodeError:
            start = json_str.find("[")
            end = json_str.rfind("]") + 1
            if start != -1 and end > start:
                scene_data = json.loads(json_str[start:end])
            else:
                raise ValueError(f"无法解析LLM输出为JSON: {llm_output[:200]}")

        scenes = []
        for i, item in enumerate(scene_data):
            scene = Scene(
                id=i,
                title=item.get("title", f"场景{i + 1}"),
                narration=item.get("narration", ""),
                image_prompt=item.get("image_prompt", ""),
                status=SceneStatus.SCRIPT_DONE,
            )
            scenes.append(scene)
        return scenes
