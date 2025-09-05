const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.static(path.join(__dirname, 'public')));

app.get('/version', (req, res) => {
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(__dirname, 'package.json'), 'utf8'));
    res.json({
      app: pkg.name,
      version: pkg.version,
      commit: process.env.COMMIT_SHA || null,
      time: new Date().toISOString()
    });
  } catch (e) {
    res.status(500).json({ error: 'version lookup failed', message: String(e) });
  }
});

app.listen(PORT, () => {
  console.log(`Web listening on http://localhost:${PORT}`);
});