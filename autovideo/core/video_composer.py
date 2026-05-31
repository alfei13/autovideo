import os

import numpy as np
from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    CompositeAudioClip,
    ImageClip,
    VideoClip,
    VideoFileClip,
    concatenate_videoclips,
)
from PIL import Image

from autovideo.config import Config
from autovideo.core.models import Scene, SceneStatus


class VideoComposer:
    def __init__(self, config: Config):
        self.config = config

    def compose_scene(self, scene: Scene, output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        duration = scene.duration + 1.0
        fps = self.config.video.fps
        target_w, target_h = self.config.video.resolution

        img = Image.open(scene.image_path)
        img = img.resize((target_w, target_h), Image.LANCZOS)
        temp_img_path = output_path.replace(".mp4", "_resized.png")
        img.save(temp_img_path)

        clip = ImageClip(temp_img_path, duration=duration)
        clip = self._add_ken_burns(clip, duration)

        if scene.audio_path and os.path.exists(scene.audio_path):
            audio = AudioFileClip(scene.audio_path)
            clip = clip.with_audio(audio)

        clip = clip.with_fps(fps)
        clip.write_videofile(output_path, codec="libx264", audio_codec="aac", logger=None)

        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)

        scene.video_path = output_path
        scene.status = SceneStatus.VIDEO_DONE
        return output_path

    def compose_final(self, scenes: list[Scene], output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        completed = [s for s in scenes if s.status == SceneStatus.VIDEO_DONE and s.video_path]
        if not completed:
            raise ValueError("没有已完成的场景视频可供拼接")

        clips = []
        for scene in completed:
            clip = VideoFileClip(scene.video_path)
            clips.append(clip)

        transition_duration = self.config.video.transition_duration
        if transition_duration > 0 and len(clips) > 1:
            final = self._add_transition(clips, transition_duration)
        else:
            final = concatenate_videoclips(clips, method="compose")

        if self.config.video.background_music_path and os.path.exists(
            self.config.video.background_music_path
        ):
            bg_music = AudioFileClip(self.config.video.background_music_path)
            vol = self.config.video.background_music_volume
            original_array = bg_music.to_soundarray(fps=bg_music.fps)
            bg_music = bg_music.with_effects(
                [lambda c: c.with_audio(
                    c.audio.with_effects(
                        [lambda a: a.transform(lambda t, arr: arr * vol)]
                    )
                )]
            )
            if bg_music.duration < final.duration:
                bg_music = bg_music.loop(duration=final.duration)
            else:
                bg_music = bg_music.subclipped(0, final.duration)
            if final.audio is not None:
                final_audio = CompositeAudioClip([final.audio, bg_music])
                final = final.with_audio(final_audio)
            else:
                final = final.with_audio(bg_music)

        final.write_videofile(output_path, codec="libx264", audio_codec="aac", logger=None)
        return output_path

    def _add_ken_burns(self, clip, duration: float):
        zoom_start = self.config.video.ken_burns_zoom_start
        zoom_end = self.config.video.ken_burns_zoom_end
        target_w, target_h = self.config.video.resolution

        def make_frame(t):
            progress = t / duration
            zoom = zoom_start + (zoom_end - zoom_start) * progress
            current_w = int(target_w * zoom)
            current_h = int(target_h * zoom)
            frame = clip.get_frame(t)
            pil_img = Image.fromarray(frame)
            pil_img = pil_img.resize((current_w, current_h), Image.LANCZOS)
            canvas = Image.new("RGB", (target_w, target_h))
            paste_x = (target_w - current_w) // 2
            paste_y = (target_h - current_h) // 2
            canvas.paste(pil_img, (paste_x, paste_y))
            return np.array(canvas)

        return VideoClip(make_frame, duration=duration).with_fps(clip.fps or self.config.video.fps)

    def _add_transition(self, clips: list, transition_duration: float):
        fps = self.config.video.fps
        sequence = []
        for i, clip in enumerate(clips):
            if i == 0:
                sequence.append(clip)
            else:
                start_time = sequence[-1].end - transition_duration
                offset_clip = clip.with_start(start_time)
                sequence.append(offset_clip)

        total_duration = sequence[-1].end
        target_w, target_h = self.config.video.resolution

        def make_frame(t):
            for i in range(len(sequence) - 1, -1, -1):
                clip = sequence[i]
                if clip.start <= t < clip.end:
                    frame_t = t - clip.start
                    if frame_t < 0:
                        continue
                    try:
                        frame = clip.get_frame(frame_t)
                    except Exception:
                        continue
                    if i > 0 and t < clip.start + transition_duration:
                        progress = (t - clip.start) / transition_duration
                        prev_clip = sequence[i - 1]
                        prev_t = t - prev_clip.start
                        try:
                            prev_frame = prev_clip.get_frame(prev_t)
                        except Exception:
                            return frame
                        blended = (
                            prev_frame.astype(np.float64) * (1 - progress)
                            + frame.astype(np.float64) * progress
                        )
                        return blended.astype(np.uint8)
                    return frame
            return clips[0].get_frame(0)

        final = VideoClip(make_frame, duration=total_duration).with_fps(fps)
        audio_clips = []
        for clip in sequence:
            if clip.audio is not None:
                audio_clips.append(clip.audio)
        if audio_clips:
            final = final.with_audio(CompositeAudioClip(audio_clips))
        return final
