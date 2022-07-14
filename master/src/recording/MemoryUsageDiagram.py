import psutil
from src.recording.BaseComponent import BaseComponent
from PIL import ImageFont


class MemoryUsageDiagram(BaseComponent):
    font = ImageFont.truetype('ark-pixel-12px-latin.ttf', 12)
    records_counts = 63 + 16

    def __init__(self):
        self.records = [None for i in range(0, MemoryUsageDiagram.records_counts)]
    
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
    
    def on_draw(self, painter, buffer):
        mem = psutil.virtual_memory()
        mem_usage_percent = int((mem.total - mem.available) / mem.total * 100)
        self.record(mem_usage_percent)

        painter.text((0, 16), f"MEM {mem_usage_percent}", font=MemoryUsageDiagram.font, fill=1)

        base_x = 48
        base_y = 16
        width = MemoryUsageDiagram.records_counts
        height = 16

        # painter.rectangle((base_x, base_y, base_x + width, base_y + height), fill=0, outline=1)

        for history_layer in range(0, len(self)):
            usage = self.get_usage(history_layer)
            if usage is not None:
                x = history_layer + base_x + 1
                y = height - (usage / 100 * (height - 2)) + base_y - 1

                painter.point((x , y), fill=1)