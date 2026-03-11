---
layout: default
title: PHP Compatibility
nav_order: 4
permalink: /compatibility
---

# PHP Language Spec — Feature Coverage

This document maps the PHP language specification to PyPHP's current support.
For each feature, the status is one of:
- ✅ **Supported** — works transparently  
- ⚠️ **Partial** — most cases work; edge-cases documented  
- ❌ **Not Supported** — not yet implemented  

---

## 1. Variables & Data Types

| Feature | PHP Syntax | Status | Notes |
|---|---|---|---|
| Variable declaration | `$name = value;` | ✅ | Mapped to `__name` in Python |
| Integer literals | `$x = 42;` | ✅ | |
| Float literals | `$x = 3.14;` | ✅ | |
| String (single-quoted) | `$s = 'hello';` | ✅ | No interpolation |
| String (double-quoted) | `$s = "Hello $name";` | ✅ | Interpolation supported |
| Boolean `true`/`false` | `$b = true;` | ✅ | Mapped to Python `True`/`False` |
| `null` | `$x = null;` | ✅ | Mapped to Python `None` |
| Arrays (sequential) | `$a = [1, 2, 3];` | ✅ | Python list |
| Arrays (associative) | `$a = ['k' => v];` | ✅ | Python dict |
| `array()` function | `array('k' => v)` | ✅ | Converted to dict/list |
| Heredoc (`<<<`) | `<<<EOT ... EOT` | ❌ | Use multi-line strings |
| Nowdoc (`<<<'`) | `<<<'EOT' ... EOT` | ❌ | Use multi-line strings |
| Type juggling (loose) | `"1" == 1` | ⚠️ | Python strict equality used |

```php
<?php
// Variables and types
$name = "Alice";
$age = 30;
$price = 9.99;
$active = true;
$nothing = null;
$items = [1, 2, 3];
$config = ['host' => 'localhost', 'port' => 3306];

assert($name === "Alice");
assert($age === 30);
assert($items[1] === 2);
assert($config['host'] === "localhost");
?>
```

---

## 2. Constants

| Feature | PHP Syntax | Status | Notes |
|---|---|---|---|
| `define()` | `define('PI', 3.14159);` | ✅ | Converted to Python assignment |
| `const` keyword | `const MAX = 100;` | ✅ | File-level and class-level |
| Built-in constants | `PHP_INT_MAX`, `PHP_EOL`, `M_PI`, `INF`, `NAN` | ✅ | Available in scope |
| `PHP_INT_MAX` | `PHP_INT_MAX` | ✅ | |
| `PHP_EOL` | `PHP_EOL` | ✅ | Platform line ending |

```php
<?php
define('APP_VERSION', '1.0.0');
const MAX_ITEMS = 100;
assert(APP_VERSION == '1.0.0');
assert(MAX_ITEMS == 100);
assert(PHP_EOL == "\n");
assert(M_PI > 3.14);
?>
```

---

## 3. Operators

| Feature | PHP Syntax | Status | Notes |
|---|---|---|---|
| Arithmetic | `+`, `-`, `*`, `/`, `%` | ✅ | |
| Integer division | `intdiv(a, b)` | ✅ | Function call |
| Power | `**` | ✅ | Python native |
| String concat | `$a . $b` | ✅ | Converted to `_cat(a, b)` |
| Concat-assign | `$a .= $b` | ✅ | Converted to `+=` |
| Comparison | `==`, `!=`, `<`, `>`, `<=`, `>=` | ✅ | |
| Strict equality | `===`, `!==` | ✅ | Mapped to `==`, `!=` |
| Logical AND | `&&`, `and` | ✅ | Mapped to `and` |
| Logical OR | `\|\|`, `or` | ✅ | Mapped to `or` |
| Logical NOT | `!`, `not` | ✅ | Mapped to `not` |
| Ternary | `$a ? $b : $c` | ✅ | Converted to Python conditional |
| Null-coalesce | `$a ?? $b` | ✅ | Key-safe |
| Increment | `$x++`, `++$x` | ✅ | Converted to `+= 1` (statement context) |
| Decrement | `$x--`, `--$x` | ✅ | Converted to `-= 1` (statement context) |
| Bitwise | `&`, `\|`, `^`, `~`, `<<`, `>>` | ✅ | Python native |
| Spaceship | `$a <=> $b` | ❌ | Use `(a>b)-(a<b)` |
| Elvis | `$a ?: $b` | ❌ | Use `$a ?? $b` or ternary |

```php
<?php
// Ternary
$x = 5;
$label = $x > 3 ? "big" : "small";
assert($label == "big");

// Null-coalesce
$config = ['timeout' => 30];
$timeout = $config['timeout'] ?? 60;
assert($timeout == 30);
$missing = $config['retry'] ?? 3;
assert($missing == 3);

// Increment/decrement
$i = 0;
$i++;
assert($i == 1);
$i--;
assert($i == 0);
?>
```

---

## 4. Control Structures

### 4.1 Conditionals

| Feature | PHP Syntax | Status | Notes |
|---|---|---|---|
| `if`/`elseif`/`else` | `if ($x) { ... }` | ✅ | |
| Colon-style | `if ($x): ... endif;` | ✅ | |
| Single-line | `if ($x) stmt;` | ✅ | Body expanded to block |

```php
<?php
$score = 85;
if ($score >= 90) {
    $grade = "A";
} elseif ($score >= 80) {
    $grade = "B";
} elseif ($score >= 70) {
    $grade = "C";
} else {
    $grade = "F";
}
assert($grade == "B");
?>
```

### 4.2 Loops

| Feature | PHP Syntax | Status | Notes |
|---|---|---|---|
| `while` | `while ($cond) { }` | ✅ | |
| `do`/`while` | `do { } while ($cond);` | ✅ | Converted to `while True:` |
| C-style `for` | `for ($i=0; $i<n; $i++) { }` | ✅ | Converted to `while` |
| `foreach` (value) | `foreach ($arr as $v)` | ✅ | |
| `foreach` (key-value) | `foreach ($arr as $k => $v)` | ✅ | |
| `break` | `break;` | ✅ | |
| `continue` | `continue;` | ✅ | |
| Colon-style foreach | `foreach ... endforeach;` | ✅ | |
| `for` with colon | `for ... endfor;` | ✅ | |
| `while` with colon | `while ... endwhile;` | ✅ | |

```php
<?php
// C-style for loop
$sum = 0;
for ($i = 1; $i <= 10; $i++) {
    $sum += $i;
}
assert($sum == 55);

// do/while
$n = 1;
do {
    $n *= 2;
} while ($n < 100);
assert($n == 128);

// foreach with key-value
$map = ['a' => 1, 'b' => 2, 'c' => 3];
$result = [];
foreach ($map as $k => $v) {
    $result[] = "$k=$v";
}
assert(implode(",", $result) == "a=1,b=2,c=3");
?>
```

### 4.3 Switch

| Feature | PHP Syntax | Status | Notes |
|---|---|---|---|
| `switch`/`case`/`default` | `switch ($x) { case 1: ... }` | ✅ | Converted to if/elif/else |
| Fall-through | `case 1: case 2: body; break;` | ✅ | |
| `break` in case | `break;` | ✅ | Implicit (no fall-through needed) |

```php
<?php
$day = "Monday";
switch ($day) {
    case "Saturday":
    case "Sunday":
        $type = "weekend";
        break;
    case "Monday":
    case "Friday":
        $type = "bookend";
        break;
    default:
        $type = "midweek";
}
assert($type == "bookend");
?>
```

### 4.4 Exceptions

| Feature | PHP Syntax | Status | Notes |
|---|---|---|---|
| `try`/`catch` | `try { } catch (Type $e) { }` | ✅ | |
| `finally` | `try { } finally { }` | ✅ | |
| `throw` | `throw new Exception("msg");` | ✅ | |
| `throw` variable | `throw $e;` | ✅ | |
| `getMessage()` | `$e->getMessage()` | ✅ | PHP exception hierarchy supported |
| `getCode()` | `$e->getCode()` | ✅ | |
| Exception hierarchy | `RuntimeException`, `LogicException`, … | ✅ | Full PHP hierarchy available |

```php
<?php
function divide($a, $b) {
    if ($b == 0) {
        throw new InvalidArgumentException("Division by zero");
    }
    return $a / $b;
}

try {
    $result = divide(10, 0);
} catch (InvalidArgumentException $e) {
    $error = $e->getMessage();
} finally {
    $done = true;
}
assert($error == "Division by zero");
assert($done == true);
?>
```

---

## 5. Functions

| Feature | PHP Syntax | Status | Notes |
|---|---|---|---|
| Function declaration | `function foo($a, $b) { }` | ✅ | |
| Default parameters | `function foo($a = 10) { }` | ✅ | |
| Return values | `return $val;` | ✅ | |
| Variable-length args | `function foo(...$args)` | ✅ | Python *args |
| Named arguments | `foo(name: value)` | ❌ | |
| Type hints | `function foo(int $a): string` | ⚠️ | Ignored (no runtime enforcement) |
| Closures | `$fn = function($x) { return $x * 2; };` | ✅ | Via braces-to-indent |
| Arrow functions | `fn($x) => $x * 2` | ✅ | Converted to `lambda` |
| Generator functions | `yield $val;` | ✅ | |
| `return` keyword | `return $val;` | ✅ | |

```php
<?php
// Default parameters
function greet($name, $greeting = "Hello") {
    return "$greeting, $name!";
}
assert(greet("Alice") == "Hello, Alice!");
assert(greet("Bob", "Hi") == "Hi, Bob!");

// Closures
$multiplier = function($x, $factor) {
    return $x * $factor;
};
assert($multiplier(5, 3) == 15);

// Arrow functions
$double = fn($x) => $x * 2;
assert($double(7) == 14);

// Generators
function fibonacci() {
    $a = 0;
    $b = 1;
    while (true) {
        yield $a;
        list($a, $b) = [$b, $a + $b];
    }
}
$gen = fibonacci();
$first5 = array_slice(iterator_to_array($gen, false), 0, 5);
?>
```

---

## 6. Classes & Object-Oriented Programming

| Feature | PHP Syntax | Status | Notes |
|---|---|---|---|
| Class definition | `class Foo { }` | ✅ | |
| Constructor | `public function __construct($x)` | ✅ | |
| Instance properties | `$this->prop` | ✅ | |
| Instance methods | `$this->method()` | ✅ | |
| Inheritance | `class Bar extends Foo` | ✅ | |
| `parent::` | `parent::__construct(...)` | ✅ | |
| Static methods | `public static function foo()` | ✅ | |
| Static call | `Foo::method()` | ✅ | |
| Access modifiers | `public`, `private`, `protected` | ✅ | Modifiers stripped (not enforced) |
| Abstract classes | `abstract class Foo` | ✅ | `abstract` keyword stripped |
| Abstract methods | `abstract function foo()` | ✅ | |
| Interfaces | `interface Foo { }` | ❌ | |
| Traits | `trait Foo { }` | ❌ | |
| `instanceof` | `$x instanceof Foo` | ✅ | Python native |
| Class constants | `const FOO = 1;` | ✅ | Class-level attribute |
| `new` keyword | `new ClassName(args)` | ✅ | |

```php
<?php
class Shape {
    protected $color;

    public function __construct($color = "white") {
        $this->color = $color;
    }

    public function getColor() {
        return $this->color;
    }

    public function area() {
        return 0;
    }
}

class Circle extends Shape {
    const PI = 3.14159;

    private $radius;

    public function __construct($radius, $color = "red") {
        parent::__construct($color);
        $this->radius = $radius;
    }

    public function area() {
        return self::PI * $this->radius * $this->radius;
    }
}

$c = new Circle(5);
assert($c->getColor() == "red");
assert(abs($c->area() - 78.53975) < 0.001);
assert($c instanceof Shape);
?>
```

---

## 7. String Functions

| Function | Status | Notes |
|---|---|---|
| `strlen()` | ✅ | |
| `strtolower()` / `strtoupper()` | ✅ | |
| `trim()` / `ltrim()` / `rtrim()` | ✅ | |
| `str_replace()` | ✅ | |
| `substr()` | ✅ | Negative indices supported |
| `strpos()` / `strrpos()` | ✅ | Returns -1 (via Python `find`) |
| `str_contains()` | ✅ | PHP 8.0 |
| `str_starts_with()` / `str_ends_with()` | ✅ | PHP 8.0 |
| `str_repeat()` | ✅ | |
| `str_split()` | ✅ | |
| `str_pad()` | ✅ | `STR_PAD_RIGHT`, `STR_PAD_LEFT`, `STR_PAD_BOTH` |
| `substr_count()` | ✅ | |
| `substr_replace()` | ✅ | |
| `str_word_count()` | ✅ | |
| `chunk_split()` | ✅ | |
| `wordwrap()` | ✅ | |
| `ucfirst()` / `lcfirst()` / `ucwords()` | ✅ | |
| `sprintf()` | ✅ | Full format spec |
| `printf()` | ✅ | Prints to stdout |
| `number_format()` | ✅ | |
| `nl2br()` | ✅ | |
| `htmlspecialchars()` | ✅ | |
| `htmlspecialchars_decode()` | ✅ | |
| `strip_tags()` | ✅ | |
| `chr()` / `ord()` | ✅ | |
| `mb_strtolower()` / `mb_strtoupper()` | ✅ | |
| `mb_strlen()` / `mb_substr()` / `mb_strpos()` | ✅ | |

```php
<?php
// str_pad
assert(str_pad("5", 3, "0", STR_PAD_LEFT) == "005");
assert(str_pad("hi", 6, "-", STR_PAD_BOTH) == "--hi--");

// sprintf with multiple formats
$formatted = sprintf("%-10s %05d %.2f", "item", 42, 3.14159);
assert(str_starts_with($formatted, "item"));

// chr/ord
assert(chr(65) == "A");
assert(ord("Z") == 90);
?>
```

---

## 8. Array Functions

| Function | Status | Notes |
|---|---|---|
| `count()` | ✅ | |
| `implode()` / `join()` | ✅ | |
| `explode()` | ✅ | |
| `in_array()` | ✅ | |
| `array_key_exists()` | ✅ | |
| `array_keys()` / `array_values()` | ✅ | |
| `array_merge()` | ✅ | |
| `array_map()` | ✅ | |
| `array_filter()` | ✅ | |
| `array_reverse()` | ✅ | |
| `array_unique()` | ✅ | |
| `array_push()` / `array_pop()` | ✅ | |
| `array_shift()` / `array_unshift()` | ✅ | |
| `array_slice()` / `array_chunk()` | ✅ | |
| `array_sum()` / `array_product()` | ✅ | |
| `array_flip()` / `array_search()` | ✅ | |
| `array_combine()` / `array_fill()` | ✅ | |
| `array_column()` | ✅ | |
| `array_splice()` | ✅ | |
| `array_pad()` | ✅ | |
| `array_count_values()` | ✅ | |
| `array_key_first()` / `array_key_last()` | ✅ | |
| `sort()` / `rsort()` / `usort()` | ✅ | |
| `ksort()` / `krsort()` | ✅ | |
| `arsort()` / `asort()` / `uasort()` | ✅ | |
| `range()` | ✅ | Numeric and character ranges |
| Array push shorthand | `$arr[] = val;` | ✅ | Converted to `.append()` |
| `compact()` | ⚠️ | Frame inspection; use explicit dict in templates |
| `extract()` | ✅ | Injects array keys as variables into the current scope |

```php
<?php
// range
$nums = range(1, 5);
assert($nums == [1, 2, 3, 4, 5]);
$letters = range('a', 'e');
assert($letters == ['a', 'b', 'c', 'd', 'e']);

// array_column
$users = [
    ['id' => 1, 'name' => 'Alice'],
    ['id' => 2, 'name' => 'Bob'],
];
$names = array_column($users, 'name');
assert($names == ['Alice', 'Bob']);

// Array push shorthand
$items = [];
$items[] = "first";
$items[] = "second";
assert(count($items) == 2);
?>
```

---

## 9. Math Functions

| Function | Status | Notes |
|---|---|---|
| `abs()`, `ceil()`, `floor()`, `round()` | ✅ | |
| `pow()`, `sqrt()` | ✅ | |
| `max()`, `min()` | ✅ | |
| `rand()`, `mt_rand()` | ✅ | |
| `pi()` | ✅ | |
| `intdiv()` | ✅ | Integer division |
| `fmod()` | ✅ | Floating-point modulo |
| `log()`, `log10()`, `log2()` | ✅ | |
| `exp()` | ✅ | |
| `sin()`, `cos()`, `tan()` | ✅ | |
| `asin()`, `acos()`, `atan()`, `atan2()` | ✅ | |
| `deg2rad()`, `rad2deg()` | ✅ | |
| `hypot()` | ✅ | |
| `is_nan()`, `is_infinite()`, `is_finite()` | ✅ | |
| `base_convert()` | ✅ | |
| `bindec()`, `octdec()`, `hexdec()` | ✅ | |
| `decbin()`, `decoct()`, `dechex()` | ✅ | |

---

## 10. Regular Expressions (PCRE)

| Function | Status | Notes |
|---|---|---|
| `preg_match()` | ✅ | With `$matches` capture |
| `preg_match_all()` | ✅ | With `$matches` capture |
| `preg_replace()` | ✅ | `$1`/`${1}` backreferences |
| `preg_replace_callback()` | ✅ | |
| `preg_split()` | ✅ | |
| `preg_quote()` | ✅ | |

> **Note**: `$matches` must be initialized as `$matches = [];` before calling `preg_match()` or `preg_match_all()` since Python cannot populate an undeclared variable by reference.

```php
<?php
// preg_match with capture groups
$matches = [];
preg_match('/(\w+)@(\w+)\.(\w+)/', 'user@example.com', $matches);
assert($matches[1] == 'user');
assert($matches[2] == 'example');
assert($matches[3] == 'com');

// preg_replace with backreference
$result = preg_replace('/(\w+) (\w+)/', '$2 $1', 'Hello World');
assert($result == 'World Hello');
?>
```

---

## 11. Type Functions

| Function | Status | Notes |
|---|---|---|
| `is_array()`, `is_string()`, `is_int()`, `is_float()`, `is_bool()`, `is_null()` | ✅ | |
| `is_numeric()`, `is_object()`, `is_iterable()` | ✅ | |
| `isset()` | ✅ | Safe for missing array keys |
| `empty()` | ✅ | |
| `intval()`, `floatval()`, `strval()`, `boolval()` | ✅ | |
| Type casting | `(int)`, `(float)`, `(string)`, `(bool)`, `(array)` | ✅ | |
| `gettype()` | ❌ | |
| `settype()` | ❌ | |
| `unset()` | ✅ | No-op (Python GC handles it) |

---

## 12. Date/Time Functions

| Function | Status | Notes |
|---|---|---|
| `time()` | ✅ | Current Unix timestamp |
| `mktime()` | ✅ | Create timestamp from date parts |
| `date()` | ✅ | Format codes: `Y`, `m`, `d`, `H`, `i`, `s`, `D`, `l`, `N`, `U`, etc. |
| `strtotime()` | ✅ | Common formats: `Y-m-d`, `d/m/Y`, etc. |
| `microtime()` | ✅ | |

```php
<?php
// Fixed timestamp for testing
$ts = mktime(12, 0, 0, 6, 15, 2023);
assert(date("Y", $ts) == "2023");
assert(date("m", $ts) == "06");
assert(date("d", $ts) == "15");
assert(date("H:i:s", $ts) == "12:00:00");
?>
```

---

## 13. Hashing & Encoding

| Function | Status | Notes |
|---|---|---|
| `md5()` | ✅ | |
| `sha1()` | ✅ | |
| `hash()` | ✅ | SHA-256, MD5, FNV, etc. |
| `crc32()` | ✅ | |
| `base64_encode()` / `base64_decode()` | ✅ | |
| `bin2hex()` / `hex2bin()` | ✅ | |

---

## 14. Output Functions

| Function | Status | Notes |
|---|---|---|
| `echo` | ✅ | Multi-arg supported |
| `<?= expr ?>` shorthand | ✅ | |
| `print` | ✅ | |
| `var_dump()` | ✅ | Prints type and value info |
| `print_r()` | ✅ | Human-readable representation |
| `var_export()` | ✅ | Parseable PHP-style output |

---

## 15. File Inclusion

| Feature | PHP Syntax | Status | Notes |
|---|---|---|---|
| `require` | `require "file.php";` | ✅ | Executes .php or .py file |
| `include` | `include "file.php";` | ✅ | Alias for require |
| `require_once` | `require_once "file.php";` | ✅ | Alias for require |
| `include_once` | `include_once "file.php";` | ✅ | Alias for require |

---

## 16. Miscellaneous

| Feature | PHP Syntax | Status | Notes |
|---|---|---|---|
| Line comments | `// comment` | ✅ | |
| Block comments | `/* comment */` | ✅ | |
| `use` namespace import | `use Some\Namespace\Class;` | ✅ | Converted to Python `import` |
| `exit()` / `die()` | `exit(0);` | ✅ | Flushes output, exits |
| `getopt()` | `getopt("u:h", ["user:"])` | ✅ | |
| `isset()` with `??` | `$a ?? $b` | ✅ | |
| `list()` assignment | `list($a, $b) = $arr;` | ✅ | |
| `$argv` | `$argv[0]` | ✅ | Command-line arguments |
| PHP `<?py ?>` block | `<?py # raw Python ?>` | ✅ | PyPHP extension |
| XML access | `$xml->element` | ✅ | Via SimpleXML wrapper |
| Output filters | `<?= $x \| filter ?>` | ✅ | PyPHP extension |

---

## 17. Not Supported (Roadmap)

| Feature | PHP Syntax | Workaround |
|---|---|---|
| Match expression | `match($x) { 1 => "a", ... }` | Use `switch` or ternary chain |
| Elvis operator | `$a ?: $b` | Use `$a ?? $b` or `$a ? $a : $b` |
| Null-safe operator | `$obj?->method()` | Use `isset($obj) ? $obj->method() : null` |
| Interfaces | `interface Foo { }` | Use abstract classes |
| Traits | `trait Foo { }` | Use class inheritance or mixins |
| Named arguments | `foo(name: value)` | Use positional arguments |
| `extract()` | `extract($arr)` | Now supported — injects array keys as `$variables` |
| `list()` with keys | `list('k' => $v) = $arr` | Use `$v = $arr['k']` |
| `heredoc` / `nowdoc` | `<<<EOT ... EOT` | Use multi-line strings |
| `goto` | `goto label;` | Restructure code |
| Closures binding (`bindTo`) | `$fn->bindTo($obj)` | Use explicit object reference |
| Enums | `enum Suit: string { ... }` | Use class constants |
| Fibers | `$fiber = new Fiber(...)` | Use Python generators |
| `match` with no-match error | `match($x)` throws | Use `switch` with `default` |

---

## Quick-Start Examples

### Example 1: Process a list of data

```php
<?php
$employees = [
    ['name' => 'Alice', 'salary' => 75000, 'dept' => 'Engineering'],
    ['name' => 'Bob',   'salary' => 65000, 'dept' => 'Marketing'],
    ['name' => 'Carol', 'salary' => 80000, 'dept' => 'Engineering'],
    ['name' => 'Dave',  'salary' => 70000, 'dept' => 'Marketing'],
];

// Filter engineering department
$engineers = array_filter($employees, fn($e) => $e['dept'] == 'Engineering');

// Calculate average salary
$total = array_sum(array_column(array_values($engineers), 'salary'));
$avg = $total / count($engineers);

echo "Engineering average salary: $" . number_format($avg) . "\n";
?>
```

### Example 2: String processing with regex

```php
<?php
$text = "Contact us at support@example.com or sales@company.org";

$emails = [];
preg_match_all('/\b[\w.]+@[\w.]+\.\w+\b/', $text, $emails);

foreach ($emails[0] as $email) {
    echo "Found email: $email\n";
}
?>
```

### Example 3: Exception handling

```php
<?php
function parseAge($value) {
    if (!is_numeric($value)) {
        throw new InvalidArgumentException("Age must be a number, got: $value");
    }
    $age = intval($value);
    if ($age < 0 || $age > 150) {
        throw new RangeException("Age $age is out of valid range [0, 150]");
    }
    return $age;
}

$inputs = ["25", "abc", "-5", "200", "42"];
$results = [];

foreach ($inputs as $input) {
    try {
        $results[] = "valid: " . parseAge($input);
    } catch (InvalidArgumentException $e) {
        $results[] = "invalid: " . $e->getMessage();
    } catch (RangeException $e) {
        $results[] = "range error: " . $e->getMessage();
    }
}

foreach ($results as $r) {
    echo $r . "\n";
}
?>
```
