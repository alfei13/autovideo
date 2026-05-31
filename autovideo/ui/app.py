import os

import gradio as gr

from autovideo.config import Config, load_config, DEFAULT_CONFIG
from autovideo.core.models import SceneStatus
from autovideo.core.pipeline import VideoPipeline
from autovideo.core.script_generator import ScriptGenerator


class AutoVideoApp:
    def __init__(self, config: Config | None = None):
        self.config = config or DEFAULT_CONFIG
        self.pipeline = VideoPipeline(self.config)
        self.current_project = None
        self.progress_text = ""
        self.is_running = False

    def generate_video(
        self, text, title, max_scenes, voice, image_size, progress=gr.Progress()
    ):
        if not text or not text.strip():
            return None, "请输入文字内容"

        if self.is_running:
            return None, "已有任务正在运行，请等待完成"

        self.is_running = True
        self.progress_text = ""

        self.config.tts.voice = voice
        self.config.image.size = image_size

        self.pipeline = VideoPipeline(self.config)

        output_dir = os.path.join(
            "./output", title.strip() if title.strip() else "untitled"
        )

        try:
            progress(0.0, desc="正在生成视频脚本...")
            self.progress_text += "📋 正在生成视频脚本...\n"

            project = self.pipeline.script_generator.generate(
                text, max_scenes=int(max_scenes)
            )
            if title and title.strip():
                project.title = title.strip()
            self.current_project = project

            self.progress_text += f"✅ 已生成 {len(project.scenes)} 个场景\n"
            progress(0.25, desc="正在生成场景图片...")

            images_dir = os.path.join(output_dir, "images")
            project.scenes = self.pipeline.image_generator.generate_batch(
                project.scenes, images_dir
            )
            done_count = sum(1 for s in project.scenes if s.image_path)
            self.progress_text += (
                f"🖼️ 已生成 {done_count}/{len(project.scenes)} 张图片\n"
            )
            progress(0.5, desc="正在合成语音...")

            audio_dir = os.path.join(output_dir, "audio")
            project.scenes = self.pipeline.tts_engine.synthesize_batch(
                project.scenes, audio_dir
            )
            done_count = sum(1 for s in project.scenes if s.audio_path)
            self.progress_text += (
                f"🔊 已合成 {done_count}/{len(project.scenes)} 段语音\n"
            )
            progress(0.75, desc="正在合成视频...")

            scenes_dir = os.path.join(output_dir, "scenes")
            for scene in project.scenes:
                if scene.status == SceneStatus.AUDIO_DONE:
                    scene_video_path = os.path.join(scenes_dir, f"scene_{scene.id}.mp4")
                    try:
                        self.pipeline.video_composer.compose_scene(
                            scene, scene_video_path
                        )
                    except Exception as e:
                        scene.status = SceneStatus.FAILED
                        self.progress_text += f"⚠️ 场景 {scene.id} 合成失败: {e}\n"

            final_path = os.path.join(output_dir, "final_video.mp4")
            self.pipeline.video_composer.compose_final(project.scenes, final_path)
            project.output_path = final_path

            self.progress_text += f"🎉 视频生成完成！\n📁 保存至: {final_path}\n"
            progress(1.0, desc="完成！")

            return final_path, self.progress_text

        except Exception as e:
            self.progress_text += f"❌ 生成失败: {str(e)}\n"
            return None, self.progress_text
        finally:
            self.is_running = False

    def preview_script(self, text, max_scenes):
        if not text or not text.strip():
            return "请输入文字内容"

        try:
            project = self.pipeline.script_generator.generate(
                text, max_scenes=int(max_scenes)
            )

            md = f"## 📋 脚本预览 ({len(project.scenes)} 个场景)\n\n"
            md += "| # | 场景标题 | 旁白 | 图片提示词 |\n"
            md += "|---|---------|------|------------|\n"
            for scene in project.scenes:
                narration = scene.narration.replace("|", "｜").replace("\n", " ")
                image_prompt = scene.image_prompt.replace("|", "｜").replace("\n", " ")
                title = scene.title.replace("|", "｜")
                md += f"| {scene.id + 1} | {title} | {narration} | {image_prompt} |\n"

            self.current_project = project
            return md

        except Exception as e:
            return f"❌ 脚本生成失败: {str(e)}"

    def create_ui(self):
        with gr.Blocks(title="AutoVideo - AI视频生成器", theme=gr.themes.Soft()) as app:
            gr.Markdown(
                "# 🎬 AutoVideo - AI文字转长视频\n输入文字内容，AI自动生成完整视频"
            )

            with gr.Row():
                with gr.Column(scale=2):
                    text_input = gr.Textbox(
                        label="📝 输入文字内容",
                        lines=10,
                        placeholder="输入你想生成视频的文字内容...",
                    )
                    title_input = gr.Textbox(
                        label="🎬 视频标题", placeholder="可选，留空则自动生成"
                    )

                    with gr.Row():
                        max_scenes = gr.Slider(
                            3, 50, value=10, step=1, label="场景数量"
                        )
                        voice = gr.Dropdown(
                            choices=[
                                "zh-CN-YunxiNeural",
                                "zh-CN-XiaoxiaoNeural",
                                "zh-CN-YunjianNeural",
                                "en-US-AndrewNeural",
                                "en-US-AriaNeural",
                            ],
                            value="zh-CN-YunxiNeural",
                            label="🔊 语音",
                        )
                        image_size = gr.Dropdown(
                            choices=["1792x1024", "1024x1792", "1024x1024"],
                            value="1792x1024",
                            label="🖼️ 图片尺寸",
                        )

                    with gr.Row():
                        preview_btn = gr.Button("📋 预览脚本", variant="secondary")
                        generate_btn = gr.Button("🚀 生成视频", variant="primary")

                    progress_output = gr.Textbox(
                        label="📊 进度", lines=5, interactive=False
                    )

                with gr.Column(scale=1):
                    script_preview = gr.Markdown(label="脚本预览")
                    video_output = gr.Video(label="🎬 生成结果")

            preview_btn.click(
                fn=self.preview_script,
                inputs=[text_input, max_scenes],
                outputs=[script_preview],
            )
            generate_btn.click(
                fn=self.generate_video,
                inputs=[text_input, title_input, max_scenes, voice, image_size],
                outputs=[video_output, progress_output],
            )

        return app

    def launch(self, share=False, server_port=7860):
        app = self.create_ui()
        app.launch(share=share, server_port=server_port)
