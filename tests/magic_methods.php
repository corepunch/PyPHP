<?php
// Tests for __toString magic method (issue #10)

class Color {
    public $r;
    public $g;
    public $b;

    public function __construct($r, $g, $b) {
        $this->r = $r;
        $this->g = $g;
        $this->b = $b;
    }

    public function __toString() {
        return "rgb(" . $this->r . "," . $this->g . "," . $this->b . ")";
    }
}

$red = new Color(255, 0, 0);
$green = new Color(0, 255, 0);

// str() / (string) cast should call __toString
assert((string)$red == "rgb(255,0,0)");
assert((string)$green == "rgb(0,255,0)");

// Implicit string conversion in echo / concatenation
$blue = new Color(0, 0, 255);
$label = "Color: " . $blue;
assert($label == "Color: rgb(0,0,255)");

// Class with typed __toString return (issue #7 interop)
class Tag {
    public $name;

    public function __construct($name) {
        $this->name = $name;
    }

    public function __toString(): string {
        return "<" . $this->name . ">";
    }
}

$tag = new Tag("div");
assert((string)$tag == "<div>");
