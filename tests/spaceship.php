<?php
// Tests for PHP spaceship operator (<=>)

// Basic integer comparisons
assert((1 <=> 2) == -1);
assert((2 <=> 1) == 1);
assert((1 <=> 1) == 0);

// String comparisons
assert(("a" <=> "b") == -1);
assert(("b" <=> "a") == 1);
assert(("a" <=> "a") == 0);

// Float comparisons
assert((1.5 <=> 2.5) == -1);
assert((2.5 <=> 1.5) == 1);
assert((1.5 <=> 1.5) == 0);

// Mixed numeric
assert((1 <=> 1.0) == 0);
assert((2 <=> 1.5) == 1);

// In usort with arrow function
$arr = [3, 1, 4, 1, 5, 9, 2, 6];
usort($arr, fn($a, $b) => $a <=> $b);
assert($arr[0] == 1);
assert($arr[1] == 1);
assert($arr[2] == 2);
assert($arr[7] == 9);

// Descending sort
$arr2 = [3, 1, 4, 1, 5];
usort($arr2, fn($a, $b) => $b <=> $a);
assert($arr2[0] == 5);
assert($arr2[4] == 1);

// Sorting strings
$words = ["banana", "apple", "cherry"];
usort($words, fn($a, $b) => $a <=> $b);
assert($words[0] == "apple");
assert($words[1] == "banana");
assert($words[2] == "cherry");

// In user-defined comparison function
function compare($a, $b) {
    return $a <=> $b;
}
$nums = [5, 2, 8, 1];
usort($nums, 'compare');
assert($nums[0] == 1);
assert($nums[3] == 8);
?>
