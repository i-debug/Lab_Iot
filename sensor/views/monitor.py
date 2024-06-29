from collections import defaultdict
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse

# from LabIot.settings import BASE_DIR
from sensor.models import RSSI_Data
from django.views.decorators.csrf import csrf_exempt
import numpy as np
import io
from sensor.views.itu_indoor_path_loss import itu_indoor_path_loss_inverse
from sklearn.manifold import MDS
from sensor.models import Sensor_Data
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
import uuid
from django.conf import settings
import os


def merge_recent_data():
    # 获取最近500条数据
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

def find_matching_pairs(merged_data):
    # 用于存储匹配数据对
    matching_pairs = []
    data_dict = {(data['device_mac'], data['ap_mac']): data for data in merged_data}

    # 查找匹配数据对
    for data in merged_data:
        device_mac = data['device_mac']
        ap_mac = data['ap_mac']
        matching_key = (ap_mac, device_mac)

        if matching_key in data_dict and matching_key != (device_mac, ap_mac):
            pair = (data, data_dict[matching_key])
            if pair not in matching_pairs and (pair[1], pair[0]) not in matching_pairs:
                matching_pairs.append(pair)
                print(f"Match found: {data} <--> {data_dict[matching_key]}")  # 调试输出

    print(f"Total matching pairs: {len(matching_pairs)}")  # 调试输出
    return matching_pairs

def create_symmetric_matrix(size):
    # 创建对应尺寸的零矩阵
    matrix = np.zeros((size, size))
    # 对角线置空（置为 NaN 表示对角线为空）
    np.fill_diagonal(matrix, np.nan)
    # return matrix.tolist()
    return matrix


# def create_distance_matrix(data):
#     # Extract unique points
#     unique_points = set()
#     for pair in data:
#         unique_points.add(pair[0]['device_mac'])
#         unique_points.add(pair[0]['ap_mac'])
#
#     # Map each point to an index
#     point_to_index = {point: idx for idx, point in enumerate(unique_points)}
#
#     # Initialize a 4x4 matrix with zeros
#     num_points = len(unique_points)
#     distance_matrix = np.zeros((num_points, num_points))
#
#     # Fill the matrix with distances
#     for pair in data:
#         device_mac_1 = pair[0]['device_mac']
#         ap_mac_1 = pair[0]['ap_mac']
#         avg_rssi_1 = float(pair[0]['avg_rssi'])
#
#         device_mac_2 = pair[1]['device_mac']
#         ap_mac_2 = pair[1]['ap_mac']
#         avg_rssi_2 = float(pair[1]['avg_rssi'])
#
#         idx1 = point_to_index[device_mac_1]
#         idx2 = point_to_index[ap_mac_1]
#
#         distance_matrix[idx1, idx2] = avg_rssi_1
#         distance_matrix[idx2, idx1] = avg_rssi_2
#
#     return distance_matrix

def create_distance_matrix(data):
    # 提取唯一的点
    unique_points = set()
    for pair in data:
        unique_points.add(pair[0]['device_mac'])
        unique_points.add(pair[0]['ap_mac'])

    # 将每个点映射到一个索引
    point_to_index = {point: idx for idx, point in enumerate(unique_points)}

    # 初始化距离矩阵和 MAC 地址矩阵
    num_points = len(unique_points)
    distance_matrix = np.zeros((num_points, num_points))
    mac_matrix = np.empty((num_points, num_points), dtype=object)

    # 填充距离矩阵和 MAC 地址矩阵
    for pair in data:
        device_mac_1 = pair[0]['device_mac']
        ap_mac_1 = pair[0]['ap_mac']
        avg_rssi_1 = float(pair[0]['avg_rssi'])

        device_mac_2 = pair[1]['device_mac']
        ap_mac_2 = pair[1]['ap_mac']
        avg_rssi_2 = float(pair[1]['avg_rssi'])

        idx1 = point_to_index[device_mac_1]
        idx2 = point_to_index[ap_mac_1]

        distance_matrix[idx1, idx2] = avg_rssi_1
        mac_matrix[idx1, idx2] = device_mac_1

        distance_matrix[idx2, idx1] = avg_rssi_2
        mac_matrix[idx2, idx1] = device_mac_2

    return distance_matrix, mac_matrix

def symmetrize_matrix(matrix):
    n = len(matrix)
    sym_matrix = np.array(matrix, dtype=float)  # 将输入矩阵转为numpy数组，确保计算方便且为浮点数

    for i in range(n):
        for j in range(i + 1, n):
            avg = (sym_matrix[i, j] + sym_matrix[j, i]) / 2
            sym_matrix[i, j] = avg
            sym_matrix[j, i] = avg

    return sym_matrix


def convert_loss_matrix_to_distance_matrix(loss_matrix, freq, pathlossindex, walllosses):
    # 获取矩阵的维度
    rows, cols = loss_matrix.shape
    # 初始化距离矩阵
    distance_matrix = np.zeros((rows, cols))

    for i in range(rows):
        for j in range(cols):
            if i != j:
                # 非对角线元素调用 itu_indoor_path_loss_inverse 转换成距离
                distance_matrix[i, j] = "{:.2f}".format(itu_indoor_path_loss_inverse(loss_matrix[i, j], freq, pathlossindex, walllosses))
            else:
                # 对角线元素保持不变（通常为零）
                distance_matrix[i, j] = 0

    return distance_matrix

def get_latest_temperature_for_device_mac(device_mac):
    """
    查找给定device_mac的最新温度数据
    :param device_mac: 设备的MAC地址
    :return: 最新的温度数据，如果没有数据则返回None
    """
    latest_data = Sensor_Data.objects.filter(device_mac=device_mac).order_by('-timestamp').first()
    if latest_data:
        return latest_data.temperature
    return None

def transform_mac_matrix_to_temperature_matrix(mac_matrix):
    """
    将device_mac矩阵转化为温度矩阵
    :param mac_matrix: 包含device_mac地址的二维列表
    :return: 转化后的温度矩阵
    """
    temperature_matrix = []
    for row in mac_matrix:
        temperature_row = []
        for mac in row:
            temperature = get_latest_temperature_for_device_mac(mac)
            temperature_row.append(temperature if temperature is not None else 0.0)  # 如果找不到数据则填0.0
        temperature_matrix.append(temperature_row)
    return temperature_matrix

# @csrf_exempt
def get_matching_data(request):
    merged_data = merge_recent_data()
    matching_pairs = find_matching_pairs(merged_data)
    print(matching_pairs)
    # 确定对称矩阵的大小
    matrix_size = int(np.ceil(np.sqrt(len(matching_pairs) * 2)))
    # 创建对称矩阵
    rssi_matrix = create_symmetric_matrix(matrix_size)
    mac_matrix = create_symmetric_matrix(matrix_size)

    # 填入数据对
    rssi_matrix, mac_matrix = create_distance_matrix(matching_pairs)
    print(rssi_matrix)
    print(mac_matrix)

    symmetric_matrix = -symmetrize_matrix(rssi_matrix)
    distance_matrix = convert_loss_matrix_to_distance_matrix(symmetric_matrix, 2400, 10, 10)
    temperature_matrix = transform_mac_matrix_to_temperature_matrix(mac_matrix)
    print(symmetric_matrix)
    print(distance_matrix)
    print(temperature_matrix)

    mds = MDS(n_components=2, dissimilarity='precomputed', random_state=0)
    restored_points = mds.fit_transform(distance_matrix)
    print(restored_points)
    plt.scatter(restored_points[:, 0], restored_points[:, 1], color='red')
    plt.show()
    grid_x, grid_y = np.mgrid[0:3:500j, 0:2:500j]
    values = [30, 31.9, 31.5, 31.2, 32.1, 33.3]

    # 插值方法：'nearest', 'linear', 'cubic'
    method = 'cubic'
    grid_z = griddata(restored_points, values, (grid_x, grid_y), method=method)
    #
    # 创建热图
    plt.figure(figsize=(10, 6))
    plt.imshow(grid_z.T, extent=(-50, 50, -30, 30), origin='lower', cmap='jet')
    plt.colorbar()
    # buf = io.BytesIO()
    # plt.savefig(buf, format='png')
    # buf.seek(0)
    # BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # media_dir = os.path.join(BASE_DIR, 'sensor/media')  # 假设 BASE_DIR 是你项目的根目录
    # if not os.path.exists(media_dir):
    #     os.makedirs(media_dir)  # 如果目录不存在，则创建它
    media_dir = "D:/Project/LabIot/sensor/media"
    image_path = os.path.join(media_dir, 'generated_image.png')

    plt.savefig(image_path)
    plt.close()  # 关闭图形，释放资源

    # 将BytesIO中的图像数据返回给模板渲染
    generated_image_url = image_path
    context = {
        'generated_image_url': generated_image_url,
    }
    return render(request, 'monitortemp.html', context)




