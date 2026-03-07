<?php
// ── Single-line method bodies: "function foo() { return ...; }" ──────────────
// These must generate "def foo(self):\n    return ..." (not leave the { } in).

class Point {
    function __construct($x, $y) {
        $this->x = $x;
        $this->y = $y;
    }
    function getX() { return $this->x; }
    function getY() { return $this->y; }
    function sum()  { return $this->x + $this->y; }
    function label() { return "(" . $this->x . "," . $this->y . ")"; }
}

$p = new Point(3, 4);
assert($p->getX() == 3);
assert($p->getY() == 4);
assert($p->sum()  == 7);
assert($p->label() == "(3,4)");

// ── Dynamic property assignment: $this->$k = $v ───────────────────────────────
// Must become setattr(self, __k, __v) so the property name is dynamic.

class Bag {
    function fill($attrs) {
        foreach ($attrs as $k => $v):
            $this->$k = $v;
        endforeach;
    }
    function get($key) { return $this->$key; }
}

$b = new Bag();
$b->fill(['color' => 'red', 'size' => 'large']);
assert($b->color == 'red');
assert($b->size  == 'large');
assert($b->get('color') == 'red');
assert($b->get('size')  == 'large');

// ── Combined: constructor with foreach + single-line methods (problem pattern) ─

class Attrs {
    function __construct($map) {
        foreach ($map as $k => $v):
            $this->$k = $v;
        endforeach;
    }
    function getName()  { return $this->name; }
    function getColor() { return $this->color; }
}

$a = new Attrs(['name' => 'box', 'color' => 'blue']);
assert($a->getName()  == 'box');
assert($a->getColor() == 'blue');
assert($a->name  == 'box');
assert($a->color == 'blue');

// ── Multi-statement single-line body ──────────────────────────────────────────

class Counter {
    function __construct() { $this->n = 0; }
    function inc() { $this->n = $this->n + 1; }
    function get() { return $this->n; }
}

$c = new Counter();
$c->inc();
$c->inc();
$c->inc();
assert($c->get() == 3);
?>
