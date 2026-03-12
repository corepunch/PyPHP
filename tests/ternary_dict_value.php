<?php
// Ternary as a value in a multi-line dict literal.
// Previously the preprocessor hoisted the ternary condition variable to its
// own line before the dict, producing invalid Python.

$namespace = "MyNamespace";
$use_ns = true;
$empty_ns = false;

// Basic ternary as dict value (middle entry)
$config = [
    'name' => 'test',
    'namespace' => $use_ns ? $namespace : '',
    'other' => 'value',
];
assert($config['namespace'] == "MyNamespace");
assert($config['name'] == 'test');
assert($config['other'] == 'value');

// Ternary as first dict value
$first = [
    'ns' => $use_ns ? $namespace : 'none',
    'x' => 42,
];
assert($first['ns'] == "MyNamespace");
assert($first['x'] == 42);

// Ternary as last dict value (trailing comma)
$last = [
    'a' => 1,
    'b' => $empty_ns ? 'yes' : 'no',
];
assert($last['b'] == "no");

// Ternary with function call in condition
$items = [1, 2, 3];
$d = [
    'label' => count($items) > 2 ? 'many' : 'few',
    'count' => count($items),
];
assert($d['label'] == 'many');
assert($d['count'] == 3);

// Nested ternary as dict value
$score = 75;
$grade_map = [
    'grade' => $score >= 90 ? 'A' : ($score >= 70 ? 'B' : 'F'),
    'pass' => $score >= 60 ? true : false,
];
assert($grade_map['grade'] == 'B');
assert($grade_map['pass'] == true);

echo "OK\n";
