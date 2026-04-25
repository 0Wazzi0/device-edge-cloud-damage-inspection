import keyboard
import airsim
import time
import threading

# 连接到 AirSim
client = airsim.MultirotorClient()
client.confirmConnection()
client.enableApiControl(True)
client.armDisarm(True)

print("=== 无人机实时控制已启动 ===")
print("K - 起飞 | L - 降落 | Esc - 退出")
print("W/S - 前后 | A/D - 左右 | ↑/↓ - 升降 | ←/→ - 转向")
print("提示：可以同时按多个键！")

# 状态变量
flying = False
running = True

def takeoff():
    global flying
    if not flying:
        print("起飞...")
        client.takeoffAsync().join()
        flying = True
        print("起飞完成")

def land():
    global flying
    if flying:
        print("降落...")
        client.landAsync().join()
        client.armDisarm(False)
        flying = False
        print("降落完成")

# 控制循环（实时检测）
def control_loop():
    while running:
        if not flying:
            time.sleep(0.1)
            continue
            
        vx, vy, vz = 0, 0, 0
        yaw_rate = 0
        
        # 实时检测按键（支持同时按）
        if keyboard.is_pressed('w'): vx = 3
        if keyboard.is_pressed('s'): vx = -3
        if keyboard.is_pressed('a'): vy = -2
        if keyboard.is_pressed('d'): vy = 2
        if keyboard.is_pressed('up'): vz = -1      # 上升
        if keyboard.is_pressed('down'): vz = 1     # 下降
        if keyboard.is_pressed('left'): yaw_rate = -20
        if keyboard.is_pressed('right'): yaw_rate = 20
        
        # 如果有按键按下，发送指令
        if vx != 0 or vy != 0 or vz != 0 or yaw_rate != 0:
            client.moveByVelocityBodyFrameAsync(vx, vy, vz, 0.1, 
                                               yaw_mode=airsim.YawMode(True, yaw_rate))
        else:
            # 无按键时悬停（可选）
            pass
            
        time.sleep(0.05)  # 20fps 刷新率

# 启动控制线程
control_thread = threading.Thread(target=control_loop)
control_thread.start()

# 功能按键（事件触发）
keyboard.add_hotkey('k', takeoff)
keyboard.add_hotkey('l', land)
keyboard.add_hotkey('esc', lambda: globals().update(running=False) or exit())

print("等待指令...")

# 保持主线程
keyboard.wait()