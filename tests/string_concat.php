<?php $first = "Hello"; $last = "World"; ?>
<?php $full = $first . " " . $last; ?>
<?php assert($full == "Hello World") ?>
<?php $a = "foo"; $b = "bar"; ?>
<?php $ab = $a . $b; ?>
<?php assert($ab == "foobar") ?>
<?php $s = "count="; $n = 5; ?>
<?php $sn = $s . $n; ?>
<?php assert($sn == "count=5") ?>
<?php $x = "abc"; $x .= "def"; ?>
<?php assert($x == "abcdef") ?>
