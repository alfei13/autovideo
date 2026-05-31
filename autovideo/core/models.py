from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SceneStatus(str, Enum):
    PENDING = "pending"
    SCRIPT_DONE = "script_done"
    IMAGE_DONE = "image_done"
    AUDIO_DONE = "audio_done"
    VIDEO_DONE = "video_done"
    FAILED = "failed"


@dataclass
class Scene:
    id: int
    title: str = ""
    narration: str = ""
    image_prompt: str = ""
    image_path: Optional[str] = None
    audio_path: Optional[str] = None
    video_path: Optional[str] = None
    duration: float = 0.0
    status: SceneStatus = SceneStatus.PENDING


@dataclass
class VideoProject:
    title: str = ""
    scenes: list[Scene] = field(default_factory=list)
    output_path: Optional[str] = None

    def get_scene(self, scene_id: int) -> Optional[Scene]:
        for scene in self.scenes:
            if scene.id == scene_id:
                return scene
        return None

    def get_pending_scenes(self) -> list[Scene]:
        return [s for s in self.scenes if s.status == SceneStatus.PENDING]

    def get_completed_scenes(self) -> list[Scene]:
        return [s for s in self.scenes if s.status == SceneStatus.VIDEO_DONE]

    def total_duration(self) -> float:
        return sum(s.duration for s in self.scenes)
