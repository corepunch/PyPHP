<?py
# Simulate a "component" object with a getProperties() generator that uses
# Python's single-argument range(n) — mirrors real-world usage where a
# generator defined in a <?py block calls range(n) but the PHP scope has
# overridden `range` with the PHP two-argument version.

class _MockType:
    def __init__(self, kind):
        self.kind = kind

class _MockProperty:
    def __init__(self, component_name, field_name):
        self.id   = field_name
        self.addr = f'{component_name}.{field_name}'
    def __str__(self):
        return self.id

class _MockComponent:
    def __init__(self, name):
        self.name = name
    def getProperties(self):
        # Yield simple scalar properties.
        yield _MockProperty(self.name, 'width'),  _MockType('int')
        yield _MockProperty(self.name, 'height'), _MockType('float')
        # Yield fixed-array properties expanded with single-arg range(n).
        # This is the pattern that previously crashed: range overridden by
        # _php_range which required 2 args; range(3) now works correctly.
        for i in range(3):
            yield _MockProperty(self.name, f'items[{i}]'), _MockType('struct')

__component = _MockComponent('Button')
__name = 'Button'
__rows = []
?>
<?php foreach ($component->getProperties() as $property => $type):
    $rows[] = "DECL(" . $property->id . "," . $name . "," . $property . "," . $property->addr . ",kDataType" . ucfirst($type->kind) . ")";
endforeach;

// Expected: 5 rows (width/int, height/float, items[0..2]/struct).
assert(count($rows) == 5);
assert($rows[0] == 'DECL(width,Button,width,Button.width,kDataTypeInt)');
assert($rows[1] == 'DECL(height,Button,height,Button.height,kDataTypeFloat)');
assert($rows[2] == 'DECL(items[0],Button,items[0],Button.items[0],kDataTypeStruct)');
assert($rows[3] == 'DECL(items[1],Button,items[1],Button.items[1],kDataTypeStruct)');
assert($rows[4] == 'DECL(items[2],Button,items[2],Button.items[2],kDataTypeStruct)');
?>
