<?php
// Tests for iterator_to_array()

// Generator yielding key => value pairs
function getNamedFields() {
    yield "field1" => "value1";
    yield "field2" => "value2";
    yield "field3" => "value3";
}

$fields = iterator_to_array(getNamedFields());
assert(count($fields) == 3);
assert($fields["field1"] == "value1");
assert($fields["field2"] == "value2");
assert($fields["field3"] == "value3");

// preserve_keys = false returns a list
$values = iterator_to_array(getNamedFields(), false);
assert(count($values) == 3);
assert($values[0] == "value1");
assert($values[1] == "value2");

// Generator yielding plain values (no explicit key)
function yieldParentNames() {
    yield "ParentA";
    yield "ConceptB";
}

// preserve_keys = false: plain values collected in order
$plain = iterator_to_array(yieldParentNames(), false);
assert(count($plain) == 2);
assert($plain[0] == "ParentA");
assert($plain[1] == "ConceptB");

// preserve_keys = true: auto-assigns integer keys 0, 1, ...
$keyed = iterator_to_array(yieldParentNames());
assert(count($keyed) == 2);
assert($keyed[0] == "ParentA");
assert($keyed[1] == "ConceptB");

// Plain-value generator combined with array_map arrow function (issue scenario)
$prefixed = array_map(fn($p) => '&_' . $p, iterator_to_array(yieldParentNames(), false));
assert(implode(',', $prefixed) == "&_ParentA,&_ConceptB");
