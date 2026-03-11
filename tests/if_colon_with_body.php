<?php
// Regression: PHP colon-style if/else block where the if-header tag also
// contains a body statement (on the same line or on the next line of the
// same PHP tag).
//
// Both forms were broken:
//   single-line: _re_block_hdr appended a spurious ':' → SyntaxError
//   multi-line:  _tokens_to_python didn't increment indent for the open block
//                → else/endif landed outside the enclosing loop → NameError

$items = [
    'add'  => ['returns' => 'int',  'args' => ['a', 'b']],
    'noop' => ['returns' => '',     'args' => []],
    'get'  => ['returns' => 'float','args' => ['x']],
];

// ── Form 1: single-line  if (cond): body;  in one block ──────────────────
$out1 = [];
foreach ($items as $name => $item):
    if ($item['returns']): $r = $item['returns'];
        $out1[] = $r;
    else:
        $out1[] = 'void';
    endif;
endforeach;
assert($out1 == ['int', 'void', 'float']);

// ── Form 2: multi-line tag, colon on first line, body on second ───────────
$out2 = [];
foreach ($items as $name => $item):
    if ($item['returns']):
        $r2 = $item['returns'];
        $out2[] = $r2;
    else:
        $out2[] = 'void';
    endif;
endforeach;
assert($out2 == ['int', 'void', 'float']);

// ── Form 3: nested — foreach containing the colon-style if with body ──────
$out3 = [];
foreach ($items as $name => $info):
    if ($info['returns']): $tag = ucfirst($info['returns']);
        $out3[] = $tag;
    else:
        $out3[] = 'void';
    endif;
endforeach;
assert($out3 == ['Int', 'void', 'Float']);

echo "OK\n";
?>
