import xml.etree.ElementTree as ET
from pyphp.renderer import E


class Model:
    def __init__(self, path):
        self._root = ET.parse(path).getroot()

    def structs(self):
        return [E(el) for el in self._root.findall("struct")]
