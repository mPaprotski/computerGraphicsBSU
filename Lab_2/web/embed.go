package web

import "embed"

//go:embed index.html style.css app.js samples/*.png
var Files embed.FS
