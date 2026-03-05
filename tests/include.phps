<?php require "tests/greet_helper.py"; ?>
<?php assert($greeting == "Hi there") ?>
<?php require_once "tests/greet_helper.py"; ?>
<?php assert($greeting == "Hi there") ?>
<?php include "tests/greet_helper.py"; ?>
<?php assert($greeting == "Hi there") ?>
