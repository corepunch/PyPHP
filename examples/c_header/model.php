<?php
use xml\etree\ElementTree as ET;
use pyphp\renderer as renderer;

class Model {
    public function __construct($path) {
        $this->_root = ET::parse($path)->getroot();
    }

    public function structs() {
        $elements = $this->_root->findall("struct");
        $result = [];
        foreach ($elements as $el) {
            array_push($result, renderer::E($el));
        }
        return $result;
    }
}
?>
