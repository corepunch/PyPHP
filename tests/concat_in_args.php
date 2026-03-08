<?php
// Tests for string concat (.) inside function call arguments (issue #4)

$first = "Hello";
$last = "World";

// Single argument with concat
$len = strlen($first . " " . $last);
assert($len == 11);

// Multiple arguments, each with concat
function joinWithSep($a, $b, $sep) {
    return $a . $sep . $b;
}
$result = joinWithSep("foo" . "bar", "baz" . "qux", "-");
assert($result == "foobar-bazqux");

// Nested: concat inside function arg which is itself an arg
$upper = strtoupper($first . $last);
assert($upper == "HELLOWORLD");

// concat in echo args
$lower = strtolower("HELLO" . " " . "WORLD");
assert($lower == "hello world");

// Return value from function call used in concat
$greeting = "Hi " . strtoupper($first);
assert($greeting == "Hi HELLO");

// Numeric context
$n = intval("42" . "0");
assert($n == 420);
