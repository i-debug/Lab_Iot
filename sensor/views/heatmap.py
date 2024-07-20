from collections import defaultdict
from django.http import JsonResponse, FileResponse, HttpResponseNotFound
from sensor.models import RSSI_Data, Sensor_Data
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import numpy as np
from sensor.views.itu_indoor_path_loss import itu_indoor_path_loss_inverse
from sklearn.manifold import MDS
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
import os
from rest_framework.decorators import api_view
from django.shortcuts import render
import threading
import time
import requests
import json
import subprocess
import cv2


# 根据mac从数据库中读取temp
def get_temp_for_dev_mac(dev_mac):

    latest_data = Sensor_Data.objects.filter(device_mac=dev_mac).order_by('-timestamp').first()
    if latest_data:
        return latest_data.temperature
    return 30.0


def get_smoke_for_dev_mac(dev_mac):

    latest_data = Sensor_Data.objects.filter(device_mac=dev_mac).order_by('-timestamp').first()
    if latest_data:
        return latest_data.smoke
    return 1024


def get_hydrogen_for_dev_mac(dev_mac):

    latest_data = Sensor_Data.objects.filter(device_mac=dev_mac).order_by('-timestamp').first()
    if latest_data:
        return latest_data.hydrogen
    return 1024


def get_co_for_dev_mac(dev_mac):

    latest_data = Sensor_Data.objects.filter(device_mac=dev_mac).order_by('-timestamp').first()
    if latest_data:
        return latest_data.co
    return 1024


# 获取最近2500条数据,将重复数据平均化合并,return数据,print尺寸
def merge_data():
    # 获取最近2500条数据
    recent_data = RSSI_Data.objects.order_by('-timestamp')[:2500]

    # 用于存储匹配的 device_mac 和 ap_mac 及其对应的 rssi 值
    data_dict = defaultdict(list)

    for data in recent_data:
        key = (data.device_mac, data.ap_mac)
        data_dict[key].append(data.rssi)

    # 处理重复项，计算rssi的平均值
    merged_data = []
    for (device_mac, ap_mac), rssi_values in data_dict.items():
        origin_avg_rssi = sum(rssi_values) / len(rssi_values)
        avg_rssi = "{:.2f}".format(origin_avg_rssi)
        merged_data.append({
            'device_mac': device_mac,
            'ap_mac': ap_mac,
            'avg_rssi': avg_rssi
        })

    return merged_data


# 求出匹配的数据对,return数据
def matching_pairs(merged_data):
    # 用于存储匹配数据对
    matched_pairs = []
    data_dict = {(data['device_mac'], data['ap_mac']): data for data in merged_data}

    # 查找匹配数据对
    for data in merged_data:
        device_mac = data['device_mac']
        ap_mac = data['ap_mac']
        matching_key = (ap_mac, device_mac)

        if matching_key in data_dict and matching_key != (device_mac, ap_mac):
            pair = (data, data_dict[matching_key])
            if pair not in matched_pairs and (pair[1], pair[0]) not in matched_pairs:
                matched_pairs.append(pair)

    return matched_pairs


# 根据dev_mac 添加对应的temp值
def add_temp(matched_pairs):
    # 计算总行数
    num_rows = len(matched_pairs) * len(matched_pairs[0])
    num_cols = len(matched_pairs[0][0]) + 1

    # 创建一个空的2维数组
    origin_array = np.empty((num_rows, num_cols), dtype=object)

    row_index = 0
    for group in matched_pairs:

        for d in group:
            origin_array[row_index, 0] = str(d['device_mac'])
            origin_array[row_index, 1] = str(d['ap_mac'])
            origin_array[row_index, 2] = str(d['avg_rssi'])
            origin_array[row_index, 3] = get_temp_for_dev_mac(str(d['device_mac']))
            row_index += 1

    return origin_array


def add_smoke(matched_pairs):
    # 计算总行数
    num_rows = len(matched_pairs) * len(matched_pairs[0])
    num_cols = len(matched_pairs[0][0]) + 1

    # 创建一个空的2维数组
    origin_array = np.empty((num_rows, num_cols), dtype=object)

    row_index = 0
    for group in matched_pairs:

        for d in group:
            origin_array[row_index, 0] = str(d['device_mac'])
            origin_array[row_index, 1] = str(d['ap_mac'])
            origin_array[row_index, 2] = str(d['avg_rssi'])
            origin_array[row_index, 3] = get_smoke_for_dev_mac(str(d['device_mac']))
            row_index += 1

    return origin_array


def add_hydrogen(matched_pairs):
    # 计算总行数
    num_rows = len(matched_pairs) * len(matched_pairs[0])
    num_cols = len(matched_pairs[0][0]) + 1

    # 创建一个空的2维数组
    origin_array = np.empty((num_rows, num_cols), dtype=object)

    row_index = 0
    for group in matched_pairs:

        for d in group:
            origin_array[row_index, 0] = str(d['device_mac'])
            origin_array[row_index, 1] = str(d['ap_mac'])
            origin_array[row_index, 2] = str(d['avg_rssi'])
            origin_array[row_index, 3] = get_hydrogen_for_dev_mac(str(d['device_mac']))
            row_index += 1

    return origin_array


def add_co(matched_pairs):
    # 计算总行数
    num_rows = len(matched_pairs) * len(matched_pairs[0])
    num_cols = len(matched_pairs[0][0]) + 1

    # 创建一个空的2维数组
    origin_array = np.empty((num_rows, num_cols), dtype=object)

    row_index = 0
    for group in matched_pairs:

        for d in group:
            origin_array[row_index, 0] = str(d['device_mac'])
            origin_array[row_index, 1] = str(d['ap_mac'])
            origin_array[row_index, 2] = str(d['avg_rssi'])
            origin_array[row_index, 3] = get_co_for_dev_mac(str(d['device_mac']))
            row_index += 1

    return origin_array


# 给每个mac地址生成序号,return字典
def mac_serial_dict(origin_4d_array):
    serial_number_dict = {}
    unique_device_macs = set(origin_4d_array[:, 0])  # 获取唯一的device_mac

    for index, device_mac in enumerate(unique_device_macs, start=1):
        serial_number_dict[index] = device_mac

    return serial_number_dict


# 根据字典，把数组中的 mac地址替换为序号
def replace_mac_with_serial(origin_array, serial_number_dict):
    # 创建一个新数组，尺寸与输入数组相同
    serial_array = np.copy(origin_array)

    # 创建反向字典，以便通过MAC地址快速查找序号
    reverse_dict = {v: k for k, v in serial_number_dict.items()}

    # 替换数组中的MAC地址为对应的序号
    for i in range(serial_array.shape[0]):
        device_mac = serial_array[i, 0]
        ap_mac = serial_array[i, 1]
        if device_mac in reverse_dict:
            serial_array[i, 0] = reverse_dict[device_mac]
        if ap_mac in reverse_dict:
            serial_array[i, 1] = reverse_dict[ap_mac]

    return serial_array


# 将rssi通过itu衰减模型转换为距离
def serial_distance_values(serial_array):
    # 创建一个新数组，尺寸与输入数组相同
    serial_distance_array = np.copy(serial_array)

    # 处理第三列的RSSI值
    for i in range(serial_distance_array.shape[0]):
        rssi_value = float(serial_distance_array[i, 2])  # 将RSSI值转换为浮点数
        pathloss = -rssi_value
        processed_rssi_value = itu_indoor_path_loss_inverse(pathloss)
        serial_distance_array[i, 2] = str(processed_rssi_value)  # 将处理后的RSSI值转换回字符串

    return serial_distance_array


# 将distance按顺序填入矩阵
def fill_rssi_matrix(serial_distance_array):
    # 确定矩阵的大小
    max_serial_number = int(np.max(serial_distance_array[:, :2].astype(int)))
    mds_matrix = np.empty((max_serial_number, max_serial_number), dtype=object)
    mds_matrix[:] = np.nan  # 使用NaN初始化

    # 填充RSSI矩阵
    for row in serial_distance_array:
        i = int(row[0]) - 1  # 序号减1以适应矩阵索引
        j = int(row[1]) - 1  # 序号减1以适应矩阵索引
        mds_matrix[i, j] = row[2]

    return mds_matrix


# 将矩阵对称化
def symmetrize_matrix(mds_matrix):
    # 将输入的列表转换为NumPy数组
    mds_matrix = np.array(mds_matrix, dtype=np.float64)

    # 将NaN值替换为0
    mds_matrix = np.nan_to_num(mds_matrix)

    # 对矩阵进行对称化
    symmetric_matrix = (mds_matrix + mds_matrix.T) / 2

    return symmetric_matrix


# mds处理
def mdsprocess(symmetric_matrix):
    mds = MDS(n_components=2, dissimilarity='precomputed', random_state=0)
    restored_points = mds.fit_transform(symmetric_matrix)
    return restored_points


# 将mds输出点和温度生成矩阵
def coordinates_temp(restored_points, serial_distance_array):
    serial_number_dict = mac_serial_dict(serial_distance_array)
    latest_data_dict = {serial_number: [] for serial_number in serial_number_dict.keys()}

    for row in serial_distance_array:
        serial_number = int(row[0])
        latest_data = row[3]
        if serial_number in latest_data_dict:
            latest_data_dict[serial_number].append(latest_data)

    combined_array = np.empty((restored_points.shape[0], 3), dtype=object)
    for i, coord in enumerate(restored_points):
        combined_array[i, 0] = coord[0]  # x坐标
        combined_array[i, 1] = coord[1]  # y坐标
        combined_array[i, 2] = latest_data_dict[i + 1][0] if latest_data_dict[i + 1] else "No data"

    return combined_array


# 根据矩阵生成nolabel温度热力图,AI识别用
def generate_heatmap_nolabel(combined_array):

    # 过滤掉包含None的条目并转换Decimal为浮点数
    filtered_array = [point for point in combined_array if point[2] is not None]
    x = np.array([point[0] for point in filtered_array])
    y = np.array([point[1] for point in filtered_array])
    z = np.array([float(point[2]) for point in filtered_array])  # 转换Decimal为浮点数

    # 计算值的平均值，并保留一位小数
    mean_value = round(np.mean(z), 1)

    # 找到坐标的最小和最大值
    x_min, x_max = x.min(), x.max()
    y_min, y_max = y.min(), y.max()

    # 生成四个角点
    corner_points = np.array([
        [x_min, y_min, mean_value],
        [x_max, y_min, mean_value],
        [x_min, y_max, mean_value],
        [x_max, y_max, mean_value]
    ])

    # 将角点添加到原数据集中
    x = np.append(x, corner_points[:, 0])
    y = np.append(y, corner_points[:, 1])
    z = np.append(z, corner_points[:, 2])

    # 定义插值网格
    xi = np.linspace(x.min() - 0.1 * abs(x.max() - x.min()), x.max() + 0.1 * abs(x.max() - x.min()), 300)
    yi = np.linspace(y.min() - 0.1 * abs(y.max() - y.min()), y.max() + 0.1 * abs(y.max() - y.min()), 300)
    xi, yi = np.meshgrid(xi, yi)

    # 使用 cubic 插值算法
    zi = griddata((x, y), z, (xi, yi), method='cubic')

    # 创建热图
    plt.figure(figsize=(8, 6))
    plt.imshow(zi, extent=(x.min() - 0.1 * abs(x.max() - x.min()), x.max() + 0.1 * abs(x.max() - x.min()),
                           y.min() - 0.1 * abs(y.max() - y.min()), y.max() + 0.1 * abs(y.max() - y.min())),
               origin='lower', cmap='jet', alpha=0.6)

    # 保存图片到img文件夹
    img_dir = os.path.join(os.getcwd(), 'img')
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    # 调试信息
    # print(f"Saving heatmap to {os.path.join(img_dir, 'heatmap_nolabel_01.png')}")

    plt.savefig(os.path.join(img_dir, 'heatmap_nolabel.png'))
    plt.close()  # 关闭图形以释放内存
    # plt.show()


# 根据矩阵生成热力图，前端用
def generate_heatmap(combined_array, datatype):
    # 默认值
    imglabel = "默认标签"
    filename = "default_heatmap.png"

    if datatype == "add_temp":
        imglabel = "温度(°C)"
        filename = "heatmap.png"
        print("生成温度热力图")
    elif datatype == 'add_smoke':
        imglabel = "烟雾浓度"
        filename = "smokemap.png"
    elif datatype == 'add_hydrogen':
        imglabel = "氢气浓度"
        filename = "hydrogenmap.png"
    elif datatype == 'add_co':
        imglabel = "一氧化碳浓度"
        filename = "comap.png"
    else:
        print("无效的datatype")

    # 过滤掉包含None的条目并转换Decimal为浮点数
    filtered_array = [point for point in combined_array if point[2] is not None]
    x = np.array([point[0] for point in filtered_array])
    y = np.array([point[1] for point in filtered_array])
    z = np.array([float(point[2]) for point in filtered_array])  # 转换Decimal为浮点数

    # 计算值的平均值，并保留一位小数
    mean_value = round(np.mean(z), 1)

    # 找到坐标的最小和最大值
    x_min, x_max = x.min(), x.max()
    y_min, y_max = y.min(), y.max()

    # 生成四个角点
    corner_points = np.array([
        [x_min, y_min, mean_value],
        [x_max, y_min, mean_value],
        [x_min, y_max, mean_value],
        [x_max, y_max, mean_value]
    ])

    # 将角点添加到原数据集中
    x = np.append(x, corner_points[:, 0])
    y = np.append(y, corner_points[:, 1])
    z = np.append(z, corner_points[:, 2])

    # 定义插值网格
    xi = np.linspace(x.min() - 0.1 * abs(x.max() - x.min()), x.max() + 0.1 * abs(x.max() - x.min()), 300)
    yi = np.linspace(y.min() - 0.1 * abs(y.max() - y.min()), y.max() + 0.1 * abs(y.max() - y.min()), 300)
    xi, yi = np.meshgrid(xi, yi)

    # 使用 cubic 插值算法
    zi = griddata((x, y), z, (xi, yi), method='cubic')

    plt.rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

    # 创建热图
    plt.figure(figsize=(10, 10))
    plt.imshow(zi, extent=(x.min() - 0.1 * abs(x.max() - x.min()), x.max() + 0.1 * abs(x.max() - x.min()),
                           y.min() - 0.1 * abs(y.max() - y.min()), y.max() + 0.1 * abs(y.max() - y.min())),
               origin='lower', cmap='jet', alpha=0.6)
    plt.colorbar(label=imglabel, orientation='horizontal')

    # 创建散点图
    plt.scatter(x, y, c='red', edgecolor='k', s=10)

    # 添加标注
    for i, txt in enumerate(z):
        plt.annotate(txt, (x[i], y[i]), fontsize=12, ha='right')

    plt.title('')

    # 保存图片到img文件夹
    img_dir = os.path.join(os.getcwd(), 'img')
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    # 调试信息
    print(f"Saving map to {os.path.join(img_dir, filename)}")

    plt.savefig(os.path.join(img_dir, filename))
    plt.show()
    plt.close()  # 关闭图形以释放内存


# 调用函数绘图nolabel
def get_heatmap_nolabel():
    while True:
        merged_data = merge_data()
        matching_pair = matching_pairs(merged_data)
        origin_4d_array = add_temp(matching_pair)
        mac_dict = mac_serial_dict(origin_4d_array)
        serial_array = replace_mac_with_serial(origin_4d_array, mac_dict)
        distance_array = serial_distance_values(serial_array)
        mds_array = fill_rssi_matrix(distance_array)
        symmetric_matrix = symmetrize_matrix(mds_array)
        restored_points = mdsprocess(symmetric_matrix)
        combined_array = coordinates_temp(restored_points, serial_array)
        generate_heatmap_nolabel(combined_array)

        time.sleep(5)


threading.Thread(target=get_heatmap_nolabel, daemon=True).start()

# 给rest驱动post数据
# def generate_and_post_json():
#     while True:
#         # 生成数据的代码
#         merged_data = merge_data()
#         matching_pair = matching_pairs(merged_data)
#         origin_4d_array = add_temp(matching_pair)
#         mac_dict = mac_serial_dict(origin_4d_array)
#         serial_array = replace_mac_with_serial(origin_4d_array, mac_dict)
#         distance_array = serial_distance_values(serial_array)
#         mds_array = fill_rssi_matrix(distance_array)
#         symmetric_matrix = symmetrize_matrix(mds_array)
#         restored_points = mdsprocess(symmetric_matrix)
#         combined_array = coordinates_temp(restored_points, serial_array)
#
#         json_data = {'data': combined_array.tolist()}
#
#         # POST数据到指定URL
#         try:
#             response = requests.post('http://192.168.1.58:59986/api/v2/resource/device-rest/json', json=json_data)
#             response.raise_for_status()
#         except requests.exceptions.RequestException as e:
#             print(f"Error posting data: {e}")
#
#         # 等待5秒钟
#         time.sleep(5)
#
#
# # 启动后台线程
# threading.Thread(target=generate_and_post_json, daemon=True).start()


# restful API,GET拿到combined_array数据
@api_view(['GET'])
def get_heatmap_json(request):

    merged_data = merge_data()
    matching_pair = matching_pairs(merged_data)
    origin_4d_array = add_temp(matching_pair)
    mac_dict = mac_serial_dict(origin_4d_array)
    serial_array = replace_mac_with_serial(origin_4d_array, mac_dict)
    distance_array = serial_distance_values(serial_array)
    mds_array = fill_rssi_matrix(distance_array)
    symmetric_matrix = symmetrize_matrix(mds_array)
    restored_points = mdsprocess(symmetric_matrix)
    combined_array = coordinates_temp(restored_points, serial_array)

    return JsonResponse({'data': combined_array.tolist()})


# 前端页面绘图函数
@api_view(['GET'])
def get_heatmap_img(request):
    merged_data = merge_data()
    matching_pair = matching_pairs(merged_data)
    origin_4d_array = add_temp(matching_pair)
    mac_dict = mac_serial_dict(origin_4d_array)
    serial_array = replace_mac_with_serial(origin_4d_array, mac_dict)
    distance_array = serial_distance_values(serial_array)
    mds_array = fill_rssi_matrix(distance_array)
    symmetric_matrix = symmetrize_matrix(mds_array)
    restored_points = mdsprocess(symmetric_matrix)
    combined_array = coordinates_temp(restored_points, serial_array)
    generate_heatmap(combined_array, "add_temp")
    generate_heatmap_nolabel(combined_array)
    img_dir = os.path.join(settings.BASE_DIR, 'img')
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    img_path = os.path.join(img_dir, 'heatmap.png')
    if os.path.exists(img_path):
        # Assuming the image is stored in the 'img' folder under the root directory
        img_url = '/img/heatmap.png'

        return render(request, 'monitortemp.html', {'img_url': img_url})
    else:
        return HttpResponseNotFound('Image not found')

# 前端页面绘图函数
@api_view(['GET'])
def get_smokemap_img(request):
    merged_data = merge_data()
    matching_pair = matching_pairs(merged_data)
    origin_4d_array = add_smoke(matching_pair)
    mac_dict = mac_serial_dict(origin_4d_array)
    serial_array = replace_mac_with_serial(origin_4d_array, mac_dict)
    distance_array = serial_distance_values(serial_array)
    mds_array = fill_rssi_matrix(distance_array)
    symmetric_matrix = symmetrize_matrix(mds_array)
    restored_points = mdsprocess(symmetric_matrix)
    combined_array = coordinates_temp(restored_points, serial_array)
    generate_heatmap(combined_array, "add_smoke")
    generate_heatmap_nolabel(combined_array)
    img_dir = os.path.join(settings.BASE_DIR, 'img')
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    img_path = os.path.join(img_dir, 'smokemap.png')
    if os.path.exists(img_path):
        # Assuming the image is stored in the 'img' folder under the root directory
        img_url = '/img/smokemap.png'

        return render(request, 'monitorsmoke.html', {'img_url': img_url})
    else:
        return HttpResponseNotFound('Image not found')

# 前端页面绘图函数
@api_view(['GET'])
def get_hydrogenmap_img(request):
    merged_data = merge_data()
    matching_pair = matching_pairs(merged_data)
    origin_4d_array = add_hydrogen(matching_pair)
    mac_dict = mac_serial_dict(origin_4d_array)
    serial_array = replace_mac_with_serial(origin_4d_array, mac_dict)
    distance_array = serial_distance_values(serial_array)
    mds_array = fill_rssi_matrix(distance_array)
    symmetric_matrix = symmetrize_matrix(mds_array)
    restored_points = mdsprocess(symmetric_matrix)
    combined_array = coordinates_temp(restored_points, serial_array)
    generate_heatmap(combined_array, "add_hydrogen")
    generate_heatmap_nolabel(combined_array)
    img_dir = os.path.join(settings.BASE_DIR, 'img')
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    img_path = os.path.join(img_dir, 'hydrogenmap.png')
    if os.path.exists(img_path):
        # Assuming the image is stored in the 'img' folder under the root directory
        img_url = '/img/hydrogenmap.png'

        return render(request, 'monitorhydrogen.html', {'img_url': img_url})
    else:
        return HttpResponseNotFound('Image not found')

# 前端页面绘图函数
@api_view(['GET'])
def get_comap_img(request):
    merged_data = merge_data()
    matching_pair = matching_pairs(merged_data)
    origin_4d_array = add_co(matching_pair)
    mac_dict = mac_serial_dict(origin_4d_array)
    serial_array = replace_mac_with_serial(origin_4d_array, mac_dict)
    distance_array = serial_distance_values(serial_array)
    mds_array = fill_rssi_matrix(distance_array)
    symmetric_matrix = symmetrize_matrix(mds_array)
    restored_points = mdsprocess(symmetric_matrix)
    combined_array = coordinates_temp(restored_points, serial_array)
    generate_heatmap(combined_array, "add_co")
    generate_heatmap_nolabel(combined_array)
    img_dir = os.path.join(settings.BASE_DIR, 'img')
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)

    img_path = os.path.join(img_dir, 'comap.png')
    if os.path.exists(img_path):
        # Assuming the image is stored in the 'img' folder under the root directory
        img_url = '/img/comap.png'

        return render(request, 'monitorco.html', {'img_url': img_url})
    else:
        return HttpResponseNotFound('Image not found')

# def img_rtsp():
#     frame_width = 800
#     frame_height = 600
#     frame_rate = 15
#     delay = 1 / frame_rate  # 计算帧间延迟
#
#     # 定义 FFmpeg 命令
#     ffmpeg_command = [
#         'ffmpeg',
#         '-re',  # 以实时速度读入
#         '-f', 'rawvideo',  # 输入格式为原始视频数据
#         '-pix_fmt', 'bgr24',  # 输入像素格式
#         '-s', f'{frame_width}x{frame_height}',  # 输入视频尺寸
#         '-r', str(frame_rate),  # 输入帧率
#         '-i', '-',  # 从标准输入读入
#         '-c:v', 'libx264',  # 使用H.264编码器
#         '-f', 'rtsp',  # 输出格式为RTSP
#         'rtsp://localhost:8554/mystream'  # RTSP服务器地址
#     ]
#
#     # 启动 FFmpeg 进程
#     ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE)
#
#     # 指定图片文件夹路径
#     image_folder = 'img/'
#
#     try:
#         while True:
#             # 获取最新的图像文件
#             images = [f for f in sorted(os.listdir(image_folder)) if f.endswith('heatmap_nolabel.png')]
#             if not images:
#                 print("No image files found. Waiting for images...")
#                 time.sleep(1)
#                 continue
#
#             for filename in images:
#                 # 读取图片
#                 image_path = os.path.join(image_folder, filename)
#                 frame = cv2.imread(image_path)
#
#                 # 检查图像尺寸是否一致
#                 if frame.shape[1] != frame_width or frame.shape[0] != frame_height:
#                     print(f"Image {filename} has incorrect dimensions. Expected {frame_width}x{frame_height}, got {frame.shape[1]}x{frame.shape[0]}")
#                     continue
#
#                 # 将帧写入 FFmpeg 进程的标准输入
#                 ffmpeg_process.stdin.write(frame.tobytes())
#
#                 # 控制帧率
#                 time.sleep(delay)
#
#     except KeyboardInterrupt:
#         # 捕获 Ctrl+C 终止进程
#         ffmpeg_process.stdin.close()
#         ffmpeg_process.wait()
#     except Exception as e:
#         print(f"An error occurred: {e}")
#         ffmpeg_process.stdin.close()
#         ffmpeg_process.wait()
#
# img_rtsp()