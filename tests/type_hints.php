<?php
// Tests for PHP type hints (issue #7 + #8)

// Parameter type hints
function add(int $a, int $b): int {
    return $a + $b;
}
assert(add(3, 4) == 7);

// String type hint
function greet(string $name): string {
    return "Hello, " . $name . "!";
}
assert(greet("Alice") == "Hello, Alice!");

// Bool return type
function isPositive(int $n): bool {
    return $n > 0;
}
assert(isPositive(5) == true);
assert(isPositive(-1) == false);

// Nullable parameter
function maybeDouble(?int $x): ?int {
    if ($x === null) {
        return null;
    }
    return $x * 2;
}
assert(maybeDouble(5) == 10);
assert(maybeDouble(null) === null);

// Union types (PHP 8+)
function stringify(int|float $n): string {
    return (string)$n;
}
assert(stringify(42) == "42");

// Class with typed properties and methods
class Point {
    public float $x;
    public float $y;

    public function __construct(float $x, float $y) {
        $this->x = $x;
        $this->y = $y;
    }

    public function distanceTo(Point $other): float {
        $dx = $this->x - $other->x;
        $dy = $this->y - $other->y;
        return sqrt($dx * $dx + $dy * $dy);
    }

    public function __toString(): string {
        return "(" . $this->x . "," . $this->y . ")";
    }
}

$p1 = new Point(0.0, 0.0);
$p2 = new Point(3.0, 4.0);
assert($p1->distanceTo($p2) == 5.0);

// Single-line method with return type (issue #8)
class Counter {
    public int $value = 0;

    public function increment(): void { $this->value = $this->value + 1; }
    public function getValue(): int { return $this->value; }
}

$c = new Counter();
$c->increment();
$c->increment();
assert($c->getValue() == 2);
