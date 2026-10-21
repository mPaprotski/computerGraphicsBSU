package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"flag"
	"fmt"
	"image"
	_ "image/jpeg"
	"image/png"
	"lab2/internal/processing"
	"lab2/web"
	"log"
	"net/http"
	"strconv"
)

func process(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Требуется POST", 405)
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, 12<<20)
	if err := r.ParseMultipartForm(12 << 20); err != nil {
		http.Error(w, "Не удалось прочитать файл (максимум 12 МиБ)", 400)
		return
	}
	defer r.MultipartForm.RemoveAll()
	f, _, err := r.FormFile("image")
	if err != nil {
		http.Error(w, "Выберите изображение", 400)
		return
	}
	defer f.Close()
	var raw bytes.Buffer
	if _, err = raw.ReadFrom(f); err != nil {
		http.Error(w, "Ошибка чтения", 400)
		return
	}
	cfg, _, err := image.DecodeConfig(bytes.NewReader(raw.Bytes()))
	if err != nil || cfg.Width < 1 || cfg.Height < 1 || cfg.Width > 4096 || cfg.Height > 4096 || int64(cfg.Width)*int64(cfg.Height) > 4_000_000 {
		http.Error(w, "Нужен PNG/JPEG до 4 млн пикселей, сторона до 4096", 400)
		return
	}
	src, _, err := image.Decode(bytes.NewReader(raw.Bytes()))
	if err != nil {
		http.Error(w, "Ошибка декодирования", 400)
		return
	}
	var result image.Image
	t := -1
	switch r.FormValue("method") {
	case "manual":
		t, err = strconv.Atoi(r.FormValue("threshold"))
		if err != nil || t < 0 || t > 255 {
			http.Error(w, "Порог: 0–255", 400)
			return
		}
		result = processing.Threshold(src, t)
	case "otsu":
		t = processing.Otsu(src)
		result = processing.Threshold(src, t)
	case "mean", "gaussian":
		size, e := strconv.Atoi(r.FormValue("size"))
		sigma, se := strconv.ParseFloat(r.FormValue("sigma"), 64)
		if e != nil || (size != 3 && size != 5 && size != 7 && size != 9 && size != 15) || se != nil || !(sigma >= 0.1 && sigma <= 10) {
			http.Error(w, "Некорректные параметры фильтра", 400)
			return
		}
		result = processing.Blur(src, size, sigma, r.FormValue("method") == "gaussian")
	default:
		http.Error(w, "Неизвестный метод", 400)
		return
	}
	var buf bytes.Buffer
	if err := png.Encode(&buf, result); err != nil {
		http.Error(w, "Ошибка кодирования", 500)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{"image": "data:image/png;base64," + base64.StdEncoding.EncodeToString(buf.Bytes()), "threshold": t, "width": cfg.Width, "height": cfg.Height})
}
func main() {
	addr := flag.String("addr", "127.0.0.1:8080", "Адрес сервера")
	flag.Parse()
	mux := http.NewServeMux()
	mux.HandleFunc("/api/process", process)
	mux.Handle("/", http.FileServer(http.FS(web.Files)))
	fmt.Printf("Лабораторная 2: http://%s\n", *addr)
	log.Fatal(http.ListenAndServe(*addr, mux))
}
