<?php
// nested foreach where the inner loop body (foreach + echo + endforeach)
// lives inside a single php tag — this was the pattern that triggered
// "unindent does not match any outer indentation level" before the fix.

$components = array_combine(["Button", "Label"], [["text", "color"], ["text", "size"]]);
$out = [];
foreach ($components as $name => $props):
  foreach ($props as $prop)
    array_push($out, "{$name}_{$prop}");
  endforeach
endforeach
assert($out == ["Button_text", "Button_color", "Label_text", "Label_size"]);

// same pattern but body uses echo with string interpolation (f-string braces)
$result = [];
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
?>
