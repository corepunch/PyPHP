<?php
// Load the XML catalog directly — no helper class, no separate model file.
// simplexml_load_file() is available as a built-in in every PyPHP template.
$catalog = simplexml_load_file("examples/simplexml/catalog.xml");

// ── Pass 1: compute summary statistics ────────────────────────────────────
$totalPages = 0;
$totalPrice = 0.0;
$genres     = [];

foreach ($catalog->book as $book) {
    $totalPages = $totalPages + intval(strval($book->pages));
    $totalPrice = $totalPrice + floatval(strval($book->price));
    $genre = $book['genre'];
    if (!in_array($genre, $genres)) {
        array_push($genres, $genre);
    }
}

$bookCount = count($catalog->book);
$avgPrice  = round($totalPrice / $bookCount, 2);
?><!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Book Catalog</title>
  <style>
    body  { font-family: sans-serif; max-width: 900px; margin: 2rem auto; color: #222; }
    h1    { border-bottom: 3px solid #2c7be5; padding-bottom: .4rem; }
    h2    { margin-top: 2rem; color: #2c7be5; }
    .kpi  { display: flex; gap: 1.5rem; margin: 1.5rem 0; flex-wrap: wrap; }
    .card { background: #eef4ff; border-left: 4px solid #2c7be5;
            padding: .8rem 1.4rem; border-radius: 4px; flex: 1; min-width: 140px; }
    .card .val { font-size: 1.5rem; font-weight: bold; color: #2c7be5; }
    .card .lbl { font-size: .8rem; color: #555; margin-top: .2rem; }
    table { border-collapse: collapse; width: 100%; margin-top: 1rem; }
    th, td { border: 1px solid #ddd; padding: .5rem 1rem; text-align: left; vertical-align: top; }
    th  { background: #2c7be5; color: #fff; }
    tr:nth-child(even) { background: #f7f9fc; }
    tr:hover { background: #ddeeff; }
    .badge { display: inline-block; padding: .15rem .5rem; border-radius: 12px;
             font-size: .75rem; margin: .1rem; background: #d0e8ff; color: #0d4e9e; }
    .oos   { color: #c0392b; font-style: italic; }
    .avail { color: #27ae60; }
  </style>
</head>
<body>
  <h1>📚 Book Catalog</h1>
  <p>Source: <code>catalog.xml</code> — loaded inline with <code>simplexml_load_file()</code></p>

  <div class="kpi">
    <div class="card">
      <div class="val"><?= $bookCount ?></div>
      <div class="lbl">Total Books</div>
    </div>
    <div class="card">
      <div class="val"><?= count($genres) ?></div>
      <div class="lbl">Genres</div>
    </div>
    <div class="card">
      <div class="val"><?= number_format($totalPages) ?></div>
      <div class="lbl">Total Pages</div>
    </div>
    <div class="card">
      <div class="val">$<?= number_format($avgPrice, 2) ?></div>
      <div class="lbl">Avg. Price</div>
    </div>
  </div>

  <h2>All Books</h2>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Title</th>
        <th>Author</th>
        <th>Year</th>
        <th>Pages</th>
        <th>Price</th>
        <th>Genre</th>
        <th>Tags</th>
        <th>Status</th>
      </tr>
    </thead>
    <tbody>
<?php foreach ($catalog->book as $book): ?>
      <tr>
        <td><?= $book['id'] ?></td>
        <td><strong><?= strval($book->title) ?></strong></td>
        <td><?= strval($book->author) ?></td>
        <td><?= strval($book->year) ?></td>
        <td><?= number_format(intval(strval($book->pages))) ?></td>
        <td>$<?= number_format(floatval(strval($book->price)), 2) ?></td>
        <td><?= $book['genre'] ?></td>
        <td>
<?php foreach ($book->tags->tag as $tag): ?>
          <span class="badge"><?= strval($tag) ?></span>
<?php endforeach ?>
        </td>
        <td>
<?php if ($book['available'] == "true"): ?>
          <span class="avail">✔ In stock</span>
<?php else: ?>
          <span class="oos">✘ Out of stock</span>
<?php endif ?>
        </td>
      </tr>
<?php endforeach ?>
    </tbody>
  </table>

  <h2>Books by Genre</h2>
  <table>
    <thead>
      <tr><th>Genre</th><th>Titles</th></tr>
    </thead>
    <tbody>
<?php foreach ($genres as $g): ?>
      <tr>
        <td><strong><?= $g ?></strong></td>
        <td>
<?php foreach ($catalog->book as $book): ?>
<?php if ($book['genre'] == $g): ?>
          <?= strval($book->title) ?><br>
<?php endif ?>
<?php endforeach ?>
        </td>
      </tr>
<?php endforeach ?>
    </tbody>
  </table>
</body>
</html>
