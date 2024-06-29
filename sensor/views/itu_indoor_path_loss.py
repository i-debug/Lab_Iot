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