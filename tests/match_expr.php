<?php
// Tests for PHP 8 match() expression

// Basic match
$x = 2;
$result = match($x) {
    1 => "one",
    2 => "two",
    3 => "three",
    default => "other"
};
assert($result == "two");

// match with default
$y = 99;
$text = match($y) {
    1 => "one",
    default => "unknown"
};
assert($text == "unknown");

// match with multiple keys per arm
$status = 3;
$label = match($status) {
    0 => "inactive",
    1 => "active",
    2, 3 => "pending",
    default => "unknown"
};
assert($label == "pending");

// match with string subject
$color = "red";
$hex = match($color) {
    "red" => "#FF0000",
    "green" => "#00FF00",
    "blue" => "#0000FF",
    default => "#000000"
};
assert($hex == "#FF0000");

// match in assignment expression
$score = 85;
$grade = match(true) {
    $score >= 90 => "A",
    $score >= 80 => "B",
    $score >= 70 => "C",
    default => "F"
};
assert($grade == "B");

// Inline match (single line)
$n = 5;
$parity = match($n % 2) { 0 => "even", 1 => "odd", default => "?" };
assert($parity == "odd");
?>
