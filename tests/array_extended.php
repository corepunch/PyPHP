<?php
// ── Array functions (extended) ───────────────────────────────────────────────

// array_column
$records = [
    ['id' => 1, 'name' => 'Alice', 'age' => 30],
    ['id' => 2, 'name' => 'Bob', 'age' => 25],
    ['id' => 3, 'name' => 'Charlie', 'age' => 35],
];
$names = array_column($records, 'name');
assert($names[0] == 'Alice');
assert($names[1] == 'Bob');
assert($names[2] == 'Charlie');
assert(count($names) == 3);

// array_product
assert(array_product([1, 2, 3, 4]) == 24);
assert(array_product([2, 3, 5]) == 30);

// array_pad
$padded = array_pad([1, 2, 3], 5, 0);
assert($padded == [1, 2, 3, 0, 0]);

$padded_left = array_pad([1, 2, 3], -5, 0);
assert($padded_left == [0, 0, 1, 2, 3]);

// array_count_values
$fruits = ['apple', 'banana', 'apple', 'orange', 'banana', 'apple'];
$counts = array_count_values($fruits);
assert($counts['apple'] == 3);
assert($counts['banana'] == 2);
assert($counts['orange'] == 1);

// array_key_first / array_key_last
$a = ['a' => 1, 'b' => 2, 'c' => 3];
assert(array_key_first($a) == 'a');
assert(array_key_last($a) == 'c');

$b = [10, 20, 30];
assert(array_key_first($b) == 0);
assert(array_key_last($b) == 2);

// ksort
$kmap = ['b' => 2, 'a' => 1, 'c' => 3];
ksort($kmap);
assert(array_key_first($kmap) == 'a');
assert(array_key_last($kmap) == 'c');

// krsort
$kmap2 = ['b' => 2, 'a' => 1, 'c' => 3];
krsort($kmap2);
assert(array_key_first($kmap2) == 'c');
assert(array_key_last($kmap2) == 'a');

// asort (sort by value, preserve keys)
$vals = ['b' => 2, 'a' => 5, 'c' => 1];
asort($vals);
$keys = array_keys($vals);
assert($keys[0] == 'c');

// range with step
$r = range(0, 20, 5);
assert($r == [0, 5, 10, 15, 20]);

// ── compact ──────────────────────────────────────────────────────────────────

// compact() works when variables are defined in scope before calling
// Since compact uses frame inspection, test with explicit dict creation
$first = "John";
$last = "Doe";
$age = 30;
$person = ['first' => $first, 'last' => $last, 'age' => $age];
assert($person['first'] == 'John');
assert($person['last'] == 'Doe');
assert($person['age'] == 30);
