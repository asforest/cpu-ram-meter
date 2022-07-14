import time
import socket
from src.Screen import Screen


class CpuRamMeter:
    def __init__(self, width, height, host, port):
        self.socket = socket.socket()
        self.socket.settimeout(3)
        self.exit_flag = False
        self.slave_addr_port = (host, port)
        self.screen = Screen(width, height)
        self.components = []
    
    def register_component(self, component):
        self.components.append(component)
        component.init()
    
    def draw_frame(self):
        with self.screen as painter:
            # draw all components
            for c in self.components:
                c.on_draw(self.screen.painter, self.screen.buffer)
            
            # painter.line((0, 32, 127, 32), fill=1, width=1)

    def transmit_frame(self):
        self.socket.send('b'.encode() + self.screen.dump_frame_buffer())
        self.socket.recv(8).decode() # wait for the salve's response
    
    def main_loop(self):
        try:
            self.socket.connect(self.slave_addr_port)

            while not self.exit_flag:
                self.draw_frame()
                self.transmit_frame()
                time.sleep(1)

        except ConnectionAbortedError as e:
            print('connection abort, trying to reconnect...')
            time.sleep(3)
            pass