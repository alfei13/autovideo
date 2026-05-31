# AutoVideo - AI文字转长视频

基于AI的自动化视频生成系统，输入文字内容即可自动生成完整的长视频。

## ✨ 功能特性

- 📝 **智能脚本生成**：AI自动将长文本拆分为多个视频场景，生成旁白和画面描述
- 🖼️ **AI图片生成**：使用DALL-E 3为每个场景生成高质量配图
- 🔊 **TTS语音合成**：使用Edge-TTS为每个场景生成自然语音旁白
- 🎬 **视频合成**：自动将图片+语音合成为视频片段，添加Ken Burns效果和转场
- 🎞️ **长视频拼接**：将多个场景视频片段拼接为完整长视频

## 🏗️ 系统架构

```
输入文本 → 脚本生成 → 图片生成 → 语音合成 → 场景合成 → 最终拼接 → 输出视频
              ↓           ↓           ↓           ↓
         ScriptGen   ImageGen    TTSEngine   VideoComposer
```

## 🚀 快速开始

### 安装

```bash
pip install -e .
```

### 配置

复制环境变量模板并填入API密钥：

```bash
cp .env.example .env
# 编辑.env，填入OPENAI_API_KEY
```

### Web界面

```bash
python main.py --web
# 或
autovideo --web
```

访问 http://localhost:7860 使用Web界面。

### CLI模式

```bash
# 直接输入文字
python main.py --text "人工智能的发展历程从图灵测试开始..."

# 从文件读取
python main.py --text-file article.txt --title "AI发展史" --max-scenes 15

# 自定义语音和输出
python main.py --text "内容" --voice zh-CN-YunxiNeural --output ./my_video
```

## ⚙️ 配置说明

编辑 `config.yaml` 自定义配置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `llm.model` | LLM模型 | gpt-4o |
| `image.model` | 图片生成模型 | dall-e-3 |
| `image.size` | 图片尺寸 | 1792x1024 |
| `tts.voice` | TTS语音 | zh-CN-YunxiNeural |
| `video.fps` | 视频帧率 | 24 |
| `video.resolution` | 视频分辨率 | 1920x1080 |
| `video.transition_duration` | 转场时长(秒) | 1.0 |

### 可用TTS语音

- 中文：zh-CN-YunxiNeural（男声）、zh-CN-XiaoxiaoNeural（女声）、zh-CN-YunjianNeural（男声）
- 英文：en-US-AndrewNeural（男声）、en-US-AriaNeural（女声）

## 📁 项目结构

```
autovideo/
├── main.py                    # 入口
├── config.yaml                # 配置文件
├── autovideo/
│   ├── cli.py                 # CLI入口
│   ├── config.py              # 配置系统
│   ├── core/
│   │   ├── models.py          # 数据模型
│   │   ├── script_generator.py # 脚本生成
│   │   ├── image_generator.py  # 图片生成
│   │   ├── tts_engine.py       # 语音合成
│   │   ├── video_composer.py   # 视频合成
│   │   └── pipeline.py         # 完整流水线
│   └── ui/
│       └── app.py             # Gradio Web界面
└── tests/
```

## 🔧 技术栈

- **LLM**: OpenAI GPT-4o（脚本生成）
- **Image**: OpenAI DALL-E 3（图片生成）
- **TTS**: Microsoft Edge-TTS（语音合成，免费）
- **Video**: MoviePy + FFmpeg（视频合成）
- **UI**: Gradio（Web界面）

## 📄 License

MIT
