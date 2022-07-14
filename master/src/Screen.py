from PIL import Image
from PIL import ImageDraw

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