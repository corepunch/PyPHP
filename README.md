# PyPHP

A lightweight **file parser and code generator** that understands PHP-style template tags (`<?php ?>` and `<?= ?>`), powered by Python under the hood.

The idea is simple: write templates that look like PHP, run them with Python, and generate any text-based output — C headers, HTML pages, SQL scripts, configuration files, and more.

---

## Why PyPHP?

PHP was originally a *preprocessor* — it sat in front of plain text and let you sprinkle logic into it.  PyPHP brings that same workflow to Python:

- You write a `.php` template that mixes static text with `<?php ?>` logic tags.
- You run `python pyphp.py template.php` (or call `render()` from Python).
- You get the generated text on stdout (or as a string).

This is especially useful for **generating source code** from structured data.  For example, you can read an XML schema and emit a C header file, or walk a JSON config and produce an HTML report — all from a single readable template.

---

## Quick Start

```
python pyphp.py template.php [key=value ...]
```

Variables passed on the command line are available as `$key` inside the template.

```php
<?= "Hello, World!" ?>
```

```
$ python pyphp.py hello.php
Hello, World!
```

---

## Examples

<table>
<tr><th>PHP</th><th>Output</th></tr>

<tr><td colspan="2"><strong>Basic variables and arithmetic</strong></td></tr>
<tr>
<td>

```php
<?php $a = 10; $b = 3; ?>
sum:     <?= $a + $b ?>
product: <?= $a * $b ?>
```

</td>
<td>

```
sum:     13
product: 30
```

</td>
</tr>

<tr><td colspan="2"><strong>Iterating a list</strong></td></tr>
<tr>
<td>

```php
<?php $fruits = ["apple", "banana", "cherry"]; ?>
<?php foreach ($fruits as $fruit): ?>
- <?= $fruit ?>
<?php endforeach ?>
```

</td>
<td>

```
- apple
- banana
- cherry
```

</td>
</tr>

<tr><td colspan="2"><strong>Conditionals</strong></td></tr>
<tr>
<td>

```php
<?php $score = 85; ?>
<?php if ($score >= 90): ?>
Grade: A
<?php elseif ($score >= 80): ?>
Grade: B
<?php else: ?>
Grade: C
<?php endif ?>
```

</td>
<td>

```
Grade: B
```

</td>
</tr>

<tr><td colspan="2"><strong>Generating an HTML table</strong></td></tr>
<tr>
<td>

```php
<?php $rows = [["Alice", 30], ["Bob", 25], ["Carol", 35]]; ?>
<table>
  <tr><th>Name</th><th>Age</th></tr>
<?php foreach ($rows as $i => $row): ?>
  <tr><td><?= $row[0] ?></td><td><?= $row[1] ?></td></tr>
<?php endforeach ?>
</table>
```

</td>
<td>

```html
<table>
  <tr><th>Name</th><th>Age</th></tr>
  <tr><td>Alice</td><td>30</td></tr>
  <tr><td>Bob</td><td>25</td></tr>
  <tr><td>Carol</td><td>35</td></tr>
</table>
```

</td>
</tr>

<tr><td colspan="2"><strong>String interpolation and concatenation</strong></td></tr>
<tr>
<td>

```php
<?php $first = "Ada"; $last = "Lovelace"; ?>
<?= "Hello, $first!" ?>
<?= $first . " " . $last ?>
<?= "Full name: {$first} {$last}" ?>
```

</td>
<td>

```
Hello, Ada!
Ada Lovelace
Full name: Ada Lovelace
```

</td>
</tr>

<tr><td colspan="2"><strong>Type casting and <code>list()</code> unpacking</strong></td></tr>
<tr>
<td>

```php
<?php $parts = ["42", "3.14"]; ?>
<?php list($n, $f) = $parts; ?>
int:   <?= (int)$n ?>
float: <?= (float)$f ?>
```

</td>
<td>

```
int:   42
float: 3.14
```

</td>
</tr>

<tr><td colspan="2"><strong>PHP string and array functions</strong></td></tr>
<tr>
<td>

```php
<?php $tags = ["PHP", "Python", "Ruby"]; ?>
<?= implode(", ", $tags) ?>
<?= strtolower(implode(" | ", $tags)) ?>
<?php $csv = "one,two,three"; ?>
<?= count(explode(",", $csv)) ?>
```

</td>
<td>

```
PHP, Python, Ruby
php | python | ruby
3
```

</td>
</tr>

<tr><td colspan="2"><strong>Classes and inheritance</strong></td></tr>
<tr>
<td>

```php
<?php
class Animal {
    public $name;
    public function __construct($name) {
        $this->name = $name;
    }
    public function speak() {
        return $this->name . " says hello";
    }
}
class Dog extends Animal {
    public function speak() {
        return $this->name . " says Woof!";
    }
}
$d = new Dog("Rex");
?>
<?= $d->speak() ?>
```

</td>
<td>

```
Rex says Woof!
```

</td>
</tr>

</table>

---

### Generating a C header from an XML model

This is the canonical use case.  Suppose `model.xml` describes a set of structs:

```xml
<model>
  <struct name="Point">
    <field name="x" type="float"/>
    <field name="y" type="float"/>
  </struct>
  <struct name="Rect">
    <field name="origin" type="Point"/>
    <field name="size"   type="Point"/>
  </struct>
</model>
```

A Python helper `model.py` loads it:

```python
import xml.etree.ElementTree as ET
from pyphp import E   # wraps XML elements so $el->attr works in templates

class Model:
    def __init__(self, path):
        self._root = ET.parse(path).getroot()

    def structs(self):
        # E() enables dot-attribute access: $struct->name instead of struct.get("name")
        return [E(s) for s in self._root.findall("struct")]
```

The template `header.php`.  Inside the template, `$argv[1]` is the first
command-line argument — `model.xml` in the `run` command below:

```php
<?php require "model.py"; ?>
<?php $model = new Model($argv[1]); ?>
<?php foreach ($model->structs() as $struct): ?>
typedef struct <?= $struct->name ?> <?= $struct->name ?>, *lp<?= $struct->name ?>;
struct <?= $struct->name ?> {
<?php foreach ($struct->findall("field") as $field): ?>
    <?= $field->type ?> <?= $field->name ?>;
<?php endforeach ?>
};

<?php endforeach ?>
```

Run it:

```
python pyphp.py header.php model.xml
```

Output:

```c
typedef struct Point Point, *lpPoint;
struct Point {
    float x;
    float y;
};

typedef struct Rect Rect, *lpRect;
struct Rect {
    Point origin;
    Point size;
};
```

---

### Function definitions

```php
<?php
function add($a, $b) {
    return $a + $b;
}
function greet($name) {
    return "Hello, " . $name . "!";
}
function printItems($items) {
    foreach ($items as $item) {
        echo $item . "\n";
    }
}
?>
<?= add(3, 4) ?>
<?= greet("World") ?>
<?php $fruits = ["apple", "banana", "cherry"]; ?>
<?php printItems($fruits); ?>
```

Output:
```
7
Hello, World!
apple
banana
cherry
```

---

## Using PyPHP as a Library

```python
from pyphp import render, render_file, Context

ctx = Context(vars={"title": "Hello", "items": ["a", "b", "c"]})
output = render_file("template.php", ctx)
print(output)
```

You can also register **filters** that post-process expression output:

```python
ctx = Context(
    vars={"name": "world"},
    filters={"upper": str.upper},
)
# In template: <?= $name | upper ?>  →  WORLD
```

---

## Supported PHP Features

| Feature | Syntax | Notes |
|---|---|---|
| Echo shorthand | `<?= $expr ?>` | Outputs the expression |
| Code block | `<?php ... ?>` | Executes arbitrary logic |
| Variables | `$name` | Mapped to Python variables |
| Property / method access | `$obj->prop`, `$obj->method()` | Mapped to `.` |
| Object creation | `new ClassName(args)` | Mapped to `ClassName(args)` |
| Boolean / null literals | `true`, `false`, `null` | Mapped to `True`, `False`, `None` |
| `foreach` (value) | `foreach ($arr as $v):` | Works on lists and any iterable |
| `foreach` (key-value) | `foreach ($arr as $k => $v):` | Works on dicts and lists (index, value) |
| `if` / `elseif` / `else` | `if ($x > 0):` | Standard conditionals |
| `while` | `while ($n > 0):` | Standard loop |
| Block-end keywords | `endif`, `endforeach`, `endwhile`, `endfor` | Closes the nearest open block |
| `count()` | `count($arr)` | Mapped to `len()` |
| `echo` | `echo $x` | Outputs the value (works inside function bodies too) |
| Line comments | `// text` | Mapped to `# text` |
| File inclusion | `require "file.php"` or `require "file.py"` | Executes the file in the current scope |
| Arithmetic | `+`, `-`, `*`, `/`, `%` | Delegated to Python |
| Comparison | `==`, `!=`, `<`, `>`, `<=`, `>=` | Delegated to Python |
| String output filters | `<?= $x \| filter ?>` | Custom post-processing functions |
| HTML comment stripping | `<!-- ... -->` | Stripped before parsing |
| `$argv` | `$argv[1]` | Command-line arguments (index 0 = first real arg) |
| XML dot-access wrapper | `E` class | Lets `$el->attr` work on XML elements |
| String interpolation | `"Hello $name"`, `"Item $arr[0]"`, `"{$name}"` | Double-quoted strings with `$var` become Python f-strings |
| String concatenation | `$a . $b`, `$a .= $b` | Coerces both sides to string (mixed types safe) |
| `include` / `require_once` / `include_once` | `include "file.php"` | Alias for `require`; executes file in current scope |
| Type casting | `(int)$x`, `(float)$x`, `(string)$x`, `(bool)$x` | Mapped to `int()`, `float()`, `str()`, `bool()` |
| `list()` assignment | `list($a, $b) = $arr` | Mapped to Python tuple unpacking |
| Function definitions | `function foo($a, $b) { ... }` | Named functions with parameters; body uses `{}`; supports `return` and `echo` |
| Class definition | `class Foo { ... }` | Mapped to `class Foo:` with body |
| Class inheritance | `class Foo extends Bar { ... }` | Mapped to `class Foo(Bar):` |
| Constructor | `function __construct(...)` | Mapped to `def __init__(...)` |
| Instance property / method | `$this->prop`, `$this->method()` | Mapped to `self.prop` / `self.method()` |
| Parent method call | `parent::method(args)` | Mapped to `super().method(args)` |
| Static method definition | `public static function foo()` | Decorated with `@staticmethod` |
| Static method call | `ClassName::method()` | Mapped to `ClassName.method()` |
| Access modifiers | `public`, `private`, `protected` | Removed (not applicable in Python) |
| Namespace import | `use A\B\C;` / `use A\B\C as D;` | Mapped to `import A.B.C as C` / `import A.B.C as D` |
| PHP string functions | `strlen()`, `strtolower()`, `strtoupper()`, `trim()`, `str_replace()`, `substr()`, `strpos()`, `sprintf()`, `ucfirst()`, `ucwords()`, `str_repeat()`, `str_contains()`, `str_starts_with()`, `str_ends_with()`, `number_format()`, `nl2br()`, `htmlspecialchars()`, `strip_tags()`, `str_split()`, … | Available directly in templates |
| PHP array functions | `implode()`, `explode()`, `in_array()`, `array_merge()`, `array_keys()`, `array_values()`, `array_map()`, `array_filter()`, `array_reverse()`, `array_unique()`, `array_push()`, `array_pop()`, `array_shift()`, `array_slice()`, `array_chunk()`, `array_sum()`, `array_flip()`, `array_search()`, `sort()`, `rsort()`, … | Available directly in templates |
| Math functions | `abs()`, `ceil()`, `floor()`, `round()`, `pow()`, `sqrt()`, `max()`, `min()`, `rand()` | Available directly in templates |
| Type-check / conversion helpers | `intval()`, `floatval()`, `strval()`, `is_array()`, `is_string()`, `is_int()`, `is_numeric()`, `isset()`, `empty()` | Available directly in templates |
| JSON helpers | `json_encode()`, `json_decode()` | Available directly in templates |

---

## Not Yet Supported

The following PHP features are not currently translated and are on the roadmap:

| Feature | PHP syntax | Status |
|---|---|---|
| PHP ternary operator | `$a ? $b : $c` | ⏳ Planned (use Python `$b if $a else $c` for now) |
| `switch` / `case` | `switch ($x) { case 1: ... }` | ⏳ Planned |

> **Tip:** Because the code inside `<?php ?>` tags is executed as Python, you can use any Python expression or built-in directly — `len()`, `range()`, `sorted()`, list comprehensions, etc.

---

## License

MIT — see [LICENSE](LICENSE).
