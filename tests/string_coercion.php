<?php
// PHP string coercion in concatenation:
//   true  -> "1"
//   false -> ""
//   null  -> ""
//   int/float -> decimal representation

$s = "val:" . true;
assert($s == "val:1");

$s2 = "val:" . false;
assert($s2 == "val:");

$s3 = "val:" . null;
assert($s3 == "val:");

$s4 = "Result:" . 42;
assert($s4 == "Result:42");

$s5 = "Pi:" . 3.14;
assert($s5 == "Pi:3.14");

// strval() coercion
assert(strval(true) == "1");
assert(strval(false) == "");
assert(strval(null) == "");

// Concatenation assignment
$msg = "Count: ";
$msg .= 5;
assert($msg == "Count: 5");

// Concat chain with mixed types
$result = "" . true . "-" . false . "-" . null . "-" . 0;
assert($result == "1---0");
?>
