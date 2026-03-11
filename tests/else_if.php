<?php
// Tests for 'else if' (two-word form) being recognised as elif

$x = 5;

// Basic else if
if ($x > 10) {
    $label = "big";
} else if ($x > 3) {
    $label = "medium";
} else {
    $label = "small";
}
assert($label == "medium");

// else if with x == boundary
$y = 10;
if ($y > 10) {
    $cat = "above";
} else if ($y == 10) {
    $cat = "equal";
} else {
    $cat = "below";
}
assert($cat == "equal");

// Chain of else if
$grade = 75;
if ($grade >= 90) {
    $letter = "A";
} else if ($grade >= 80) {
    $letter = "B";
} else if ($grade >= 70) {
    $letter = "C";
} else {
    $letter = "D";
}
assert($letter == "C");

// elseif (one word) still works too
$z = 2;
if ($z == 1) {
    $r = "one";
} elseif ($z == 2) {
    $r = "two";
} else {
    $r = "other";
}
assert($r == "two");
