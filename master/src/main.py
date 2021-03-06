from src.CpuRamMeter import CpuRamMeter
from src.recording.CpuUsageDiagram import CpuUsageDiagram
from src.recording.MemoryUsageDiagram import MemoryUsageDiagram


def main():
    meter = CpuRamMeter(128, 32, '192.168.1.242', 9080)

    meter.register_component(MemoryUsageDiagram())
    meter.register_component(CpuUsageDiagram())
    
    meter.main_loop()
