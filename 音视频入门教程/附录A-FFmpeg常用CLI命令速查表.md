# 附录 A：FFmpeg 常用 CLI 命令速查表

## 查看信息

```bash
# 查看文件信息
ffprobe input.mp4

# 详细 JSON 格式输出
ffprobe -v quiet -show_format -show_streams -print_format json input.mp4

# 查看每个包的信息
ffprobe -v quiet -show_packets -select_streams v:0 input.mp4

# 查看每帧信息
ffprobe -v quiet -show_frames -select_streams v:0 input.mp4

# 查看关键帧
ffprobe -v quiet -select_streams v:0 -show_entries frame=pict_type,pts_time \
  -of csv input.mp4 | grep I
```

## 格式转换

```bash
# MP4 转 MKV
ffmpeg -i input.mp4 -c copy output.mkv

# 转码为 H.264 + AAC
ffmpeg -i input.avi -c:v libx264 -crf 23 -c:a aac -b:a 128k output.mp4

# 指定分辨率
ffmpeg -i input.mp4 -vf scale=1280:720 -c:v libx264 -c:a copy output_720p.mp4

# 指定帧率
ffmpeg -i input.mp4 -r 30 -c:v libx264 -c:a copy output_30fps.mp4

# MP4 faststart（Web 优化）
ffmpeg -i input.mp4 -c copy -movflags +faststart output.mp4
```

## 提取和分离

```bash
# 提取视频（去掉音频）
ffmpeg -i input.mp4 -an -c:v copy video_only.mp4

# 提取音频
ffmpeg -i input.mp4 -vn -c:a copy audio.aac

# 提取音频为 WAV
ffmpeg -i input.mp4 -vn -f wav audio.wav

# 提取音频为 PCM
ffmpeg -i input.mp4 -vn -f s16le -acodec pcm_s16le -ar 44100 -ac 2 audio.pcm

# 提取某一帧为图片
ffmpeg -i input.mp4 -ss 00:01:30 -frames:v 1 frame.png

# 提取关键帧
ffmpeg -i input.mp4 -vf "select=eq(pict_type\,I)" -vsync vfr keyframes_%03d.png
```

## 裁剪和拼接

```bash
# 裁剪时间段（不重新编码）
ffmpeg -i input.mp4 -ss 00:01:00 -to 00:02:00 -c copy clip.mp4

# 裁剪画面区域
ffmpeg -i input.mp4 -vf "crop=640:480:100:50" cropped.mp4

# 拼接视频（先创建文件列表）
echo "file 'part1.mp4'" > list.txt
echo "file 'part2.mp4'" >> list.txt
ffmpeg -f concat -safe 0 -i list.txt -c copy merged.mp4
```

## 图片和视频互转

```bash
# 视频转图片序列
ffmpeg -i input.mp4 -r 1 frames_%04d.png  # 每秒 1 帧

# 图片序列转视频
ffmpeg -framerate 24 -i frames_%04d.png -c:v libx264 -pix_fmt yuv420p output.mp4

# GIF 转视频
ffmpeg -i input.gif -c:v libx264 -pix_fmt yuv420p output.mp4

# 视频转 GIF
ffmpeg -i input.mp4 -vf "fps=10,scale=320:-1" -gifflags +transdiff output.gif
```

## 音频处理

```bash
# 调整音量
ffmpeg -i input.mp4 -af "volume=2.0" -c:v copy louder.mp4

# 生成测试音频（正弦波）
ffmpeg -f lavfi -i "sine=frequency=440:duration=5" test_tone.wav

# 混合两个音频
ffmpeg -i audio1.mp3 -i audio2.mp3 -filter_complex amix=inputs=2 mixed.mp3

# 音频变速不变调
ffmpeg -i input.mp3 -af "atempo=1.5" faster.mp3
```

## 生成测试源

```bash
# 测试视频（彩条）
ffmpeg -f lavfi -i testsrc2=size=1280x720:rate=24:duration=10 test.mp4

# 测试视频 + 测试音频
ffmpeg -f lavfi -i "testsrc2=size=1280x720:rate=24:duration=10" \
       -f lavfi -i "sine=frequency=440:duration=10:sample_rate=48000" \
       -c:v libx264 -c:a aac test_av.mp4

# 纯色视频
ffmpeg -f lavfi -i "color=c=blue:s=1920x1080:d=5" blue.mp4
```

## 流媒体

```bash
# 播放 RTMP 流
ffplay rtmp://live.example.com/stream

# 播放 HLS
ffplay http://example.com/stream.m3u8

# 推流到 RTMP 服务器
ffmpeg -i input.mp4 -c:v libx264 -c:a aac -f flv rtmp://server/live/key
```

## 常用参数说明

| 参数 | 说明 |
| --- | --- |
| `-c:v` / `-vcodec` | 视频编码器 |
| `-c:a` / `-acodec` | 音频编码器 |
| `-c copy` | 不重新编码（直接拷贝） |
| `-crf` | 质量控制（0-51，越小越好，23 为默认） |
| `-b:v` | 视频码率 |
| `-b:a` | 音频码率 |
| `-r` | 帧率 |
| `-s` | 分辨率（如 1280x720） |
| `-ss` | 起始时间 |
| `-to` | 结束时间 |
| `-t` | 持续时长 |
| `-an` | 去掉音频 |
| `-vn` | 去掉视频 |
| `-y` | 覆盖输出文件 |
| `-f` | 强制格式 |

---

> 返回 [第 18 章：回顾与展望](18-回顾与展望.md)
