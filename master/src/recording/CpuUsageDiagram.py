import psutil
from src.recording.BaseComponent import BaseComponent
from PIL import ImageFont


class CpuUsageDiagram(BaseComponent):
    font = ImageFont.truetype('ark-pixel-12px-latin.ttf', 12)
    records_counts = 63 + 16

    def __init__(self):
        self.records = [None for i in range(0, CpuUsageDiagram.records_counts)]
        psutil.cpu_percent(interval=0.1)
    
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
    
    def on_draw(self, painter, buffer):
        usage = psutil.cpu_percent(interval=None)
        self.record([usage])

        painter.text((0 , 0), f"CPU {int(usage)}", font=CpuUsageDiagram.font, fill=1)

        base_x = 48
        base_y = 0
        width = CpuUsageDiagram.records_counts
        height = 15

        # painter.rectangle((base_x, base_y, base_x + width, base_y + height), fill=0, outline=1)

        for history_layer in range(0, len(self)):
            core_usage = self.get_usage(0, history_layer)
            if core_usage is not None:
                x = history_layer + base_x + 1
                y = height - (core_usage / 100 * (height - 2)) + base_y - 1

                painter.point((x , y), fill=1)
