<?php
// ── Basic class with constructor and instance methods ──────────────────────────

class Animal {
    public $name;
    public $sound = "...";

    public function __construct($name) {
        $this->name = $name;
    }

    public function speak() {
        return $this->name . " says " . $this->sound;
    }

    public function getName() {
        return $this->name;
    }
}

$a = new Animal("Cat");
assert($a->getName() == "Cat");
assert($a->speak() == "Cat says ...");

// ── Inheritance: subclass overrides a method ───────────────────────────────────

class Dog extends Animal {
    public function __construct($name) {
        parent::__construct($name);
        $this->sound = "Woof";
    }

    public function speak() {
        return "Woof! My name is " . $this->name;
    }
}

class Cat extends Animal {
    public function __construct($name) {
        parent::__construct($name);
        $this->sound = "Meow";
    }

    public function speak() {
        return "Meow! I am " . $this->name;
    }
}

$dog = new Dog("Rex");
$cat = new Cat("Whiskers");

assert($dog->speak() == "Woof! My name is Rex");
assert($cat->speak() == "Meow! I am Whiskers");
assert($dog->getName() == "Rex");
assert($cat->getName() == "Whiskers");
assert($dog->sound == "Woof");
assert($cat->sound == "Meow");

// ── Multi-level inheritance ────────────────────────────────────────────────────

class Vehicle {
    public $make;
    public $speed;

    public function __construct($make, $speed) {
        $this->make = $make;
        $this->speed = $speed;
    }

    public function describe() {
        return $this->make . " at " . $this->speed . " km/h";
    }
}

class Car extends Vehicle {
    public $doors;

    public function __construct($make, $speed, $doors) {
        parent::__construct($make, $speed);
        $this->doors = $doors;
    }

    public function describe() {
        return parent::describe() . ", " . $this->doors . " doors";
    }
}

class ElectricCar extends Car {
    public $range;

    public function __construct($make, $speed, $doors, $range) {
        parent::__construct($make, $speed, $doors);
        $this->range = $range;
    }

    public function describe() {
        return parent::describe() . ", range " . $this->range . " km";
    }
}

$car = new Car("Toyota", 120, 4);
assert($car->describe() == "Toyota at 120 km/h, 4 doors");

$ev = new ElectricCar("Tesla", 200, 4, 500);
assert($ev->describe() == "Tesla at 200 km/h, 4 doors, range 500 km");
assert($ev->make == "Tesla");
assert($ev->range == 500);

// ── Static methods ─────────────────────────────────────────────────────────────

class MathHelper {
    public static function square($n) {
        return $n * $n;
    }

    public static function cube($n) {
        return $n * $n * $n;
    }

    public static function add($a, $b) {
        return $a + $b;
    }
}

assert(MathHelper::square(4) == 16);
assert(MathHelper::cube(3) == 27);
assert(MathHelper::add(5, 7) == 12);

// ── Class with private/protected methods ──────────────────────────────────────

class Counter {
    private $count;

    public function __construct() {
        $this->count = 0;
    }

    public function increment() {
        $this->count = $this->count + 1;
    }

    public function getCount() {
        return $this->count;
    }
}

$c = new Counter();
assert($c->getCount() == 0);
$c->increment();
$c->increment();
$c->increment();
assert($c->getCount() == 3);

// ── Class with multiple properties ────────────────────────────────────────────

class Point {
    public $x;
    public $y;

    public function __construct($x, $y) {
        $this->x = $x;
        $this->y = $y;
    }

    public function distanceTo($other) {
        $dx = $this->x - $other->x;
        $dy = $this->y - $other->y;
        return sqrt($dx * $dx + $dy * $dy);
    }

    public function translate($dx, $dy) {
        $this->x = $this->x + $dx;
        $this->y = $this->y + $dy;
    }
}

$p1 = new Point(0, 0);
$p2 = new Point(3, 4);
assert($p1->distanceTo($p2) == 5.0);

$p1->translate(1, 1);
assert($p1->x == 1);
assert($p1->y == 1);
?>
