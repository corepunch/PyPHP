<?php
// Regression test: single-line foreach without braces must execute its body,
// not fail with a syntax error.

// Key-value foreach with echo body (mirrors the original bug report).
$parsers = ['translation' => 'char*', 'rotation' => 'float', 'scale' => 'float'];
$decls = [];
foreach ($parsers as $field => $type) array_push($decls, "$type $field;");
assert($decls == ['char* translation;', 'float rotation;', 'float scale;']);

// Value-only foreach with echo body.
$items = ['a', 'b', 'c'];
$out = '';
foreach ($items as $v) $out .= $v;
assert($out == 'abc');

// Single-line foreach with echo — verify the body actually executes.
$seen = [];
foreach ($parsers as $field => $type) array_push($seen, "$type $field");
assert($seen == ['char* translation', 'float rotation', 'float scale']);

// Single-line foreach where the condition contains a method call with parens.
// Regression: the greedy regex used to match the wrong ')' and leave the
// line unsplit, causing "echo" to appear as an undefined name at runtime.
class TypeInfo {
    private $container;
    public function __construct($c) { $this->container = $c; }
    public function getContainer() { return $this->container; }
}
class StructDef {
    private $parsers;
    public function __construct() {
        $this->parsers = ['x' => new TypeInfo('int'), 'y' => new TypeInfo('float')];
    }
    public function getParsers() { return $this->parsers; }
}
$struct = new StructDef();
$lines = [];
foreach ($struct->getParsers() as $field => $type) array_push($lines, $type->getContainer() . " $field;");
assert($lines == ['int x;', 'float y;']);
?>
