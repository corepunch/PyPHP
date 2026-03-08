<?php
// ── Static property access: ClassName::$Prop ─────────────────────────────────
// Tests that config::$TypeInfos[$key] works correctly and is NOT mangled
// to _ClassName__Prop inside class bodies.

class TypeConfig {
    public static $Infos = [
        "int"    => ["size" => 4, "signed" => true],
        "float"  => ["size" => 4, "signed" => true],
        "string" => ["size" => 0, "signed" => false],
    ];

    public static $Names = ["alpha", "beta", "gamma"];

    public static $Counter = 0;
}

// ── Access static property directly ──────────────────────────────────────────

assert(TypeConfig::$Infos["int"]["size"] == 4);
assert(TypeConfig::$Infos["float"]["signed"] == true);
assert(TypeConfig::$Infos["string"]["signed"] == false);
assert(TypeConfig::$Names[0] == "alpha");
assert(count(TypeConfig::$Names) == 3);

// ── Modify static property ────────────────────────────────────────────────────

TypeConfig::$Counter = 42;
assert(TypeConfig::$Counter == 42);

// ── Access static property from inside a class method ────────────────────────
// This is the key bug: inside class bodies, Python's name mangling would
// transform config.__TypeInfos to config._ClassName__TypeInfos.

class Parser {
    public $kind;
    public function __construct($kind) {
        $this->kind = $kind;
    }
    public function getSize() {
        return TypeConfig::$Infos[$this->kind]["size"];
    }
    public function isSigned() {
        return TypeConfig::$Infos[$this->kind]["signed"];
    }
    public function getName($index) {
        return TypeConfig::$Names[$index];
    }
}

$p = new Parser("int");
assert($p->getSize() == 4);
assert($p->isSigned() == true);
assert($p->getName(0) == "alpha");
assert($p->getName(1) == "beta");

$p2 = new Parser("string");
assert($p2->getSize() == 0);
assert($p2->isSigned() == false);

// ── ClassName::$Prop inside instance method ──────────────────────────────────
// Accessing static array properties of another class from within a class
// method should not trigger Python name-mangling.

class State {
    public static $table = ["a" => 1, "b" => 2, "c" => 3];
}

class Checker {
    public $key;
    public function __construct($key) {
        $this->key = $key;
    }
    public function lookup() {
        return State::$table[$this->key];
    }
}

$ch = new Checker("b");
assert($ch->lookup() == 2);

// ── Only config::$Prop (with $) should access a static property ──────────────
// config::Prop (without $) would resolve to a *different* Python attribute and
// should raise an error at runtime.  Verify the $-prefixed form works correctly,
// which implicitly validates that the two access paths are distinct.

class Registry {
    public static $items = ["x" => 10, "y" => 20];
    public static $count = 3;
}

// Correct: $-prefixed access works for reads
assert(Registry::$items["x"] == 10);
assert(Registry::$items["y"] == 20);
assert(Registry::$count == 3);

// Correct: $-prefixed access works for writes
Registry::$count = 99;
assert(Registry::$count == 99);
?>
