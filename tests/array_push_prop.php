<?php
// Tests for array push on object properties (issue #3)

class Cart {
    public $items = [];
    public $tags = [];

    public function addItem($item) {
        $this->items[] = $item;
    }

    public function addTag($tag) {
        $this->tags[] = $tag;
    }

    public function getItems() {
        return $this->items;
    }
}

$cart = new Cart();
assert(count($cart->items) == 0);

// $this->items[] = $item (array push on object property)
$cart->addItem("apple");
$cart->addItem("banana");
$cart->addItem("cherry");
assert(count($cart->items) == 3);
assert($cart->items[0] == "apple");
assert($cart->items[1] == "banana");
assert($cart->items[2] == "cherry");

// Multiple properties
$cart->addTag("fruit");
$cart->addTag("organic");
assert(count($cart->tags) == 2);
assert($cart->tags[0] == "fruit");
