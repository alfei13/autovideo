import os

from autovideo.config import Config
from autovideo.core.models import SceneStatus, VideoProject
from autovideo.core.script_generator import ScriptGenerator
from autovideo.core.image_generator import ImageGenerator
from autovideo.core.tts_engine import TTSEngine
from autovideo.core.video_composer import VideoComposer


class VideoPipeline:
    def __init__(self, config: Config):
        self.config = config
        self.script_generator = ScriptGenerator(config)
        self.image_generator = ImageGenerator(config)
        self.tts_engine = TTSEngine(config)
        self.video_composer = VideoComposer(config)
        self._progress = {
            "current_stage": "",
            "total_scenes": 0,
            "completed_scenes": 0,
        }

    def run(self, text: str, output_dir: str = "./output") -> str:
        os.makedirs(output_dir, exist_ok=True)

        self._progress["current_stage"] = "script_generation"
        print("[1/4] 正在分析文本，生成视频脚本...")
        project = self.script_generator.generate(text)
        self._progress["total_scenes"] = len(project.scenes)
        print(f"  已生成 {len(project.scenes)} 个场景")

        self._progress["current_stage"] = "image_generation"
        print("[2/4] 正在生成场景图片...")
        images_dir = os.path.join(output_dir, "images")
        project.scenes = self.image_generator.generate_batch(project.scenes, images_dir)
        done_count = sum(1 for s in project.scenes if s.status == SceneStatus.IMAGE_DONE)
        print(f"  已生成 {done_count}/{len(project.scenes)} 张图片")

        self._progress["current_stage"] = "tts_synthesis"
        print("[3/4] 正在合成语音...")
        audio_dir = os.path.join(output_dir, "audio")
        project.scenes = self.tts_engine.synthesize_batch(project.scenes, audio_dir)
        done_count = sum(1 for s in project.scenes if s.status == SceneStatus.AUDIO_DONE)
        print(f"  已合成 {done_count}/{len(project.scenes)} 段语音")

        self._progress["current_stage"] = "video_composition"
        print("[4/4] 正在合成视频...")
        scenes_dir = os.path.join(output_dir, "scenes")
        for scene in project.scenes:
            if scene.status == SceneStatus.AUDIO_DONE:
                scene_video_path = os.path.join(scenes_dir, f"scene_{scene.id}.mp4")
                try:
                    self.video_composer.compose_scene(scene, scene_video_path)
                    self._progress["completed_scenes"] += 1
                except Exception as e:
                    scene.status = SceneStatus.FAILED
                    print(f"  场景 {scene.id} 视频合成失败: {e}")

        completed = sum(1 for s in project.scenes if s.status == SceneStatus.VIDEO_DONE)
        print(f"  已合成 {completed}/{len(project.scenes)} 个场景视频")

        final_path = os.path.join(output_dir, "final_video.mp4")
        print("正在拼接最终视频...")
        self.video_composer.compose_final(project.scenes, final_path)
        print(f"最终视频已保存至: {final_path}")

        project.output_path = final_path
        self._progress["current_stage"] = "completed"
        return final_path

    def run_from_project(self, project: VideoProject, output_dir: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        self._progress["total_scenes"] = len(project.scenes)

        scenes_need_images = [
            s for s in project.scenes if s.status in (SceneStatus.PENDING, SceneStatus.SCRIPT_DONE)
        ]
        if scenes_need_images:
            self._progress["current_stage"] = "image_generation"
            print(f"[续作] 正在生成 {len(scenes_need_images)} 个场景的图片...")
            images_dir = os.path.join(output_dir, "images")
            project.scenes = self.image_generator.generate_batch(project.scenes, images_dir)

        scenes_need_audio = [
            s
            for s in project.scenes
            if s.status in (SceneStatus.PENDING, SceneStatus.SCRIPT_DONE, SceneStatus.IMAGE_DONE)
        ]
        if scenes_need_audio:
            self._progress["current_stage"] = "tts_synthesis"
            print(f"[续作] 正在合成 {len(scenes_need_audio)} 段语音...")
            audio_dir = os.path.join(output_dir, "audio")
            project.scenes = self.tts_engine.synthesize_batch(project.scenes, audio_dir)

        scenes_need_video = [
            s for s in project.scenes if s.status == SceneStatus.AUDIO_DONE
        ]
        if scenes_need_video:
            self._progress["current_stage"] = "video_composition"
            print(f"[续作] 正在合成 {len(scenes_need_video)} 个场景视频...")
            scenes_dir = os.path.join(output_dir, "scenes")
            for scene in scenes_need_video:
                scene_video_path = os.path.join(scenes_dir, f"scene_{scene.id}.mp4")
                try:
                    self.video_composer.compose_scene(scene, scene_video_path)
                    self._progress["completed_scenes"] += 1
                except Exception as e:
                    scene.status = SceneStatus.FAILED
                    print(f"  场景 {scene.id} 视频合成失败: {e}")

        final_path = os.path.join(output_dir, "final_video.mp4")
        completed = [s for s in project.scenes if s.status == SceneStatus.VIDEO_DONE]
        if completed:
            print("[续作] 正在拼接最终视频...")
            self.video_composer.compose_final(project.scenes, final_path)
            print(f"最终视频已保存至: {final_path}")
            project.output_path = final_path

        self._progress["current_stage"] = "completed"
        return final_path

    def get_progress(self) -> dict:
        return dict(self._progress)
