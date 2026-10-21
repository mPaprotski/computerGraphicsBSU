package processing

import (
	"image"
	"image/color"
	"testing"
)

func TestThresholdOtsu(t *testing.T) {
	s := image.NewGray(image.Rect(7, 9, 11, 10))
	for i, v := range []uint8{20, 20, 200, 200} {
		s.SetGray(i+7, 9, color.Gray{Y: v})
	}
	v := Otsu(s)
	if v <= 20 || v > 200 {
		t.Fatal(v)
	}
	out := Threshold(s, v)
	for i, w := range []uint8{0, 0, 255, 255} {
		if out.GrayAt(i, 0).Y != w {
			t.Fatal(i)
		}
	}
	if Threshold(s, 20).GrayAt(0, 0).Y != 255 {
		t.Fatal("equality")
	}
}
func TestBlur(t *testing.T) {
	s := image.NewNRGBA(image.Rect(0, 0, 5, 5))
	c := color.NRGBA{40, 80, 120, 128}
	for y := 0; y < 5; y++ {
		for x := 0; x < 5; x++ {
			s.SetNRGBA(x, y, c)
		}
	}
	for _, g := range []bool{false, true} {
		out := Blur(s, 5, 1.4, g)
		for y := 0; y < 5; y++ {
			for x := 0; x < 5; x++ {
				if out.NRGBAAt(x, y) != c {
					t.Fatal("constant changed")
				}
			}
		}
	}
	imp := image.NewGray(image.Rect(0, 0, 5, 5))
	imp.SetGray(2, 2, color.Gray{255})
	box := Blur(imp, 3, 1, false)
	if box.NRGBAAt(2, 2).R != 28 || box.NRGBAAt(1, 1).R != 28 || box.NRGBAAt(0, 0).R != 0 {
		t.Fatal("box weights")
	}
	g := Blur(imp, 3, 1, true)
	if g.NRGBAAt(2, 2).R <= g.NRGBAAt(1, 1).R {
		t.Fatal("Gaussian weights")
	}
}
