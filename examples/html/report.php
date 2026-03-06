<?php
$title = 'Sales Report — Q1 2024';
$summary = [
    {"label": "Total Units",   "value": "5,570"},
    {"label": "Total Revenue", "value": '$142,400'},
    {"label": "Top Product",   "value": "Gadget X"},
];
$headers = ["Product", "Units", "Revenue", "Margin"];
$rows = [
    ["Widget A",  "1,200",  '$24,000', "38%"],
    ["Widget B",    "850",  '$17,000', "42%"],
    ["Gadget X",  "3,100",  '$93,000', "61%"],
    ["Gadget Y",    "420",   '$8,400', "55%"],
];
?><!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title><?= $title ?></title>
  <style>
    body  { font-family: sans-serif; max-width: 820px; margin: 2rem auto; color: #333; }
    h1    { border-bottom: 2px solid #4a90d9; padding-bottom: .4rem; }
    .kpi  { display: flex; gap: 1.5rem; margin: 1.5rem 0; }
    .card { background: #f0f6ff; border-left: 4px solid #4a90d9;
            padding: .8rem 1.2rem; border-radius: 4px; flex: 1; }
    .card .val { font-size: 1.6rem; font-weight: bold; color: #4a90d9; }
    .card .lbl { font-size: .85rem; color: #666; margin-top: .2rem; }
    table { border-collapse: collapse; width: 100%; margin-top: 1rem; }
    th, td { border: 1px solid #ddd; padding: .5rem 1rem; text-align: left; }
    th  { background: #4a90d9; color: white; }
    tr:nth-child(even) { background: #f9f9f9; }
    tr:hover { background: #eef4ff; }
  </style>
</head>
<body>
  <h1><?= $title ?></h1>

  <div class="kpi">
<?php foreach ($summary as $item): ?>
    <div class="card">
      <div class="val"><?= $item["value"] ?></div>
      <div class="lbl"><?= $item["label"] ?></div>
    </div>
<?php endforeach ?>
  </div>

  <table>
    <thead>
      <tr>
<?php foreach ($headers as $h): ?>
        <th><?= $h ?></th>
<?php endforeach ?>
      </tr>
    </thead>
    <tbody>
<?php foreach ($rows as $row): ?>
      <tr>
<?php foreach ($row as $cell): ?>
        <td><?= $cell ?></td>
<?php endforeach ?>
      </tr>
<?php endforeach ?>
    </tbody>
  </table>
</body>
</html>
