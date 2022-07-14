import time
import socket
import psutil
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

Font_ArkPixel_12px = ImageFont.truetype('ark-pixel-12px-latin.ttf', 12)

class Screen:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.clear_screen_data = [0] * width * height
        self.buffer = Image.new('1', (width, height))
        self.painter = ImageDraw.Draw(self.buffer)
    
    def clear_frame(self):
        self.buffer.putdata(self.clear_screen_data)
    
    def print_buf_to_terminal(self, buffer):
        data = buffer.getdata()
        for y in range(0, self.height):
            for x in range(0, self.width):
                pixel = data[x + y * self.width]
                flag = '#' if pixel else '.'
                print(f'{flag}', end='')
            print('')

    def dump_frame_buffer(self) -> bytearray:
        data = self.buffer.getdata()
        buf_len = self.width * self.height / 8
        buf_len += 1 if buf_len % 8 > 0 else 0
        buf_len = int(buf_len)
        buf = bytearray(buf_len)

        for byte_index in range(0, buf_len):
            for bit_index in range(0, 8):
                data_idx = byte_index * 8 + bit_index
                if data_idx < len(data):
                    pixel = data[data_idx]
                    if pixel:
                        buf[byte_index] |= 0x80 >> bit_index
                    else:
                        buf[byte_index] &= ~(0x80 >> bit_index)
        
        return buf
    
    def __enter__(self):
        self.clear_frame()
        return self.painter
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

class CpuUsageRecords:
    def __init__(self, records_counts):
        self.records = [None for i in range(0, records_counts)]
    
    def record(self, usage):
        self.records.append(usage)
        self.records.pop(0)
    
    def get_usage(self, core, history_layer):
        if history_layer >= len(self.records):
            return None
        history = self.records[history_layer]
        if history is None or core >= len(history):
            return None
        return history[core]
    
    def __len__(self):
        return len(self.records)
    
class MemoryUsageRecords:
    def __init__(self, records_counts):
        self.records = [None for i in range(0, records_counts)]
    
    def record(self, usage):
        self.records.append(usage)
        self.records.pop(0)
    
    def get_usage(self, history_layer):
        if history_layer >= len(self.records):
            return None
        return self.records[history_layer]
    
    def __len__(self):
        return len(self.records)
    
    def __iter__(self):
        return self.records


def main():
    while True:
        try:
            s = socket.socket()
            s.settimeout(3)
            s.connect(('192.168.1.234', 9080))

            with s as conn:
                screen = Screen(128, 64)

                mem_records = MemoryUsageRecords(46)
                cpus_records = CpuUsageRecords(14)

                psutil.cpu_percent(interval=0.1)
                while True:
                    with screen as painter:
                        cpu_usage = psutil.cpu_percent(interval=None)
                        mem = psutil.virtual_memory()
                        mem_usage_percent = int((mem.total - mem.available) / mem.total * 100)

                        # painter.text((2, 2), f"MEM: {mem_usage_percent}\nCPU: {cpu_usage}", font=Font_ArkPixel_12px, fill=1)
                        painter.text((2, 2), f"MEM: {mem_usage_percent}", font=Font_ArkPixel_12px, fill=1)

                        mem_records.record(mem_usage_percent)

                        cpu_usages = psutil.cpu_percent(interval=None, percpu=True)
                        cpus_records.record(cpu_usages)

                        base_x = 64
                        base_y = 0
                        gap_v = 0
                        gap_h = 0
                        block_width = 15
                        block_height = 15
                        colums = 4
                        for core_index in range(0, len(cpu_usages)):
                            block_x = core_index % colums
                            block_y = core_index // colums
                            frame_x = base_x + block_x * block_width + gap_h * block_x
                            frame_y = base_y + block_y * block_height + gap_v * block_y

                            painter.rectangle((frame_x, frame_y, frame_x + block_width, frame_y + block_height), fill=0, outline=1)

                            for history_layer in range(0, len(cpus_records)):
                                core_usage = cpus_records.get_usage(core_index, history_layer)
                                if core_usage is not None:
                                    x = history_layer + frame_x + 1
                                    y = block_height - (core_usage / 100 * block_height) + frame_y - 1

                                    painter.point((x , y), fill=1)

                        painter.rectangle((0, 16, 63 - 16, 63), fill=0, outline=1)
                        for history_layer in range(0, len(mem_records)):
                            usage = mem_records.get_usage(history_layer)
                            if usage is not None:
                                x = history_layer + 0 + 1
                                y = 63 - (usage / 100 * (63 - 16 - 2)) - 1

                                painter.point((x , y), fill=1)
                        
                        painter.line((0, 32, 127, 32), fill=1, width=1)

                        
                    conn.send('b'.encode() + screen.dump_frame_buffer())
                    conn.recv(8).decode()
                    time.sleep(1)
        except ConnectionAbortedError as e:
            print('connection abort, trying to reconnect...')
            time.sleep(3)
            pass

            
        




    
