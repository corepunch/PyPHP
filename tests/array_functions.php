<?php $nums = [3, 1, 4, 1, 5, 9, 2, 6]; ?>
<?php assert(implode(", ", $nums) == "3, 1, 4, 1, 5, 9, 2, 6") ?>
<?php $words = "one,two,three"; ?>
<?php assert(implode("-", explode(",", $words)) == "one-two-three") ?>
<?php $fruits = ["apple", "banana", "cherry"]; ?>
<?php assert(in_array("banana", $fruits)) ?>
<?php assert(in_array("grape", $fruits) == false) ?>
<?php assert(count($fruits) == 3) ?>
<?php assert(array_sum($nums) == 31) ?>
<?php $unique = array_unique([1, 2, 2, 3, 3, 3]); ?>
<?php assert(implode(",", $unique) == "1,2,3") ?>
<?php $rev = array_reverse([1, 2, 3]); ?>
<?php assert(implode(",", $rev) == "3,2,1") ?>
<?php sort($nums); ?>
<?php assert(implode(",", $nums) == "1,1,2,3,4,5,6,9") ?>
<?php $keys = array_keys(["x", "y", "z"]); ?>
<?php assert(implode(",", $keys) == "0,1,2") ?>
<?php $merged = array_merge([1, 2], [3, 4]); ?>
<?php assert(implode(",", $merged) == "1,2,3,4") ?>
<?php $sliced = array_slice([10, 20, 30, 40, 50], 1, 3); ?>
<?php assert(implode(",", $sliced) == "20,30,40") ?>
<?php $assoc = ["a" => 10, "b" => 20, "c" => 30]; ?>
<?php assert(implode(",", $assoc) == "10,20,30") ?>
<?php $doubled = array_map(fn($v) => $v * 2, $assoc); ?>
<?php assert(implode(",", $doubled) == "20,40,60") ?>
<?php $akeys = array_keys($assoc); ?>
<?php assert(implode(",", $akeys) == "a,b,c") ?>
