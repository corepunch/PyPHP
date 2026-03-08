<?php
// Tests for PHP variable functions and call_user_func

function greet($name) { return "Hello, $name!"; }
function double($n) { return $n * 2; }

// Variable function via string name
$func = "greet";
assert($func("World") == "Hello, World!");

// Variable function with different name
$fn = "double";
assert($fn(5) == 10);

// Anonymous function assigned to variable
$square = function($n) { return $n * $n; };
assert($square(4) == 16);

// call_user_func with string name
assert(call_user_func("greet", "PHP") == "Hello, PHP!");
assert(call_user_func("double", 7) == 14);

// call_user_func_array
assert(call_user_func_array("greet", ["Test"]) == "Hello, Test!");

// is_callable
assert(is_callable($square) == true);
assert(is_callable(42) == false);

// usort with string callback
function cmp_asc($a, $b) { return $a - $b; }
$arr = [3, 1, 4, 1, 5];
usort($arr, "cmp_asc");
assert($arr[0] == 1);
assert($arr[4] == 5);
?>
