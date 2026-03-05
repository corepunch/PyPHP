<?php $name = "World"; ?>
<?php assert("Hello, $name!" == "Hello, World!") ?>
<?php $count = 3; ?>
<?php assert("Count: $count items" == "Count: 3 items") ?>
<?php $arr = ["a", "b", "c"]; ?>
<?php assert("First: $arr[0]" == "First: a") ?>
<?php $x = 42; ?>
<?php assert("x is {$x}" == "x is 42") ?>
<?php assert('No $interpolation here' == 'No $interpolation here') ?>
