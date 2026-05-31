import os
from dataclasses import dataclass, field
from typing import Optional

import yaml


@dataclass
class LLMConfig:
    api_key: str = ""
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen-plus"
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class ImageConfig:
    provider: str = "dashscope"
    api_key: str = ""
    model: str = "wanx-v1"
    size: str = "1024*1024"
    n: int = 1
    style: str = "<auto>"


@dataclass
class TTSConfig:
    voice: str = "zh-CN-YunxiNeural"
    rate: str = "+0%"
    volume: str = "+0%"


@dataclass
class VideoConfig:
    fps: int = 24
    width: int = 1920
    height: int = 1080
    transition_duration: float = 1.0
    ken_burns_zoom_start: float = 1.0
    ken_burns_zoom_end: float = 1.15
    background_music_path: Optional[str] = None
    background_music_volume: float = 0.3

    @property
    def resolution(self) -> tuple[int, int]:
        return (self.width, self.height)


@dataclass
class PipelineConfig:
    concurrent_images: int = 3
    max_retries: int = 3
    retry_delay: float = 2.0
    max_scenes: int = 20


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    image: ImageConfig = field(default_factory=ImageConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)

    @classmethod
    def from_env(cls) -> "Config":
        config = cls()
        dashscope_key = os.getenv("DASHSCOPE_API_KEY", "")
        config.llm.api_key = dashscope_key
        config.llm.base_url = os.getenv("LLM_BASE_URL", config.llm.base_url)
        config.llm.model = os.getenv("LLM_MODEL", config.llm.model)
        config.image.api_key = dashscope_key
        config.image.model = os.getenv("IMAGE_MODEL", config.image.model)
        config.tts.voice = os.getenv("EDGE_TTS_VOICE", config.tts.voice)
        return config


DEFAULT_CONFIG = Config()


def load_config(path: str) -> Config:
    if not os.path.exists(path):
        return Config.from_env()
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    llm_data = data.get("llm", {})
    image_data = data.get("image", {})
    tts_data = data.get("tts", {})
    video_data = data.get("video", {})
    pipeline_data = data.get("pipeline", {})

    dashscope_key = os.getenv("DASHSCOPE_API_KEY", "")

    llm_api_key_env = llm_data.pop("api_key_env", None)
    if llm_api_key_env:
        llm_data["api_key"] = os.getenv(llm_api_key_env, dashscope_key)
    elif dashscope_key:
        llm_data["api_key"] = dashscope_key

    image_api_key_env = image_data.pop("api_key_env", None)
    if image_api_key_env:
        image_data["api_key"] = os.getenv(image_api_key_env, dashscope_key)
    elif dashscope_key:
        image_data["api_key"] = dashscope_key

    if "resolution" in video_data:
        res = video_data.pop("resolution")
        video_data["width"] = res.get("width", 1920)
        video_data["height"] = res.get("height", 1080)

    config = Config(
        llm=LLMConfig(**{k: v for k, v in llm_data.items() if k in LLMConfig.__dataclass_fields__}),
        image=ImageConfig(**{k: v for k, v in image_data.items() if k in ImageConfig.__dataclass_fields__}),
        tts=TTSConfig(**{k: v for k, v in tts_data.items() if k in TTSConfig.__dataclass_fields__}),
        video=VideoConfig(**{k: v for k, v in video_data.items() if k in VideoConfig.__dataclass_fields__}),
        pipeline=PipelineConfig(**{k: v for k, v in pipeline_data.items() if k in PipelineConfig.__dataclass_fields__}),
    )
    return config
