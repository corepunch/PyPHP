"""
model.py — loads model.xml and exposes a Model class used by header.php.

E() wraps XML elements so $struct->name and $field->type work in templates
instead of the more verbose ET element .get() calls.
"""

import xml.etree.ElementTree as ET
from pyphp import E


class Model:
    def __init__(self, path):
        self._root = ET.parse(path).getroot()

    def structs(self):
        return [E(s) for s in self._root.findall("struct")]
