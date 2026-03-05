<?php
function add($a, $b) {
    return $a + $b;
}
function greet($name) {
    return "Hello, " . $name . "!";
}
function double($n) {
    return $n * 2;
}
function printContents($list) {
    foreach ($list as $item) {
        echo $item . "\n";
    }
}
function emptyBody($x) {}
?>
<?php assert(add(3, 4) == 7) ?>
<?php assert(greet("World") == "Hello, World!") ?>
<?php assert(double(6) == 12) ?>
<?php $fruits = ["apple", "banana", "cherry"]; ?>
<?php printContents($fruits); ?>
<?php emptyBody(42); ?>
