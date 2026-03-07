<?php
// ── Math functions ───────────────────────────────────────────────────────────

// intdiv
assert(intdiv(10, 3) == 3);
assert(intdiv(7, 2) == 3);
assert(intdiv(-7, 2) == -3);

// fmod
assert(abs(fmod(10.5, 3.0) - 1.5) < 0.001);
assert(abs(fmod(7.0, 2.0) - 1.0) < 0.001);

// log
assert(abs(log(M_E) - 1.0) < 0.001);
assert(abs(log(100, 10) - 2.0) < 0.001);
assert(abs(log10(1000) - 3.0) < 0.001);
assert(abs(log2(8) - 3.0) < 0.001);

// exp
assert(abs(exp(0) - 1.0) < 0.001);
assert(abs(exp(1) - M_E) < 0.001);

// is_nan / is_infinite / is_finite
assert(is_nan(sqrt(-1)) == true);    // PHP: sqrt of negative returns NaN
assert(is_finite(3.14) == true);
assert(is_finite(INF) == false);
assert(is_infinite(INF) == true);
assert(is_infinite(3.14) == false);

// Trigonometry
assert(abs(sin(0)) < 0.001);
assert(abs(cos(0) - 1.0) < 0.001);
assert(abs(tan(0)) < 0.001);

// deg2rad / rad2deg
assert(abs(deg2rad(180) - M_PI) < 0.001);
assert(abs(rad2deg(M_PI) - 180.0) < 0.001);

// hypot
assert(abs(hypot(3, 4) - 5.0) < 0.001);

// base conversions
assert(bindec('1010') == 10);
assert(octdec('17') == 15);
assert(hexdec('ff') == 255);
assert(decbin(10) == '1010');
assert(decoct(15) == '17');
assert(dechex(255) == 'ff');
assert(base_convert('ff', 16, 10) == '255');
assert(base_convert('10', 2, 10) == '2');

// ── String functions (extended) ──────────────────────────────────────────────

// str_pad
assert(str_pad("hello", 10) == "hello     ");
assert(str_pad("hello", 10, "*") == "hello*****");
assert(str_pad("hello", 10, "*", STR_PAD_LEFT) == "*****hello");
assert(str_pad("hello", 10, "+-", STR_PAD_BOTH) == "+-hello+-+");

// wordwrap
$long = "The quick brown fox jumped over the lazy dog";
$wrapped = wordwrap($long, 15);
assert(strpos($wrapped, "\n") !== false);

// substr_count
assert(substr_count("hello world hello", "hello") == 2);
assert(substr_count("aaaa", "aa") == 2);
assert(substr_count("hello", "xyz") == 0);

// substr_replace
assert(substr_replace("hello world", "PHP", 6) == "hello PHP");
assert(substr_replace("hello world", "PHP", 6, 5) == "hello PHP");
assert(substr_replace("hello world", "", 5) == "hello");

// chr / ord
assert(chr(65) == "A");
assert(chr(97) == "a");
assert(ord("A") == 65);
assert(ord("hello") == 104);

// ── Encoding ─────────────────────────────────────────────────────────────────

$encoded = base64_encode("Hello, World!");
assert($encoded == "SGVsbG8sIFdvcmxkIQ==");
$decoded = base64_decode($encoded);
assert($decoded == "Hello, World!");

$hex = bin2hex("A");
assert($hex == "41");
$back = hex2bin("41");
assert($back == "A");

// md5 / sha1
$m = md5("hello");
assert(strlen($m) == 32);
assert($m == "5d41402abc4b2a76b9719d911017c592");

$s = sha1("hello");
assert(strlen($s) == 40);

// ── range ────────────────────────────────────────────────────────────────────

$r1 = range(1, 5);
assert($r1 == [1, 2, 3, 4, 5]);

$r2 = range(0, 10, 2);
assert($r2 == [0, 2, 4, 6, 8, 10]);

$r3 = range(5, 1);
assert($r3 == [5, 4, 3, 2, 1]);

$r4 = range('a', 'e');
assert($r4 == ['a', 'b', 'c', 'd', 'e']);
