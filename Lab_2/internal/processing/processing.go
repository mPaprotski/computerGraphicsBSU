// Package processing implements variant 7 without external image libraries.
package processing

import (
	"image"
	"image/color"
	"math"
)

func Gray(src image.Image) *image.Gray {
	b := src.Bounds()
	out := image.NewGray(image.Rect(0, 0, b.Dx(), b.Dy()))
	for y := 0; y < b.Dy(); y++ {
		for x := 0; x < b.Dx(); x++ {
			c := color.NRGBAModel.Convert(src.At(x+b.Min.X, y+b.Min.Y)).(color.NRGBA)
			v := .299*float64(c.R) + .587*float64(c.G) + .114*float64(c.B)
			out.SetGray(x, y, color.Gray{uint8(math.Round(v))})
		}
	}
	return out
}

// Otsu returns the first intensity in the white class; Threshold uses >=.
func Otsu(src image.Image) int {
	g := Gray(src)
	var h [256]float64
	for _, v := range g.Pix {
		h[v]++
	}
	total := float64(len(g.Pix))
	sum := 0.0
	for i, n := range h {
		sum += float64(i) * n
	}
	weight, sumLeft, best, t := 0.0, 0.0, -1.0, 128
	for i := 0; i < 255; i++ {
		weight += h[i]
		sumLeft += float64(i) * h[i]
		if weight == 0 {
			continue
		}
		right := total - weight
		if right == 0 {
			break
		}
		d := sumLeft/weight - (sum-sumLeft)/right
		score := weight * right * d * d
		if score > best {
			best = score
			t = i + 1
		}
	}
	if best < 0 {
		for i, n := range h {
			if n > 0 {
				return i
			}
		}
	}
	return t
}
func Threshold(src image.Image, t int) *image.Gray {
	g := Gray(src)
	for i, v := range g.Pix {
		if int(v) >= t {
			g.Pix[i] = 255
		} else {
			g.Pix[i] = 0
		}
	}
	return g
}

// Blur uses separable normalized kernels and replicated borders. RGB is
// premultiplied by alpha before convolution to avoid transparent color halos.
func Blur(src image.Image, size int, sigma float64, gaussian bool) *image.NRGBA {
	b := src.Bounds()
	w, h := b.Dx(), b.Dy()
	k := make([]float64, size)
	sum := 0.0
	for i := range k {
		k[i] = 1
		if gaussian {
			d := float64(i - size/2)
			k[i] = math.Exp(-d * d / (2 * sigma * sigma))
		}
		sum += k[i]
	}
	for i := range k {
		k[i] /= sum
	}
	data := make([][4]float64, w*h)
	temp := make([][4]float64, w*h)
	for y := 0; y < h; y++ {
		for x := 0; x < w; x++ {
			r, g, bb, a := src.At(x+b.Min.X, y+b.Min.Y).RGBA()
			data[y*w+x] = [4]float64{float64(r) / 257, float64(g) / 257, float64(bb) / 257, float64(a) / 257}
		}
	}
	clamp := func(v, n int) int {
		if v < 0 {
			return 0
		}
		if v >= n {
			return n - 1
		}
		return v
	}
	for y := 0; y < h; y++ {
		for x := 0; x < w; x++ {
			for j, weight := range k {
				p := data[y*w+clamp(x+j-size/2, w)]
				for c := 0; c < 4; c++ {
					temp[y*w+x][c] += weight * p[c]
				}
			}
		}
	}
	out := image.NewNRGBA(image.Rect(0, 0, w, h))
	byteValue := func(v float64) uint8 { return uint8(math.Max(0, math.Min(255, math.Round(v)))) }
	for y := 0; y < h; y++ {
		for x := 0; x < w; x++ {
			var p [4]float64
			for j, weight := range k {
				v := temp[clamp(y+j-size/2, h)*w+x]
				for c := 0; c < 4; c++ {
					p[c] += weight * v[c]
				}
			}
			c := color.NRGBA{A: byteValue(p[3])}
			if p[3] > 0 {
				c.R = byteValue(p[0] * 255 / p[3])
				c.G = byteValue(p[1] * 255 / p[3])
				c.B = byteValue(p[2] * 255 / p[3])
			}
			out.SetNRGBA(x, y, c)
		}
	}
	return out
}
