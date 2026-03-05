<?php
/* Test PHP class support */

class Animal {
    public function __construct($name, $sound) {
        $this->name = $name;
        $this->sound = $sound;
    }

    public function speak() {
        return $this->name . " says " . $this->sound;
    }

    public function getName() {
        return $this->name;
    }
}

class Dog extends Animal {
    public function __construct($name) {
        parent::__construct($name, "woof");
    }

    public function fetch($item) {
        return $this->name . " fetches the " . $item;
    }
}

/* Class constants */
class Config {
    const VERSION = "1.0";
    const DEBUG   = false;
}

$dog = new Dog("Rex");
assert($dog->speak() == "Rex says woof");
assert($dog->getName() == "Rex");
assert($dog->fetch("ball") == "Rex fetches the ball");

/* Test logical operators && || ! */
$a = true;
$b = false;
assert($a && !$b);
assert($a || $b);
assert(!$b);

/* Test class constants */
assert(Config::VERSION == "1.0");
assert(Config::DEBUG == false);

/* Test array append */
$items = [];
$items[] = "alpha";
$items[] = "beta";
assert(count($items) == 2);
assert($items[0] == "alpha");
assert($items[1] == "beta");
?>
