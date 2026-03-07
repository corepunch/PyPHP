<?php
// Tests for $this in foreach iterables (issue #2)

class ItemList {
    public $items = [];
    public $counts = [];

    public function __construct() {
        $this->items = ["apple", "banana", "cherry"];
        $this->counts = [3, 5, 2];
    }

    public function getItems() {
        $result = [];
        foreach ($this->items as $item) {
            $result[] = $item;
        }
        return $result;
    }

    public function sumCounts() {
        $total = 0;
        foreach ($this->counts as $n) {
            $total = $total + $n;
        }
        return $total;
    }

    public function getMap() {
        $map = array("a" => 0, "b" => 1, "c" => 2);
        foreach ($this->items as $k => $v) {
            $map[$k] = $v;
        }
        return $map;
    }
}

$list = new ItemList();

// foreach ($this->items as $item)
$got = $list->getItems();
assert(count($got) == 3);
assert($got[0] == "apple");
assert($got[1] == "banana");
assert($got[2] == "cherry");

// foreach ($this->counts as $n) accumulation
assert($list->sumCounts() == 10);

// foreach ($this->items as $k => $v) key-value
$map = $list->getMap();
assert($map[0] == "apple");
assert($map[2] == "cherry");
