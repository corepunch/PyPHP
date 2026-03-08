<?php
// Tests for abstract class support

abstract class Shape {
    abstract public function area();
    abstract public function perimeter();

    public function describe() {
        return "area=" . $this->area() . " perimeter=" . $this->perimeter();
    }
}

class Circle extends Shape {
    private $radius;
    public function __construct($r) { $this->radius = $r; }
    public function area() { return 3.14159 * $this->radius * $this->radius; }
    public function perimeter() { return 2 * 3.14159 * $this->radius; }
}

class Rectangle extends Shape {
    private $w;
    private $h;
    public function __construct($w, $h) { $this->w = $w; $this->h = $h; }
    public function area() { return $this->w * $this->h; }
    public function perimeter() { return 2 * ($this->w + $this->h); }
}

$c = new Circle(5);
assert(abs($c->area() - 78.53975) < 0.001);
assert(abs($c->perimeter() - 31.4159) < 0.001);
assert($c->describe() == "area=78.53975 perimeter=31.4159");

$r = new Rectangle(3, 4);
assert($r->area() == 12);
assert($r->perimeter() == 14);

// Abstract class with constructor
abstract class Animal {
    private $name;
    public function __construct($name) { $this->name = $name; }
    public function getName() { return $this->name; }
    abstract public function sound();
    public function speak() { return $this->getName() . " says " . $this->sound(); }
}

class Dog extends Animal {
    public function sound() { return "Woof"; }
}

class Cat extends Animal {
    public function sound() { return "Meow"; }
}

$dog = new Dog("Rex");
assert($dog->speak() == "Rex says Woof");

$cat = new Cat("Whiskers");
assert($cat->speak() == "Whiskers says Meow");
?>
