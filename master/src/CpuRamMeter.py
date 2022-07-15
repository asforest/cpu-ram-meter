import time
import socket
from src.Screen import Screen


class CpuRamMeter:
    def __init__(self, width, height, host, port):
        self.socket = None
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
        response = self.socket.recv(64).decode().strip() # wait for the salve's response
        if response != 'ok':
            print(response)
    
    def conect_to_slave(self):
        self.socket = socket.socket()
        self.socket.settimeout(3)
        self.socket.connect(self.slave_addr_port)

    def main_loop(self):
        retries = 3

        while retries >= 0:
            try:
                print('connect to ' + str(self.slave_addr_port))
                self.conect_to_slave()

                while not self.exit_flag:
                    self.draw_frame()
                    self.transmit_frame()
                    time.sleep(1)

            except TimeoutError as e:
                retries -= 1
                print('connection timeout')
                time.sleep(1)
                
            except ConnectionAbortedError as e:
                retries -= 1
                print('connection abort')
                time.sleep(1)
            
            finally:
                self.socket.close()