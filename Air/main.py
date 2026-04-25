"""
无人机车损勘察系统主程序
完全在无人机端运行，独立完成搜索 - 勘察工作流程
无需与基站通信，所有决策均由无人机本地完成
"""

import time
from system_status import DroneSystemState

def simulate_search_sequence():
    """
    模拟搜索序列：从不同角度拍摄的测试图片
    返回:
        list: 测试图片路径列表，前 2 张没有车损，第 3 张开始有车损
    """
    # 假设我们有 5 张测试图片，模拟盘旋搜索过程
    # 前 2 张没有车损，第 3 张开始有车损
    test_images = [
        "./images/test_no_damage_1.jpg",
        "./images/test_no_damage_2.jpg", 
        "./images/testImage.jpg",  # 有车损的图片
        "./images/test_damage_left.jpg",  # 假设车损偏左
        "./images/test_damage_center.jpg"  # 假设车损居中
    ]
    return test_images

def main():
    """主函数：执行无人机车损勘察的完整流程"""
    print("=== 无人机车损勘察系统启动 ===")
    
    # 初始化系统状态机
    system = DroneSystemState()
    
    # 尝试连接AirSim模拟器（可选）
    try:
        import airsim
        client = airsim.MultirotorClient()
        client.confirmConnection()
        client.enableApiControl(True)
        client.armDisarm(True)
        print("已连接到AirSim模拟器")
        use_airsim = True
    except ImportError:
        print("AirSim库未安装，使用模拟模式")
        use_airsim = False
        client = None
    except Exception as e:
        print(f"无法连接到AirSim模拟器: {e}，使用模拟模式")
        use_airsim = False
        client = None
    
    test_images = simulate_search_sequence()
    
    # 主循环：依次处理每张图片
    for i, image_path in enumerate(test_images):
        print(f"\n--- 步骤 {i+1}: 处理图片 {image_path} ---")
        
        if system.state == "SEARCH":
            # 搜索模式：检测当前图片是否有车损
            has_damage, damage_info = system.search_mode(image_path)
            
            if has_damage:
                # 发现车损，切换到勘察模式
                system.update_state("INSPECTION")
                system.inspection_count = 0  # 重置计数器
                
                # 开始勘察循环：调整无人机位置直到车损居中
                continue_inspection = True
                while continue_inspection and system.state == "INSPECTION":
                    instruction, continue_inspection = system.inspection_mode(
                        image_path, system.damage_center
                    )
                    
                    # 根据是否使用AirSim执行相应的移动操作
                    if use_airsim and client:
                        # 使用AirSim进行真实移动
                        system.move_by_velocity(client, instruction)
                    else:
                        # 模拟执行移动指令（在实际系统中，这里会发送指令到飞控系统）
                        system.simulate_movement(instruction)
                    
                    # 模拟移动后重新"拍摄"（这里简化处理，实际应该用新图片）
                    # 在实际系统中，这里应该调用无人机拍照，然后更新 image_path
                    
                    time.sleep(1)  # 模拟处理时间
                
                # 勘察完成，返回搜索模式或结束
                system.update_state("SEARCH")
                break  # 演示目的，找到一次车损后就结束
        
        time.sleep(0.5)  # 模拟处理间隔
    
    # 降落无人机（如果使用AirSim）
    if use_airsim and client:
        try:
            client.landAsync().join()
            client.armDisarm(False)
            client.enableApiControl(False)
        except:
            pass
    
    print("\n=== 系统运行完成 ===")
    print(f"最终状态：{system.state}")
    print(f"最终位置：{system.current_position}")

if __name__ == "__main__":
    main()