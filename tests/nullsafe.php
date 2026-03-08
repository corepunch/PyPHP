<?php
// Tests for PHP 8 null-safe operator (?->)

class User {
    public $name;
    public $email;
    public function __construct($name, $email = null) {
        $this->name = $name;
        $this->email = $email;
    }
    public function getName() { return $this->name; }
    public function getEmail() { return $this->email; }
    public function getUpperName() { return strtoupper($this->name); }
}

class Order {
    public $user;
    public $total;
    public function __construct($user, $total) {
        $this->user = $user;
        $this->total = $total;
    }
    public function getUser() { return $this->user; }
}

// Non-null object: method call
$user = new User("Alice", "alice@example.com");
assert($user?->getName() == "Alice");
assert($user?->getUpperName() == "ALICE");
assert($user?->getEmail() == "alice@example.com");

// Non-null object: property access
assert($user?->name == "Alice");
assert($user?->email == "alice@example.com");

// Null object: method call returns null
$null_user = null;
assert($null_user?->getName() === null);
assert($null_user?->getEmail() === null);

// Null object: property access returns null
assert($null_user?->name === null);

// Null-safe in condition
$admin = null;
$name = $admin?->getName();
if ($name === null) {
    $name = "Guest";
}
assert($name == "Guest");

// Chained object access
$order = new Order(new User("Bob"), 99.99);
$null_order = null;
assert($order->getUser()?->getName() == "Bob");
assert($null_order?->getUser() === null);
?>
