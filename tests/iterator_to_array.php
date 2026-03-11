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
