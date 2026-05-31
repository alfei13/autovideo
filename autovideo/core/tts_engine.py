import asyncio
import os

import edge_tts
from mutagen.mp3 import MP3

from autovideo.config import Config
from autovideo.core.models import Scene, SceneStatus


class TTSEngine:
    def __init__(self, config: Config):
        self.config = config

    def synthesize(self, text: str, output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        communicate = edge_tts.Communicate(
            text,
            self.config.tts.voice,
            rate=self.config.tts.rate,
            volume=self.config.tts.volume,
        )
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(communicate.save(output_path))
        finally:
            loop.close()
        return output_path

    def synthesize_batch(self, scenes: list[Scene], output_dir: str) -> list[Scene]:
        os.makedirs(output_dir, exist_ok=True)
        updated_scenes = list(scenes)

        for scene in updated_scenes:
            if scene.status in (SceneStatus.PENDING, SceneStatus.SCRIPT_DONE, SceneStatus.IMAGE_DONE):
                if not scene.narration:
                    continue
                try:
                    output_path = os.path.join(output_dir, f"scene_{scene.id}.mp3")
                    self.synthesize(scene.narration, output_path)
                    scene.audio_path = output_path
                    scene.duration = self._get_audio_duration(output_path)
                    scene.status = SceneStatus.AUDIO_DONE
                except Exception as e:
                    scene.status = SceneStatus.FAILED
                    print(f"场景 {scene.id} 语音合成失败: {e}")

        return updated_scenes

    def _get_audio_duration(self, audio_path: str) -> float:
        try:
            audio = MP3(audio_path)
            return audio.info.length
        except Exception:
            return 0.0
