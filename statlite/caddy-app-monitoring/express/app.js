const express = require('express');
const app = express();
app.get('/ok', (req, res) => res.send('ok\n'));
app.get('/fail', (req, res) => res.status(500).send('deliberate failure\n'));
app.get('/slow', (req, res) => setTimeout(() => res.send('slow\n'), 250));
app.listen(3000, '127.0.0.1');
