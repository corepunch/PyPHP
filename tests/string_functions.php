<?php $s = "  Hello World  "; ?>
<?php assert(strlen($s) == 15) ?>
<?php assert(strtolower($s) == "  hello world  ") ?>
<?php assert(strtoupper($s) == "  HELLO WORLD  ") ?>
<?php assert(trim($s) == "Hello World") ?>
<?php assert(str_replace("World", "PHP", $s) == "  Hello PHP  ") ?>
<?php
// str_replace with optional 4th argument (count) must not raise TypeError
$count = 0;
$result = str_replace("l", "L", "hello world", $count);
assert($result == "heLLo worLd");
?>
<?php $t = "abcdef"; ?>
<?php assert(substr($t, 2, 3) == "cde") ?>
<?php assert(strpos($t, "cd") == 2) ?>
<?php assert(str_repeat("ab", 3) == "ababab") ?>
<?php assert(ucfirst("hello world") == "Hello world") ?>
<?php assert(ucwords("hello world") == "Hello World") ?>
<?php assert(sprintf("%.2f", 3.14159) == "3.14") ?>
<?php assert(number_format(1234567.891, 2) == "1,234,567.89") ?>
