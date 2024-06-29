import numpy as np

frequency = 2400  # 使用的频率（MHz）
path_loss_index = 3  # 路径损耗指数(ITU模型定义)
wall_losses_index = 5

def itu_indoor_path_loss_inverse(pathloss, freq, pathlossindex, walllosses):
    """
    使用ITU-R P.1238室内传播模型的逆向函数计算距离
    参数:
    pathloss (float): 路径损耗，单位dB
    freq (float): 频率，单位MHz
    pathlossindex (float): 路径损耗指数
    walllosses (float): 障碍物损耗，单位dB
    返回:
    float: 距离，单位米
    """
    log_distance = (pathloss + 28 - walllosses - 20 * np.log10(freq)) / pathlossindex
    distance = 10 ** log_distance

    return distance
def convert_loss_matrix_to_distance_matrix(loss_matrix, freq, pathlossindex, walllosses):
    """
    将损耗矩阵中除对角线外的元素转换为距离矩阵
    参数:
    loss_matrix (np.array): 损耗矩阵
    freq (float): 频率，单位MHz
    pathlossindex (float): 路径损耗指数
    walllosses (float): 障碍物损耗，单位dB
    返回:
    np.array: 距离矩阵
    """
    # 获取矩阵的维度
    rows, cols = loss_matrix.shape
    # 初始化距离矩阵
    distance_matrix = np.zeros((rows, cols))

    for i in range(rows):
        for j in range(cols):
            if i != j:
                # 非对角线元素调用 itu_indoor_path_loss_inverse 转换成距离
                distance_matrix[i, j] = itu_indoor_path_loss_inverse(loss_matrix[i, j], freq, pathlossindex, walllosses)
            else:
                # 对角线元素保持不变（通常为零）
                distance_matrix[i, j] = 0

    return distance_matrix


# 示例调用
loss_matrix = np.array([
    [0, 50, 70],
    [50, 0, 60],
    [70, 60, 0]
])

freq = 2400  # 频率，单位MHz
pathlossindex = 10  # 路径损耗指数
walllosses = 5  # 障碍物损耗，单位dB

distance_matrix = convert_loss_matrix_to_distance_matrix(loss_matrix, freq, pathlossindex, walllosses)
print(distance_matrix)
