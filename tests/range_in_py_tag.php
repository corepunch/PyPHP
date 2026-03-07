<?py
# Simulate a "component" object with a getProperties() generator that uses
# Python's single-argument range(n) — mirrors real-world usage where a
# generator defined in a <?py block calls range(n) but the PHP scope has
# overridden `range` with the PHP two-argument version.

class _MockType:
    def __init__(self, kind):
        self.kind = kind

class _MockProperty:
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return self.name

class _MockComponent:
    def getProperties(self):
        # Yield simple scalar properties.
        yield _MockProperty('width'), _MockType('int')
        yield _MockProperty('height'), _MockType('float')
        # Yield a fixed-array property expanded with single-arg range(n).
        for i in range(3):          # Python-style range — must work in PHP scope
            yield _MockProperty(f'items[{i}]'), _MockType('struct')

__component = _MockComponent()
?>
<?php
// Iterate a Python generator that yields 2-tuples (property, type) exactly
// like the real-world getProperties() in the problem description.
$rows = [];
foreach ($component->getProperties() as $property => $type):
    $rows[] = ucfirst($type->kind) . ':' . (string)$property;
endforeach;

// Expected: width(int), height(float), items[0..2](struct) — 5 rows total.
assert(count($rows) == 5);
assert($rows[0] == 'Int:width');
assert($rows[1] == 'Float:height');
assert($rows[2] == 'Struct:items[0]');
assert($rows[3] == 'Struct:items[1]');
assert($rows[4] == 'Struct:items[2]');
?>
