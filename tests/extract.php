<?php
// Basic extract: associative array keys become variables
$data = ['color' => 'blue', 'size' => 'large', 'count' => 42];
extract($data);
assert($color == 'blue');
assert($size == 'large');
assert($count == 42);
echo $color . '/' . $size . '/' . $count . "\n";

// extract() returns the number of variables imported
$n = extract(['x' => 1, 'y' => 2, 'z' => 3]);
assert($n == 3);
echo $n . "\n";

// Integer keys are skipped (not valid PHP variable names)
$arr = [0 => 'zero', 'name' => 'Alice'];
$imported = extract($arr);
assert($imported == 1);
assert($name == 'Alice');
echo $imported . "\n";
echo $name . "\n";

// extract() works inside a function: variables become accessible within the function
// and in any require-d files (injected into the shared exec scope)
function include_template($variables = []) {
    extract($variables);
    echo $greeting . ' ' . $subject . "\n";
}
include_template(['greeting' => 'Hello', 'subject' => 'World']);
