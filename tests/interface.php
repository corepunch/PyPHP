<?php
// Tests for PHP interface support

interface Greetable {
    public function greet();
}

interface Farewell {
    public function farewell();
}

class Hello implements Greetable {
    public function greet() { return "Hello!"; }
}

// Class implementing multiple interfaces
class Greeter implements Greetable, Farewell {
    public $name;
    public function __construct($name) { $this->name = $name; }
    public function greet() { return "Hello, " . $this->name . "!"; }
    public function farewell() { return "Goodbye, " . $this->name . "!"; }
}

$h = new Hello();
assert($h->greet() == "Hello!");

$g = new Greeter("World");
assert($g->greet() == "Hello, World!");
assert($g->farewell() == "Goodbye, World!");

// Interface with class extending another class and implementing interface
interface Measurable {
    public function area();
}

class Shape {
    public $color;
    public function __construct($color) { $this->color = $color; }
    public function getColor() { return $this->color; }
}

class Rectangle extends Shape implements Measurable {
    public $width;
    public $height;
    public function __construct($w, $h) {
        parent::__construct("red");
        $this->width = $w;
        $this->height = $h;
    }
    public function area() { return $this->width * $this->height; }
}

$r = new Rectangle(4, 5);
assert($r->area() == 20);
assert($r->getColor() == "red");

// Interface extending another interface
interface Animal {
    public function sound();
}

interface Pet extends Animal {
    public function name();
}

class Dog implements Pet {
    public function sound() { return "Woof"; }
    public function name() { return "Buddy"; }
}

$dog = new Dog();
assert($dog->sound() == "Woof");
assert($dog->name() == "Buddy");
?>
