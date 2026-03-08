<?php
// ── PHP array (PhpArray) tests ────────────────────────────────────────────────
// [] now creates a PHP-style ordered dictionary (PhpArray) that supports
// any-type keys, not just integer indices.

// ── Empty array can accept non-integer keys ───────────────────────────────────

class Key {
    public $name;
    public function __construct($n) { $this->name = $n; }
}

$result = [];
$k1 = new Key("first");
$k2 = new Key("second");
$result[$k1] = "one";
$result[$k2] = "two";
assert(count($result) == 2);
assert($result[$k1] == "one");
assert($result[$k2] == "two");

// ── Sequential array via [] literal ──────────────────────────────────────────

$nums = [10, 20, 30];
assert(count($nums) == 3);
assert($nums[0] == 10);
assert($nums[1] == 20);
assert($nums[2] == 30);

// ── Array push shorthand on a [] literal ─────────────────────────────────────

$arr = [];
$arr[] = "a";
$arr[] = "b";
$arr[] = "c";
assert(count($arr) == 3);
assert($arr[0] == "a");
assert($arr[1] == "b");
assert($arr[2] == "c");
assert($arr == ["a", "b", "c"]);

// ── foreach value-only on [] literal ─────────────────────────────────────────

$items = ["x", "y", "z"];
$out = [];
foreach ($items as $v) {
    $out[] = $v;
}
assert($out == ["x", "y", "z"]);

// ── foreach KV on [] literal ─────────────────────────────────────────────────

$items = ["x", "y", "z"];
$keys = [];
$vals = [];
foreach ($items as $k => $v) {
    $keys[] = $k;
    $vals[] = $v;
}
assert($keys == [0, 1, 2]);
assert($vals == ["x", "y", "z"]);

// ── Comparison with same sequential array ────────────────────────────────────

$a = [1, 2, 3];
$b = [1, 2, 3];
assert($a == $b);

$c = [1, 2, 4];
assert($a != $c);

// ── in_array works on [] literals ────────────────────────────────────────────

$fruits = ["apple", "banana", "cherry"];
assert(in_array("banana", $fruits));
assert(!in_array("grape", $fruits));

// ── sort / rsort on [] literal ───────────────────────────────────────────────

$nums = [3, 1, 4, 1, 5];
sort($nums);
assert($nums[0] == 1);
assert($nums[4] == 5);
assert(implode(",", $nums) == "1,1,3,4,5");

$nums2 = [3, 1, 4];
rsort($nums2);
assert(implode(",", $nums2) == "4,3,1");

// ── array_push on [] ─────────────────────────────────────────────────────────

$arr2 = [];
array_push($arr2, 100, 200);
assert(count($arr2) == 2);
assert($arr2[0] == 100);
assert($arr2[1] == 200);

// ── array_slice on [] literal ────────────────────────────────────────────────

$sliced = array_slice([10, 20, 30, 40, 50], 1, 3);
assert(implode(",", $sliced) == "20,30,40");

// ── array_merge on [] literals ───────────────────────────────────────────────

$merged = array_merge([1, 2], [3, 4]);
assert(implode(",", $merged) == "1,2,3,4");

// ── array_reverse on [] literal ──────────────────────────────────────────────

$rev = array_reverse([1, 2, 3]);
assert(implode(",", $rev) == "3,2,1");

// ── array_key_first / array_key_last on [] literal ───────────────────────────

$b2 = [10, 20, 30];
assert(array_key_first($b2) == 0);
assert(array_key_last($b2) == 2);

// ── Nested [] array (array of arrays) ────────────────────────────────────────

$matrix = [[1, 2], [3, 4]];
assert($matrix[0][0] == 1);
assert($matrix[0][1] == 2);
assert($matrix[1][0] == 3);
assert($matrix[1][1] == 4);

// ── array() function still works ─────────────────────────────────────────────

$arr3 = array(7, 8, 9);
assert(count($arr3) == 3);
assert($arr3[1] == 8);

$arr4 = array("a", "b");
$arr4[] = "c";
assert($arr4 == ["a", "b", "c"]);
?>
