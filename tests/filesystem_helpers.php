<?php
// ── dirname ──────────────────────────────────────────────────────────────────
assert(dirname('/var/www/html/index.php') == '/var/www/html');
assert(dirname('/var/www/html/') == '/var/www');
assert(dirname('/var/www/html/index.php', 2) == '/var/www');
assert(dirname('/var/www/html/index.php', 3) == '/var');
assert(dirname('file.txt') == '.');

// ── basename ─────────────────────────────────────────────────────────────────
assert(basename('/var/www/html/index.php') == 'index.php');
assert(basename('/var/www/html/index.php', '.php') == 'index');
assert(basename('/var/www/html/') == 'html');
assert(basename('file.txt') == 'file.txt');

// ── pathinfo ─────────────────────────────────────────────────────────────────
$info = pathinfo('/var/www/html/index.php');
assert($info['dirname'] == '/var/www/html');
assert($info['basename'] == 'index.php');
assert($info['extension'] == 'php');
assert($info['filename'] == 'index');

assert(pathinfo('/var/www/html/index.php', PATHINFO_DIRNAME) == '/var/www/html');
assert(pathinfo('/var/www/html/index.php', PATHINFO_BASENAME) == 'index.php');
assert(pathinfo('/var/www/html/index.php', PATHINFO_EXTENSION) == 'php');
assert(pathinfo('/var/www/html/index.php', PATHINFO_FILENAME) == 'index');

// no extension
$info2 = pathinfo('/usr/local/bin/php');
assert($info2['extension'] == '');
assert($info2['filename'] == 'php');

// ── realpath ─────────────────────────────────────────────────────────────────
// realpath of an existing directory should return a non-empty string
$rp = realpath('/tmp');
assert($rp !== false);
assert(strlen($rp) > 0);

// realpath of a non-existent path should return false
assert(realpath('/nonexistent/path/that/does/not/exist') === false);

// ── file_exists / is_file / is_dir ───────────────────────────────────────────
// /tmp always exists as a directory on Linux/macOS
assert(file_exists('/tmp') == true);
assert(is_dir('/tmp') == true);
assert(is_file('/tmp') == false);

// ── file_get_contents / file_put_contents / unlink ───────────────────────────
$tmpfile = sys_get_temp_dir() . '/pyphp_test_' . rand(100000, 999999) . '.txt';
$content = "Hello, PHP filesystem helpers!\nSecond line.\n";
$bytes = file_put_contents($tmpfile, $content);
assert($bytes == strlen($content));
assert(file_exists($tmpfile));
assert(is_file($tmpfile));

$read = file_get_contents($tmpfile);
assert($read == $content);

// append mode
file_put_contents($tmpfile, "Third line.\n", FILE_APPEND);
$read2 = file_get_contents($tmpfile);
assert(str_contains($read2, "Third line."));

// ── file() ───────────────────────────────────────────────────────────────────
$lines = file($tmpfile, FILE_IGNORE_NEW_LINES);
assert(count($lines) >= 3);
assert($lines[0] == "Hello, PHP filesystem helpers!");

$nonempty = file($tmpfile, FILE_SKIP_EMPTY_LINES);
assert(count($nonempty) >= 3);

// ── filesize ─────────────────────────────────────────────────────────────────
$sz = filesize($tmpfile);
assert($sz > 0);

// ── is_readable / is_writable ────────────────────────────────────────────────
assert(is_readable($tmpfile) == true);
assert(is_writable($tmpfile) == true);

// ── unlink ───────────────────────────────────────────────────────────────────
assert(unlink($tmpfile) == true);
assert(file_exists($tmpfile) == false);

// ── mkdir / rmdir / rename / copy ────────────────────────────────────────────
$tmpdir = sys_get_temp_dir() . '/pyphp_testdir_' . rand(100000, 999999);
assert(mkdir($tmpdir) == true);
assert(is_dir($tmpdir) == true);

$src = $tmpdir . '/src.txt';
$dst = $tmpdir . '/dst.txt';
file_put_contents($src, "copy me");
assert(copy($src, $dst) == true);
assert(file_get_contents($dst) == "copy me");

$rn = $tmpdir . '/renamed.txt';
assert(rename($dst, $rn) == true);
assert(file_exists($rn) == true);
assert(file_exists($dst) == false);

unlink($src);
unlink($rn);
assert(rmdir($tmpdir) == true);
assert(is_dir($tmpdir) == false);

// ── sys_get_temp_dir ─────────────────────────────────────────────────────────
$td = sys_get_temp_dir();
assert(strlen($td) > 0);
assert(is_dir($td) == true);

// ── tempnam ──────────────────────────────────────────────────────────────────
$tn = tempnam(sys_get_temp_dir(), 'pyphp_');
assert($tn !== false);
assert(file_exists($tn));
unlink($tn);

// ── glob ─────────────────────────────────────────────────────────────────────
$testsdir = dirname(__FILE__);
$phpfiles = glob($testsdir . '/*.php');
assert(count($phpfiles) > 0);
// the current file should be among them
assert(in_array($testsdir . '/filesystem_helpers.php', $phpfiles));

// ── scandir ──────────────────────────────────────────────────────────────────
$entries = scandir('/tmp');
assert(in_array('.', $entries));
assert(in_array('..', $entries));

// ── DIRECTORY_SEPARATOR / PATH_SEPARATOR ─────────────────────────────────────
assert(strlen(DIRECTORY_SEPARATOR) == 1);
assert(strlen(PATH_SEPARATOR) == 1);

// ── filemtime / touch ────────────────────────────────────────────────────────
$mfile = tempnam(sys_get_temp_dir(), 'pyphp_mtime_');
assert(filemtime($mfile) > 0);
assert(touch($mfile, 1000000000) == true);
assert(filemtime($mfile) == 1000000000);
unlink($mfile);
