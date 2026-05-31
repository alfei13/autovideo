import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class ImageConfig:
    model: str = "dall-e-3"
    size: str = "1792x1024"
    quality: str = "standard"
    style: str = "vivid"


@dataclass
class TTSConfig:
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: str = "+0%"
    volume: str = "+0%"


@dataclass
class VideoConfig:
    fps: int = 24
    resolution: tuple = (1920, 1080)
    transition_duration: float = 1.0
    ken_burns_zoom_range: tuple = (1.0, 1.15)
    background_music_path: Optional[str] = None
    background_music_volume: float = 0.3


@dataclass
class PipelineConfig:
    concurrent_images: int = 3
    max_retries: int = 3
    retry_delay: float = 2.0


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
        config.llm.api_key = os.getenv("OPENAI_API_KEY", "")
        config.llm.base_url = os.getenv("OPENAI_BASE_URL", config.llm.base_url)
        config.llm.model = os.getenv("OPENAI_MODEL", config.llm.model)
        config.tts.voice = os.getenv("EDGE_TTS_VOICE", config.tts.voice)
        return config
