import argparse
import os
import sys

from autovideo.config import Config, load_config
from autovideo.core.pipeline import VideoPipeline


def main():
    parser = argparse.ArgumentParser(description="AutoVideo - AI文字转长视频")
    parser.add_argument("--text", type=str, help="输入文字内容")
    parser.add_argument("--text-file", type=str, help="从文件读取文字内容")
    parser.add_argument("--title", type=str, default="", help="视频标题")
    parser.add_argument("--output", type=str, default="./output", help="输出目录")
    parser.add_argument("--config", type=str, default="config.yaml", help="配置文件路径")
    parser.add_argument("--max-scenes", type=int, default=10, help="最大场景数")
    parser.add_argument("--voice", type=str, default="zh-CN-YunxiNeural", help="TTS语音")
    parser.add_argument("--web", action="store_true", help="启动Web界面")
    parser.add_argument("--port", type=int, default=7860, help="Web界面端口")
    parser.add_argument("--share", action="store_true", help="创建公开分享链接")

    args = parser.parse_args()

    config = load_config(args.config)

    if not config.llm.api_key:
        config = Config.from_env()

    if args.voice:
        config.tts.voice = args.voice

    if args.web:
        from autovideo.ui.app import AutoVideoApp
        app = AutoVideoApp(config)
        app.launch(share=args.share, server_port=args.port)
        return

    text = args.text
    if args.text_file:
        if not os.path.exists(args.text_file):
            print(f"错误: 文件不存在: {args.text_file}")
            sys.exit(1)
        with open(args.text_file, "r", encoding="utf-8") as f:
            text = f.read().strip()

    if not text:
        print("错误: 请通过 --text 或 --text-file 提供文字内容，或使用 --web 启动Web界面")
        parser.print_help()
        sys.exit(1)

    pipeline = VideoPipeline(config)

    output_dir = args.output
    if args.title:
        output_dir = os.path.join(args.output, args.title)

    try:
        final_path = pipeline.run(text, output_dir)
        print(f"\n✅ 视频生成完成: {final_path}")
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
