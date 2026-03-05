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

### 1 — Basic variables and arithmetic

```php
<?php $a = 10; $b = 3; ?>
sum:     <?= $a + $b ?>
product: <?= $a * $b ?>
```

Output:
```
sum:     13
product: 30
```

---

### 2 — Iterating a list

```php
<?php $fruits = ["apple", "banana", "cherry"]; ?>
<?php foreach ($fruits as $fruit): ?>
- <?= $fruit ?>
<?php endforeach ?>
```

Output:
```
- apple
- banana
- cherry
```

---

### 3 — Conditionals

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

---

### 4 — Generating a C header from an XML model

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

### 5 — Generating an HTML table

```php
<?php $rows = [["Alice", 30], ["Bob", 25], ["Carol", 35]]; ?>
<table>
  <tr><th>Name</th><th>Age</th></tr>
<?php foreach ($rows as $i => $row): ?>
  <tr><td><?= $row[0] ?></td><td><?= $row[1] ?></td></tr>
<?php endforeach ?>
</table>
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
| `echo` | `echo $x` | Outputs the value |
| Line comments | `// text` | Mapped to `# text` |
| File inclusion | `require "file.php"` or `require "file.py"` | Executes the file in the current scope |
| Arithmetic | `+`, `-`, `*`, `/`, `%` | Delegated to Python |
| Comparison | `==`, `!=`, `<`, `>`, `<=`, `>=` | Delegated to Python |
| String output filters | `<?= $x \| filter ?>` | Custom post-processing functions |
| HTML comment stripping | `<!-- ... -->` | Stripped before parsing |
| `$argv` | `$argv[1]` | Command-line arguments (index 0 = first real arg) |
| XML dot-access wrapper | `E` class | Lets `$el->attr` work on XML elements |

---

## Not Yet Supported

The following PHP features are not currently translated and are on the roadmap:

| Feature | PHP syntax | Status |
|---|---|---|
| String interpolation | `"Hello $name"` | ⏳ Planned |
| String concatenation operator | `$a . $b` | ⏳ Planned (use Python `+` for now) |
| PHP ternary operator | `$a ? $b : $c` | ⏳ Planned (Python `b if a else c` works) |
| `include` / `require_once` | `include "file.php"` | ⏳ Planned |
| Type casting | `(int)$x`, `(string)$x` | ⏳ Planned |
| PHP string functions | `strlen()`, `str_replace()`, … | ⏳ Planned |
| PHP array functions | `array_map()`, `array_filter()`, … | ⏳ Planned |
| `switch` / `case` | `switch ($x) { case 1: ... }` | ⏳ Planned |
| Class / function definitions in templates | `function foo() { ... }` | ⏳ Planned |
| `list()` assignment | `list($a, $b) = $arr` | ⏳ Planned |

> **Tip:** Because the code inside `<?php ?>` tags is executed as Python, you can use any Python expression or built-in directly — `len()`, `range()`, `sorted()`, list comprehensions, etc.

---

## License

MIT — see [LICENSE](LICENSE).
