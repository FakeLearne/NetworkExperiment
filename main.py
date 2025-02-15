import threading
import time
import random
import queue
import matplotlib.pyplot as plt

# 参数设置
BUFFER_SIZE = 10
SIMULATION_TIME = 100  # 模拟时间（秒）
PACKET_GEN_RATE_START = 1.2  # 初始数据包生成率（每秒）
PACKET_INTERVAL_STDDEV = 0.5  # 生成数据包间隔时间的标准差
DELAY_MEAN = 0.5  # 路由器处理数据包的延迟的数学期望（秒）
DELAY_STDDEV = 0.2  # 网络延迟的震荡幅度（标准差）
RETRY_TIME = 0.5

# 全局变量
packets_sent = 0
packets_received = 0
packets_dropped = 0
total_delay = 0
lock = threading.Lock()

# 统计数据
stats_time = []
stats_throughput = []
stats_packet_loss = []
stats_packet_delay = []
receiver_stats = {
    "A": [],
    "B": [],
    "C": [],
    "D": []
}

# 定义数据包类
class Packet:
    def __init__(self, src, dest, path, seq_num, timestamp):
        self.src = src
        self.dest = dest
        self.pre = src
        self.path = 0  # 当前路径的位置索引
        self.seq_num = seq_num
        self.timestamp = timestamp
        self.path_list = path  # 路径列表，例如 [R1, R2]
        self.packet_id = f"{self.src}{self.seq_num}"  # 添加唯一标识符

# 定义路由器类
class Router:
    def __init__(self, name, buffer_size):
        self.name = name
        self.buffer = queue.Queue(maxsize=buffer_size)
        self.lock = threading.Lock()

    def receive_packet(self, packet):
        with self.lock:
            if not self.buffer.full():
                self.buffer.put(packet)
                # print(f"{self.name} received packet {packet.packet_id} from {packet.src}")
                packet.path += 1
                return True
            else:
                print(f"Time: {time.time()-start_time:.2f}s, {self.name} buffer full. Packet {packet.packet_id} dropped.")
                return False

    def process_packets(self):
        global packets_received, packets_dropped, total_delay
        while True:
            try:
                with self.lock:
                    packet = self.buffer.get(timeout=0.1)
                # 模拟处理时间和网络延迟
                delay = max(0, random.gauss(DELAY_MEAN, DELAY_STDDEV))
                time.sleep(delay)
                with lock:
                    total_delay += (time.time() - packet.timestamp)
                # 转发到下一个路由器或目标主机
                if packet.path >= len(packet.path_list):
                    # 到达目标主机
                    receiver_stats[packet.dest].append(time.time() - packet.timestamp)
                    with lock:
                        packets_received += 1
                    # print(f"{self.name} forwarded packet {packet.packet_id} to Host {packet.dest}")
                    print(f"Time: {time.time()-start_time:.2f}s, Host {packet.dest} received packet {packet.packet_id} from {self.name}")
                else:
                    next_router = packet.path_list[packet.path]
                    # print(f"{self.name} forwarded packet {packet.packet_id} to {next_router.name}")
                    while True:
                        print(f"Time: {time.time()-start_time:.2f}s, {self.name} forwarded packet {packet.packet_id} to {next_router.name}")
                        success = next_router.receive_packet(packet)
                        pre_time = time.time()
                        with self.lock:
                            if success:
                                print(f"Time: {time.time()-start_time:.2f}s, {next_router.name} received packet {packet.packet_id} from {self.name}")
                                break
                            else:
                                packets_dropped += 1
                        time.sleep(RETRY_TIME)
                        total_delay += (time.time() - pre_time)
                    # success = next_router.receive_packet(packet)
                    # if success:
                    #     # packet.path += 1
                    #     # print(f"{self.name} forwarded packet {packet.packet_id} to {next_router.name}")
                    #     print(f"{next_router.name} received packet {packet.packet_id} from {self.name}")
                    # else:
                    #     # 转发失败，丢包
                    #     with lock:
                    #         packets_dropped += 1
            except queue.Empty:
                continue

# 定义主机类
class Host:
    def __init__(self, name, target, path):
        self.name = name
        self.target = target
        self.path_list = path  # 路径列表，例如 [R1, R2]
        self.seq_num = 0
        self.send_rate = PACKET_GEN_RATE_START  # 初始发送速率
        self.lock = threading.Lock()
        self.pre_packets_dropped = 0

    def send_packets(self):
        global packets_sent, packets_dropped
        while time.time() - start_time < SIMULATION_TIME:
            packet = Packet(
                src=self.name,
                dest=self.target,
                path=self.path_list,
                seq_num=self.seq_num,
                timestamp=time.time()
            )
            first_router = self.path_list[0]
            while True:
                success = first_router.receive_packet(packet)
                with self.lock:
                    if success:
                        packets_sent += 1
                        self.seq_num += 1
                        print(f"Time: {time.time()-start_time:.2f}s, {first_router.name} received packet {packet.packet_id} from {packet.src}")
                        break
                    else:
                        packets_dropped += 1
                self.adjust_send_rate()
                sleeptime = max(0, random.gauss(1 / self.send_rate, PACKET_INTERVAL_STDDEV))
                time.sleep(sleeptime)
            # 根据拥塞控制算法调整发送速率
            self.adjust_send_rate()
            sleeptime = max(0, random.gauss(1/self.send_rate, PACKET_INTERVAL_STDDEV))
            time.sleep(sleeptime)

    def adjust_send_rate(self):
        # 简单的拥塞控制算法示例
        global packets_dropped
        deta = packets_dropped - self.pre_packets_dropped
        with self.lock:
            if deta > 0:
                # 拥塞时减少发送速率
                self.send_rate = max(0.2, self.send_rate - 0.1)
                print(f"Host {self.name} detected congestion. Reducing send rate to {self.send_rate:.2f} packets/s")
            else:
                # 无拥塞时逐步增加发送速率
                self.send_rate += 0.02
                print(f"Host {self.name} increasing send rate to {self.send_rate:.2f} packets/s")
        self.pre_packets_dropped = packets_dropped

# 创建路由器
R1 = Router("R1", buffer_size=BUFFER_SIZE)
R2 = Router("R2", buffer_size=BUFFER_SIZE)
R3 = Router("R3", buffer_size=BUFFER_SIZE)
R4 = Router("R4", buffer_size=BUFFER_SIZE)

# 路径定义
PATH_A_TO_C = [R1, R2]
PATH_B_TO_D = [R2, R3]
PATH_C_TO_A = [R3, R4]
PATH_D_TO_B = [R4, R1]

# 创建主机
A = Host("A", "C", PATH_A_TO_C)
B = Host("B", "D", PATH_B_TO_D)
C = Host("C", "A", PATH_C_TO_A)
D = Host("D", "B", PATH_D_TO_B)

# 记录模拟开始时间
start_time = time.time()
print("开始模拟...")

# 启动路由器线程
routers = [R1, R2, R3, R4]
for router in routers:
    threading.Thread(target=router.process_packets, daemon=True).start()

# 启动主机发送线程
hosts = [A, B, C, D]
for host in hosts:
    threading.Thread(target=host.send_packets, daemon=True).start()

# 统计线程函数
def collect_stats():
    global stats_time, stats_throughput, stats_packet_loss, stats_packet_delay
    while time.time() - start_time < SIMULATION_TIME:
        with lock:
            current_time = time.time() - start_time
            current_sent = packets_sent
            current_received = packets_received
            current_dropped = packets_dropped
            current_delay = total_delay

        throughput = current_received / current_time if current_time > 0 else 0
        # packet_loss = current_dropped / current_sent if current_sent > 0 else 0
        packet_loss = (current_sent - current_received) / current_sent if current_sent > 0 else 0
        avg_delay = current_delay / current_sent if current_sent > 0 else 0

        stats_time.append(current_time)
        stats_throughput.append(throughput)
        stats_packet_loss.append(packet_loss)
        stats_packet_delay.append(avg_delay)

        print(f"Time: {current_time:.2f}s, Sent: {current_sent}, Received: {current_received}, Dropped: {current_dropped} , Delay: {current_delay:.2f}")

        time.sleep(1)  # 每秒输出一次

# 启动统计线程
stats_thread = threading.Thread(target=collect_stats, daemon=True)
stats_thread.start()

# 等待模拟时间结束
time.sleep(SIMULATION_TIME)

# 等待统计线程结束
stats_thread.join()

# 绘制图形
plt.figure(figsize=(12, 6))

plt.subplot(2, 2, 1)
plt.plot(stats_time, stats_throughput, label='Throughput')
plt.title('Throughput Over Time')
plt.xlabel('Time (s)')
plt.ylabel('Throughput (packets/s)')
plt.legend()

plt.subplot(2, 2, 2)
plt.plot(stats_time, stats_packet_loss, label='Packet Loss Rate', color='red')
plt.title('Packet Loss Rate Over Time')
plt.xlabel('Time (s)')
plt.ylabel('Packet Loss Rate')
plt.legend()

plt.subplot(2, 2, 3)
plt.plot(stats_time, stats_packet_delay, label='Average Packet Delay', color='black')
plt.title('Average Packet Delay Over Time')
plt.xlabel('Time (s)')
plt.ylabel('Delay (s/packet)')
plt.legend()

plt.tight_layout()
plt.show()

# 输出各主机接收延迟统计
for host, delays in receiver_stats.items():
    if delays:
        avg_delay = sum(delays) / len(delays)
        print(f"Host {host} average delay: {avg_delay:.4f}s over {len(delays)} packets")
    else:
        print(f"Host {host} received no packets.")

