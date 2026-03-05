<?php
function add($a, $b) {
    return $a + $b;
}
function greet($name) {
    return "Hello, " . $name . "!";
}
function printContents($list) {
    foreach ($list as $item) {
        echo $item . "\n";
    }
}
function emptyBody($x) {}
?>
<?= add(3, 4) ?>
<?= greet("World") ?>
<?php $fruits = ["apple", "banana", "cherry"]; ?>
<?php printContents($fruits); ?>
<?php emptyBody(42); ?>
done
