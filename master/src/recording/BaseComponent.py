from abc import ABC, abstractmethod


class BaseComponent(ABC):
    def init(self):
        pass

    @abstractmethod
    def on_draw(self, painter, buffer):
        pass