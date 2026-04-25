"""
无人机系统状态机模块
管理无人机在不同工作状态之间的切换和行为控制
"""

from typing import Dict, Tuple, Optional

class DroneSystemState:
    """无人机系统状态机"""
    
    def __init__(self):
        """初始化无人机系统状态"""
        self.state = "SEARCH"  # 初始状态：搜索模式
        self.current_position = (0, 0, 10)  # 当前三维坐标 (x, y, 高度)，单位：米
        self.damage_center = None  # 检测到的车损中心点坐标（归一化）
        self.inspection_count = 0  # 勘察次数计数器
        self.max_inspection_steps = 5  # 最大勘察步数限制
        
    def update_state(self, new_state):
        """
        更新系统状态
        参数:
            new_state: 新的状态名称（如 "SEARCH", "INSPECTION"）
        """
        print(f"状态切换：{self.state} -> {new_state}")
        self.state = new_state
        
    def search_mode(self, image_path):
        """
        搜索模式：检测当前图像中是否有车损
        参数:
            image_path: 待检测的图像路径
        返回:
            tuple: (has_damage: 是否发现车损，damage_info: 车损信息)
        """
        from yolo_service import get_damage_center_for_llm
        
        damage_info = get_damage_center_for_llm(image_path, conf_thres=0.5)
        
        if damage_info:
            print(f"搜索模式：发现车损！置信度：{damage_info['confidence']:.3f}")
            print(f"车损中心位置：{damage_info['center_norm']}")
            self.damage_center = damage_info['center_norm']
            return True, damage_info
        else:
            print("搜索模式：未发现车损，继续搜索...")
            return False, None
    
    def inspection_mode(self, image_path, damage_center):
        """
        勘察模式：基于车损位置生成无人机调整指令
        参数:
            image_path: 当前拍摄的图像路径
            damage_center: 车损中心点坐标（归一化）
        返回:
            tuple: (instruction: 调整指令，should_continue: 是否继续勘察)
        """
        self.inspection_count += 1
        
        # 使用本地规则引擎生成指令
        instruction = self._generate_adjustment_instruction(damage_center)
        
        print(f"勘察模式 第{self.inspection_count}步：{instruction}")
        
        # 检查是否完成勘察（车损已居中或达到最大步数）
        if self._is_inspection_complete(damage_center) or self.inspection_count >= self.max_inspection_steps:
            print("勘察完成！")
            return instruction, False
        else:
            return instruction, True
    
    def _generate_adjustment_instruction(self, damage_center):
        """
        生成调整指令（本地规则引擎），支持多轴同时移动
        参数:
            damage_center: 车损中心点坐标（归一化）(x_norm, y_norm)
        返回:
            dict: 包含动作类型、各轴速度和原因的指令字典
        """
        x_norm, y_norm = damage_center
        
        # 计算偏差
        dx = x_norm - 0.5  # x方向偏差 (-0.5 到 0.5)
        dy = y_norm - 0.5  # y方向偏差 (-0.5 到 0.5)
        
        # 设置最大和最小速度（米/秒）
        max_speed = 2.0
        min_speed = 0.2
        k = 0.05
        # 计算各轴速度，根据偏差大小调整速度
        speed_x = max(min(abs(dx) * k, max_speed), min_speed) if abs(dx) > 0.05 else 0
        speed_y = max(min(abs(dy) * k, max_speed), min_speed) if abs(dy) > 0.05 else 0
        
        # 确定移动方向
        direction_x = "右" if dx > 0 else "左" if dx < 0 else ""
        direction_y = "上" if dy > 0 else "下" if dy < 0 else ""
        
        # 组合方向描述
        directions = []
        if direction_x: directions.append(direction_x)
        if direction_y: directions.append(direction_y)
        
        if directions:
            action_desc = "".join(directions) + "移"
        else:
            action_desc = "悬停拍摄"
        
        # 创建速度指令，支持x和y轴同时移动
        velocity_instruction = {
            "action": action_desc,
            "vel_x": speed_x if dx != 0 else 0,  # x方向速度
            "vel_y": speed_y if dy != 0 else 0,  # y方向速度
            "direction_x": direction_x,  # x方向描述
            "direction_y": direction_y,  # y方向描述
            "duration": 1.0,
            "reason": f"车损位置在({x_norm:.3f}, {y_norm:.3f})，需要{action_desc}调整位置"
        }
        
        return velocity_instruction
    
    def _is_inspection_complete(self, damage_center):
        """
        判断勘察是否完成（车损是否已居中）
        参数:
            damage_center: 车损中心点坐标（归一化）
        返回:
            bool: 勘察是否完成
        """
        x_norm, y_norm = damage_center
        center_threshold = 0.05  # 更严格的居中判断阈值
        
        return (abs(x_norm - 0.5) < center_threshold and 
                abs(y_norm - 0.5) < center_threshold)
    
    def move_by_velocity(self, client, instruction):
        """
        通过速度控制无人机移动（支持多轴同时移动）
        参数:
            client: AirSim客户端对象
            instruction: 移动指令字典，包含 vel_x, vel_y 和 duration
        """
        import airsim
        import time
        
        # 获取移动参数
        vel_x = instruction["vel_x"]
        vel_y = instruction["vel_y"]
        duration = instruction["duration"]
        
        # 确定移动方向
        direction_x = instruction["direction_x"]
        direction_y = instruction["direction_y"]
        
        # 执行多轴同时移动
        if vel_x != 0 or vel_y != 0:
            # 同时在x和y方向移动
            client.moveByVelocityAsync(vel_x if direction_x == "右" else -vel_x if direction_x == "左" else 0,
                                      vel_y if direction_y == "上" else -vel_y if direction_y == "下" else 0,
                                      0,  # z轴不动
                                      duration).join()
        else:
            # 悬停拍摄
            client.hoverAsync().join()
            time.sleep(1)  # 等待1秒
            print("执行拍摄操作")
        
        print(f"移动指令：{instruction['action']} 速度: X轴{'+' if direction_x == '右' else '-'}{vel_x:.2f}m/s, "
              f"Y轴{'+' if direction_y == '上' else '-'}{vel_y:.2f}m/s 时间:{duration:.2f}s")
        self.current_position = self._get_current_position(client)
        print(f"新位置：{self.current_position}")
    
    def _get_current_position(self, client):
        """
        获取当前无人机位置
        参数:
            client: AirSim客户端对象
        返回:
            tuple: 当前位置坐标 (x, y, z)
        """
        try:
            # 尝试获取位置，如果client不可用则返回模拟位置
            pos = client.simGetVehiclePose().position
            return (pos.x_val, pos.y_val, pos.z_val)
        except:
            # 如果无法获取真实位置，则返回模拟位置
            return self.current_position
    
    def simulate_movement(self, instruction):
        """
        模拟无人机移动（支持多轴同时移动），更新当前位置坐标
        参数:
            instruction: 移动指令字典，包含 vel_x, vel_y 和 duration
        """
        # 获取移动参数
        vel_x = instruction["vel_x"]
        vel_y = instruction["vel_y"]
        duration = instruction["duration"]
        direction_x = instruction["direction_x"]
        direction_y = instruction["direction_y"]
        
        # 根据指令类型调整位置
        new_x = self.current_position[0]
        new_y = self.current_position[1]
        
        if direction_x == "右":
            new_x += vel_x * duration
        elif direction_x == "左":
            new_x -= vel_x * duration
            
        if direction_y == "上":
            new_y += vel_y * duration
        elif direction_y == "下":
            new_y -= vel_y * duration
        
        self.current_position = (new_x, new_y, self.current_position[2])
        
        print(f"模拟移动：{instruction['action']} 速度: X轴{'+' if direction_x == '右' else '-'}{vel_x:.2f}m/s, "
              f"Y轴{'+' if direction_y == '上' else '-'}{vel_y:.2f}m/s 时间:{duration:.2f}s")
        print(f"新位置：{self.current_position}")