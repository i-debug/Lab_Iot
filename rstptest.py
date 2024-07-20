import cv2
import numpy as np
import subprocess
import time

import os

# # 定义帧的宽度、高度和帧率
# frame_width = 640
# frame_height = 480
# frame_rate = 10
#
# # FFmpeg命令，用于将视频推送到RTSP服务器
# ffmpeg_command = [
#     'ffmpeg',
#     '-re',  # 以实时速度读入
#     '-f', 'rawvideo',  # 输入格式为原始视频数据
#     '-pix_fmt', 'bgr24',  # 输入像素格式
#     '-s', f'{frame_width}x{frame_height}',  # 输入视频尺寸
#     '-r', str(frame_rate),  # 输入帧率
#     '-i', '-',  # 从标准输入读入
#     '-c:v', 'libx264',  # 使用H.264编码器
#     '-f', 'rtsp',  # 输出格式为RTSP
#     'rtsp://localhost:8554/mystream'  # RTSP服务器地址
# ]
#
#
# # 启动FFmpeg进程
# ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE)
#
# try:
#     while True:
#         # 生成一帧随机图像
#         frame = np.random.randint(0, 255, (frame_height, frame_width, 3), dtype=np.uint8)
#
#         # 在此处可以添加代码生成实际图像帧
#         # 例如，可以绘制文本或图形：
#         # cv2.putText(frame, 'Hello, 111!', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
#
#         # 将帧写入FFmpeg进程的标准输入
#         ffmpeg_process.stdin.write(frame.tobytes())
#
# except KeyboardInterrupt:
#     # 捕获Ctrl+C终止进程
#     ffmpeg_process.stdin.close()
#     ffmpeg_process.wait()


# frame_width = 800
# frame_height = 600
# frame_rate = 15
# delay = 1 / frame_rate  # 计算帧间延迟
#
# # 定义 FFmpeg 命令
# ffmpeg_command = [
#     'ffmpeg',
#     '-re',  # 以实时速度读入
#     '-f', 'rawvideo',  # 输入格式为原始视频数据
#     '-pix_fmt', 'bgr24',  # 输入像素格式
#     '-s', f'{frame_width}x{frame_height}',  # 输入视频尺寸
#     '-r', str(frame_rate),  # 输入帧率
#     '-i', '-',  # 从标准输入读入
#     '-c:v', 'libx264',  # 使用H.264编码器
#     '-f', 'rtsp',  # 输出格式为RTSP
#     'rtsp://localhost:8554/mystream'  # RTSP服务器地址
# ]
#
# # 启动 FFmpeg 进程
# ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE)
#
# # 指定图片文件夹路径
# image_folder = 'img/'
#
# try:
#     while True:
#         # 获取最新的图像文件
#         images = [f for f in sorted(os.listdir(image_folder)) if f.endswith('heatmap_nolabel.png')]
#         if not images:
#             print("No image files found. Waiting for images...")
#             time.sleep(1)
#             continue
#
#         for filename in images:
#             # 读取图片
#             image_path = os.path.join(image_folder, filename)
#             frame = cv2.imread(image_path)
#
#             # 检查图像尺寸是否一致
#             if frame.shape[1] != frame_width or frame.shape[0] != frame_height:
#                 print(
#                     f"Image {filename} has incorrect dimensions. Expected {frame_width}x{frame_height}, got {frame.shape[1]}x{frame.shape[0]}")
#                 continue
#
#             # 将帧写入 FFmpeg 进程的标准输入
#             ffmpeg_process.stdin.write(frame.tobytes())
#
#             # 控制帧率
#             time.sleep(delay)
#
# except KeyboardInterrupt:
#     # 捕获 Ctrl+C 终止进程
#     ffmpeg_process.stdin.close()
#     ffmpeg_process.wait()
# except Exception as e:
#     print(f"An error occurred: {e}")
#     ffmpeg_process.stdin.close()
#     ffmpeg_process.wait()


import cv2
# import ffmpeg

# 图片路径
image_path = 'img/heatmap_nolabel.png'

# 读取图片
image = cv2.imread(image_path)

if image is None:
    print("Error: Cannot read the image file")
    exit()

# 图片尺寸
height, width, _ = image.shape

# FFmpeg 推流设置
output_stream = 'rtsp://localhost:8554/mystream'
process = (
    ffmpeg
    .input('pipe:', format='rawvideo', pix_fmt='bgr24', s=f'{width}x{height}', r=15)
    .output(output_stream, vcodec='libx264', pix_fmt='yuv444p', format='rtsp')
    .global_args('-loglevel', 'error')
    .run_async(pipe_stdin=True)
)

# 将图片推流
try:
    while True:
        process.stdin.write(image.tobytes())
except KeyboardInterrupt:
    print("Stream interrupted by user")
finally:
    process.stdin.close()
    process.wait()
