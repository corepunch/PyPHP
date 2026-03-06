<?php
// greet.php - CLI script demonstrating getopt() and isset()
//
// Usage:
//   python3 -m pyphp examples/getopt/greet.php [OPTIONS]
//
// Options:
//   -u, --user=NAME      Your name (required)
//   -g, --greeting=TEXT  Custom greeting (default: "Hello")
//   -h, --help           Show this help message

$options = getopt("u:g:h", ["user:", "greeting:", "help"]);

// Show help if --help / -h is given, or if no arguments were provided
if (isset($options['help']) || isset($options['h']) || empty($options)) {
    echo "Usage: python3 -m pyphp examples/getopt/greet.php [OPTIONS]\n";
    echo "Options:\n";
    echo "  -u, --user=NAME      Your name (required)\n";
    echo "  -g, --greeting=TEXT  Custom greeting (default: Hello)\n";
    echo "  -h, --help           Show this help message\n";
    exit(0);
}

// Prefer long option; fall back to short option
$user     = $options['user']     ?? $options['u']     ?? null;
$greeting = $options['greeting'] ?? $options['g']     ?? "Hello";

if (!$user) {
    echo "Error: --user is required\n\n";
    echo "Try: python3 -m pyphp examples/getopt/greet.php --user=YourName\n";
    exit(1);
}

echo "$greeting, $user!\n";
?>
