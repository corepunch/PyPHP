<?php require "tests/php_helper.php"; ?>
<?php assert($php_greeting == "Hello from PHP") ?>
<?php assert(php_greet("World") == "Hello, World!") ?>
<?php $g = new Greeter("Hi"); ?>
<?php assert($g->greet("Alice") == "Hi, Alice!") ?>
