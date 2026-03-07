<?php
// ── Basic try/catch ─────────────────────────────────────────────────────────

try {
    throw new Exception("something went wrong");
} catch (Exception $e) {
    $msg = $e->getMessage();
}
assert($msg == "something went wrong");

// ── Exception with code ─────────────────────────────────────────────────────

try {
    throw new Exception("error", 42);
} catch (Exception $e) {
    $code = $e->getCode();
    $msg2 = $e->getMessage();
}
assert($code == 42);
assert($msg2 == "error");

// ── try without exception ───────────────────────────────────────────────────

$result = "ok";
try {
    $result = "changed";
} catch (Exception $e) {
    $result = "caught";
}
assert($result == "changed");

// ── re-throw in catch ────────────────────────────────────────────────────────

$caught_msg = "";
try {
    try {
        throw new Exception("inner error");
    } catch (Exception $e) {
        $caught_msg = $e->getMessage();
        throw new Exception("re-thrown: " . $caught_msg);
    }
} catch (Exception $e) {
    $outer_msg = $e->getMessage();
}
assert($caught_msg == "inner error");
assert($outer_msg == "re-thrown: inner error");

// ── finally block ────────────────────────────────────────────────────────────

$finally_ran = false;
try {
    $x = 1 + 1;
} finally {
    $finally_ran = true;
}
assert($finally_ran == true);

// ── finally with exception ────────────────────────────────────────────────────

$finally_ran2 = false;
$caught2 = false;
try {
    throw new Exception("test");
} catch (Exception $e) {
    $caught2 = true;
} finally {
    $finally_ran2 = true;
}
assert($caught2 == true);
assert($finally_ran2 == true);

// ── RuntimeException ─────────────────────────────────────────────────────────

$rte_msg = "";
try {
    throw new RuntimeException("runtime error");
} catch (RuntimeException $e) {
    $rte_msg = $e->getMessage();
}
assert($rte_msg == "runtime error");
