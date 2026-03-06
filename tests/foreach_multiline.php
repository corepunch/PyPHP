<?php

// Test that foreach with a multi-line iterable expression works correctly.
// Regression test for: foreach (array_filter(\n    ...\n) as $k => $v)

class Type {
    public $default;
    public function __construct($d) {
        $this->default = $d;
    }
}

$items = [
    'x' => new Type('10'),
    'y' => new Type(null),
    'z' => new Type('5'),
];

// Multi-line foreach (key=>value) with array_filter and arrow fn
$out = [];
foreach (array_filter(
    $items,
    fn($type) => $type->default
) as $property => $type):
    array_push($out, $property);
endforeach;
assert($out == ['x', 'z']);

// Multi-line foreach, value-only variant
$values = [];
foreach (array_filter(
    ['a', '', 'b', '', 'c'],
    fn($s) => $s
) as $v):
    array_push($values, $v);
endforeach;
assert($values == ['a', 'b', 'c']);
?>
