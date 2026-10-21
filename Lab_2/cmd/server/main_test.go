package main

import (
	"bytes"
	"encoding/json"
	"mime/multipart"
	"net/http/httptest"
	"os"
	"testing"
)

func TestProcessHTTP(t *testing.T) {
	data, err := os.ReadFile("../../web/samples/bimodal.png")
	if err != nil {
		t.Fatal(err)
	}
	for _, method := range []string{"manual", "otsu", "mean", "gaussian", "invalid"} {
		t.Run(method, func(t *testing.T) {
			var body bytes.Buffer
			mw := multipart.NewWriter(&body)
			for k, v := range map[string]string{"method": method, "threshold": "128", "size": "5", "sigma": "1.4"} {
				mw.WriteField(k, v)
			}
			file, _ := mw.CreateFormFile("image", "test.png")
			file.Write(data)
			mw.Close()
			req := httptest.NewRequest("POST", "/api/process", &body)
			req.Header.Set("Content-Type", mw.FormDataContentType())
			w := httptest.NewRecorder()
			process(w, req)
			if method == "invalid" {
				if w.Code != 400 {
					t.Fatal(w.Code)
				}
				return
			}
			if w.Code != 200 {
				t.Fatal(w.Body.String())
			}
			var out struct {
				Image  string
				Width  int
				Height int
			}
			if err := json.Unmarshal(w.Body.Bytes(), &out); err != nil {
				t.Fatal(err)
			}
			if out.Width != 480 || out.Height != 320 || len(out.Image) < 100 {
				t.Fatal("invalid response")
			}
		})
	}
}
