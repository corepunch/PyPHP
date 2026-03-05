<?php
// nested foreach where the inner loop body (foreach + echo + endforeach)
// lives inside a single php tag.

$components = array_combine(["Button", "Label"], [["text", "color"], ["text", "size"]]);
$out = [];
foreach ($components as $name => $props):
  foreach ($props as $prop)
    array_push($out, "{$name}_{$prop}");
  endforeach
endforeach
assert($out == ["Button_text", "Button_color", "Label_text", "Label_size"]);

// same pattern but body uses echo with string interpolation (f-string braces)
foreach (["x", "y"] as $item):
  foreach ([1, 2] as $n)
    echo("{$item}{$n} ");
  endforeach
endforeach

// hash() builtin: fnv1a32 and common hashlib algorithms
assert(hash('fnv1a32', 'hello') == '4f9f2cab');
assert(hash('fnv1a32', 'world') == '37a3e893');
assert(hash('md5', 'test') == '098f6bcd4621d373cade4e832627b4f6');
assert(strlen(hash('sha256', 'abc')) == 64);

// single-line foreach: foreach (...) body; endforeach all on one line
$singles = [];
foreach (["a", "b", "c"] as $v) array_push($singles, $v); endforeach
assert($singles == ["a", "b", "c"]);

// single-line kv foreach with echo + hash (exact pattern from the issue)
$props = array_combine(["text", "color"], ["string", "int"]);
$name = "Button";
?>
<?php foreach ($props as $property_name => $property_type) echo("#define ID_{$name}_{$property_name} " . hash('fnv1a32', "$name.$property_name") . "\n"); endforeach ?>
<?php
assert(hash('fnv1a32', 'Button.text')  == 'e2f86876');
assert(hash('fnv1a32', 'Button.color') == '22146540');
?>
