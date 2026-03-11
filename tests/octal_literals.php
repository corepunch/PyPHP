<?php
// Tests for octal integer literal conversion (0755 -> 0o755)

// Common Unix permission octal literals
$perm755 = 0755;
assert($perm755 == 493);  // 0o755 = 493 decimal

$perm777 = 0777;
assert($perm777 == 511);  // 0o777 = 511 decimal

$perm644 = 0644;
assert($perm644 == 420);  // 0o644 = 420 decimal

$perm600 = 0600;
assert($perm600 == 384);  // 0o600 = 384 decimal

// Smallest octal (0 with one octal digit)
$oct1 = 01;
assert($oct1 == 1);

$oct7 = 07;
assert($oct7 == 7);

$oct10 = 010;
assert($oct10 == 8);  // 0o10 = 8 decimal

// Plain zero is not affected
$zero = 0;
assert($zero == 0);
