<?php
// Test multi-arg echo syntax
// Each arg should appear in the output

// String concatenation and stdlib still work correctly
$result = "hello" . " " . "world";
assert($result == "hello world");

// Function calls with commas in their argument lists are separated correctly
$ha3 = str_repeat("ha", 3);
assert($ha3 == "hahaha");

// Single-argument echo (existing behaviour)
$a = "single";
assert($a == "single");
?>
<?php echo "multi", "-", "arg"; ?>
