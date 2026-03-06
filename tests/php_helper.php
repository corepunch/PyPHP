<?php
$php_greeting = "Hello from PHP";

function php_greet($name) {
    return "Hello, " . $name . "!";
}

class Greeter {
    public function __construct($prefix) {
        $this->prefix = $prefix;
    }
    public function greet($name) {
        return $this->prefix . ", " . $name . "!";
    }
}
