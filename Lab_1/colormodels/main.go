// Лабораторная работа 1. Цветовые модели: CMYK – RGB – HLS.
// Вся математика преобразований написана на Go (только стандартная библиотека).
// Запуск: go run main.go  →  http://localhost:8080
package main

import (
	"encoding/json"
	"fmt"
	"log"
	"math"
	"net/http"
	"strconv"
	"strings"
)

// clamp ограничивает число диапазоном [lo, hi]: Min отсекает значения выше hi,
// а Max — ниже lo. Например, clamp(120, 0, 100)=100, clamp(-5, 0, 100)=0.
// Допустимые значения не меняются; это ограничение, а не масштабирование.
func clamp(x, lo, hi float64) float64 { return math.Max(lo, math.Min(hi, x)) }

// ---------- CMYK (значения 0..100 %) ----------

// rgbToCMYK переводит аддитивную модель RGB в субтрактивную CMYK.
// RGB описывает интенсивности света: R — красного, G — зелёного, B — синего.
// RGB(0,0,0) — чёрный, RGB(255,255,255) — белый.
// CMYK описывает доли красок: C (cyan) поглощает красную составляющую,
// M (magenta) — зелёную, Y (yellow) — синюю, K (black) затемняет все каналы.
// Используется идеализированная модель без цветовых профилей, характеристик
// бумаги и реальных красок; она не даёт точного прогноза цвета при печати.
// Вход: R,G,B в [0,255]. Выход: [C,M,Y,K] в процентах [0,100].
// Один RGB можно получить из разных CMYK. Здесь выбирается максимально
// возможная общая чёрная составляющая, поэтому CMYK → RGB → CMYK может
// изменить доли красок, сохранив RGB-цвет в пределах погрешности вычислений.
func rgbToCMYK(r, g, b float64) [4]float64 {
	// Нормализуем интенсивности до [0,1]: полная интенсивность теперь равна 1.
	r, g, b = r/255, g/255, b/255
	// Если использовать только цветные краски, их доли равны 1-r, 1-g, 1-b.
	// Общую часть заменяем чёрной: K=min(1-r,1-g,1-b)=1-max(r,g,b).
	k := 1 - math.Max(r, math.Max(g, b))
	// Для чёрного r=g=b=0, K=1. В общей формуле знаменатель 1-K был бы
	// нулевым, поэтому возвращаем 100% чёрной краски без цветных компонентов.
	if k >= 1 { // чёрный цвет
		return [4]float64{0, 0, 0, 100}
	}
	return [4]float64{
		// Из r=(1-C)*(1-K) получаем C=(1-r-K)/(1-K).
		// Аналогично вычисляем M и Y; умножение на 100 переводит доли в проценты.
		// RGB(255,0,0) → CMYK(0,100,100,0).
		// RGB(128,128,128) → примерно CMYK(0,0,0,49.80).
		(1 - r - k) / (1 - k) * 100,
		(1 - g - k) / (1 - k) * 100,
		(1 - b - k) / (1 - k) * 100,
		k * 100,
	}
}

// cmykToRGB выполняет обратное преобразование в той же идеализированной модели.
// Вход: C,M,Y,K в процентах [0,100]. Выход: [R,G,B] в [0,255].
func cmykToRGB(c, m, y, k float64) [3]float64 {
	// Переводим проценты в доли: например, 25% → 0.25.
	c, m, y, k = c/100, m/100, y/100, k/100
	return [3]float64{
		// 1-C — доля красного, оставшаяся после голубой краски; 1-M и 1-Y
		// аналогично задают зелёный и синий. Множитель 1-K затемняет все каналы.
		// При K=1 получается чёрный; при C=M=Y=K=0 — белый.
		// Умножение на 255 возвращает шкалу RGB. Дробные каналы не округляются.
		255 * (1 - c) * (1 - k),
		255 * (1 - m) * (1 - k),
		255 * (1 - y) * (1 - k),
	}
}

// ---------- HLS (H: 0..360°, L и S: 0..100 %) ----------

// hue вычисляет тон по RGB (0..255); общий для HSV и HLS.
// Тон — угол на цветовом круге: красный 0°, жёлтый 60°, зелёный 120°,
// голубой 180°, синий 240°, пурпурный 300°; 360° совпадает с 0°.
// Для вычисления тона нормализация RGB не нужна: масштаб сокращается
// в отношениях разностей каналов. Результат находится в диапазоне [0,360).
func hue(r, g, b float64) float64 {
	// mx и mn — самый сильный и самый слабый каналы; d — разность между ними.
	mx, mn := math.Max(r, math.Max(g, b)), math.Min(r, math.Min(g, b))
	d := mx - mn
	// При R=G=B цвет серый (включая белый и чёрный), тон не определён.
	// Условно выбираем H=0 и исключаем деление на ноль в следующих формулах.
	if d == 0 {
		return 0 // серый: тон не определён
	}
	var h float64
	// Круг состоит из шести секторов по 60°. Максимальный канал определяет
	// пару секторов, отношение разности других каналов к d — положение в ней.
	// Смещения +2 и +4 соответствуют зелёному (120°) и синему (240°).
	// При равных максимальных каналах соседние формулы совпадают на границе.
	switch mx {
	case r:
		// Красная область пересекает границу 0°/360°. Остаток по модулю 6
		// задаёт положение на круге из шести секторов и может быть отрицательным.
		h = 60 * math.Mod((g-b)/d, 6)
	case g:
		h = 60 * ((b-r)/d + 2)
	default:
		h = 60 * ((r-g)/d + 4)
	}
	// math.Mod сохраняет знак аргумента. Переносим отрицательные углы
	// в положительную часть круга: например, -60° становится 300°.
	if h < 0 {
		h += 360
	}
	return h
}

// rgbToHLS вычисляет Hue (тон), Lightness (светлоту), Saturation (насыщенность).
// Эту модель также называют HSL, но здесь порядок компонентов именно [H,L,S].
// Вход: RGB в [0,255]. Выход: H в [0,360), L и S в процентах [0,100].
// Светлота HLS не равна воспринимаемой яркости: одинаковое L у разных тонов
// не означает одинаковую яркость для глаза. Формулы работают непосредственно
// с переданными RGB-каналами, без перевода в линейный свет.
func rgbToHLS(r, g, b float64) [3]float64 {
	// Для светлоты и насыщенности используем экстремумы каналов в шкале [0,1].
	mx, mn := math.Max(r, math.Max(g, b))/255, math.Min(r, math.Min(g, b))/255
	d := mx - mn
	// Светлота — середина между максимальным и минимальным каналами.
	// Чёрный даёт L=0, белый L=1, чистые основные цвета L=0.5.
	l := (mx + mn) / 2
	// Для серого d=0, поэтому S=0. У чёрного и белого также d=0:
	// проверка ниже предотвращает деление на нулевой знаменатель при L=0 или 1.
	s := 0.0
	if d != 0 {
		// Максимальная разность каналов при данном L равна
		// 1-|2L-1| = 2*min(L,1-L): при L<=0.5 это 2L, иначе 2(1-L).
		// Делим фактическую разность d на максимально допустимую.
		// S=1 означает максимальную насыщенность при выбранной светлоте.
		s = d / (1 - math.Abs(2*l-1))
	}
	// H уже в градусах; L и S переводим из долей в проценты.
	// RGB(255,0,0) → HLS(0,50,100); RGB(128,128,128) → HLS(0,50.20,0).
	return [3]float64{hue(r, g, b), l * 100, s * 100}
}

// hlsToRGB восстанавливает RGB по HLS. Вход: H в [0,360], L и S в [0,100].
// Выход: [R,G,B] в [0,255]. Углы 0° и 360° дают один цвет.
func hlsToRGB(h, l, s float64) [3]float64 {
	// H оставляем в градусах, L и S переводим из процентов в доли.
	l, s = l/100, s/100
	// a — половина разности максимального и минимального каналов:
	// d=S*(1-|2L-1|), следовательно a=d/2=S*min(L,1-L).
	// Каналы лежат между L-a и L+a. При S=0 они все равны L;
	// L=0 даёт чёрный, L=1 — белый независимо от тона и насыщенности.
	a := s * math.Min(l, 1-l)
	// Одна периодическая кусочно-линейная функция вычисляет любой канал.
	// Сдвиг n выбирает красный, зелёный или синий вместо ветвления по секторам.
	f := func(n float64) float64 {
		// h/30 разбивает круг на 12 отрезков. Остаток по модулю 12 замыкает
		// круг, а n сдвигает функцию для нужного канала. Это локальная фаза k,
		// не связанная с чёрной составляющей K модели CMYK.
		k := math.Mod(n+h/30, 12)
		// Обозначим t=max(-1,min(k-3,9-k,1)). На [0,2] t=-1;
		// на [2,4] t=k-3; на [4,8] t=1; на [8,10] t=9-k;
		// на [10,12) t=-1. Min строит два наклонных участка и верхнее плато,
		// Max ограничивает функцию снизу значением -1.
		// Канал L-a*t проходит максимум L+a, линейный спад, минимум L-a
		// и линейный рост, смешивая соседние цвета круга. Затем возвращаем
		// масштаб [0,255]. Например, при L=0.5,S=1 каналы лежат между 0 и 255.
		return 255 * (l - a*math.Max(-1, math.Min(math.Min(k-3, 9-k), 1)))
	}
	// Сдвиги 0,8,4 соответствуют R,G,B. Относительно красного сдвиг G
	// эквивалентен -120°, а B — +120°. HLS(0,50,100) → RGB(255,0,0).
	return [3]float64{f(0), f(8), f(4)}
}

// ---------- HTTP ----------

type response struct {
	RGB  [3]float64 `json:"RGB"`
	CMYK [4]float64 `json:"CMYK"`
	HLS  [3]float64 `json:"HLS"`
	Hex  string     `json:"hex"`
}

// convert: /api/convert?model=RGB|CMYK|HLS&v=a,b,c[,d]
// Переводит входную модель в RGB, а затем RGB — во все остальные модели.
// RGB служит промежуточной моделью: CMYK → HLS = CMYK → RGB → HLS,
// а HLS → CMYK = HLS → RGB → CMYK. Отдельные формулы для каждой пары не нужны.
// Пример запроса: /api/convert?model=HLS&v=0,50,100 (красный цвет).
func convert(w http.ResponseWriter, r *http.Request) {
	// Компоненты v идут в порядке выбранной модели: R,G,B; C,M,Y,K; H,L,S.
	// ParseFloat сохраняет дробные входные значения для дальнейших вычислений.
	model := r.URL.Query().Get("model")
	var v []float64
	for _, p := range strings.Split(r.URL.Query().Get("v"), ",") {
		x, err := strconv.ParseFloat(p, 64)
		if err != nil {
			http.Error(w, "bad number", http.StatusBadRequest)
			return
		}
		v = append(v, x)
	}
	// Проверяем модель и количество компонентов. Для CMYK/HLS входные значения
	// ограничиваются допустимыми диапазонами до применения формул.
	// H ограничивается, а не нормализуется по кругу: 400° станет 360°, -10° — 0°.
	var rgb [3]float64
	switch {
	case model == "RGB" && len(v) == 3:
		copy(rgb[:], v)
	case model == "CMYK" && len(v) == 4:
		rgb = cmykToRGB(clamp(v[0], 0, 100), clamp(v[1], 0, 100), clamp(v[2], 0, 100), clamp(v[3], 0, 100))
	case model == "HLS" && len(v) == 3:
		rgb = hlsToRGB(clamp(v[0], 0, 360), clamp(v[1], 0, 100), clamp(v[2], 0, 100))
	default:
		http.Error(w, "bad model or value count", http.StatusBadRequest)
		return
	}
	// Общее ограничение RGB применяется к прямому вводу и результатам формул,
	// в том числе к небольшим выходам за границы из-за погрешности float64.
	for i := range rgb {
		rgb[i] = clamp(rgb[i], 0, 255)
	}
	// Все модели вычисляем из одного RGB без промежуточного округления.
	// Это сохраняет точность дробных каналов; округление применяется только к HEX.
	res := response{
		RGB:  rgb,
		CMYK: rgbToCMYK(rgb[0], rgb[1], rgb[2]),
		HLS:  rgbToHLS(rgb[0], rgb[1], rgb[2]),
		// HEX — шестнадцатеричная запись RGB, а не отдельная цветовая модель.
		// Round округляет каналы до целых, %02X записывает их двумя заглавными
		// цифрами с ведущим нулём: 0 → 00, 15 → 0F, 255 → FF.
		// Порядок #RRGGBB: RGB(255,0,0) → #FF0000. В отличие от массивов
		// ответа HEX теряет дробную часть каналов и используется для показа цвета.
		Hex:  fmt.Sprintf("#%02X%02X%02X", int(math.Round(rgb[0])), int(math.Round(rgb[1])), int(math.Round(rgb[2]))),
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(res)
}

func main() {
	http.HandleFunc("/api/convert", convert)
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		fmt.Fprint(w, page)
	})
	log.Println("http://localhost:8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}

// Интерфейс: только отображение и ввод; все вычисления делает сервер на Go.
const page = `<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Цветовые модели</title>
<style>
:root{--bg:#f6f6f9;--card:#fff;--tx:#1d1d28;--mut:#6b6b7b;--bd:#d9d9e3;--ac:#5b4bdb}
@media (prefers-color-scheme:dark){:root{--bg:#15151c;--card:#1f1f29;--tx:#eeeef5;--mut:#9a9aae;--bd:#34344a;--ac:#8d80ff}}
body{margin:0;background:var(--bg);color:var(--tx);font-family:system-ui,"Segoe UI",Roboto,sans-serif}
main{max-width:980px;margin:0 auto;padding:16px}
h1{font-size:1.3rem;margin:4px 0 12px}
.top{display:flex;gap:16px;flex-wrap:wrap;align-items:center;background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:12px}
#sw{width:140px;height:90px;border-radius:10px;border:1px solid var(--bd)}
input[type=color]{width:64px;height:40px;border:none;background:none;padding:0;cursor:pointer}
#hex{font-family:monospace}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-top:12px}
.m{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:12px}
.m h2{font-size:1rem;margin:0 0 8px}
.row{display:grid;grid-template-columns:22px 1fr 68px;gap:8px;align-items:center;margin:8px 0}
.row label{font-weight:600;color:var(--mut)}
.row input[type=range]{width:100%;accent-color:var(--ac)}
.row input[type=number]{width:100%;box-sizing:border-box;padding:5px;border:1px solid var(--bd);border-radius:6px;background:var(--bg);color:var(--tx)}
</style></head><body><main>
<h1>Цветовые модели: CMYK · RGB · HLS</h1>
<div class="top"><div id="sw"></div>
<div><div style="color:var(--mut);font-size:.85rem">Палитра</div><input type="color" id="pal" value="#5b4bdb"><div id="hex"></div></div></div>
<div class="grid" id="grid"></div>
</main>
<script>
const M={
 CMYK:[["C",100],["M",100],["Y",100],["K",100]],
 RGB:[["R",255],["G",255],["B",255]],
 HLS:[["H",360],["L",100],["S",100]]};
const els={},grid=document.getElementById("grid");
for(const k in M){
 const s=document.createElement("section");s.className="m";s.innerHTML="<h2>"+k+"</h2>";els[k]=[];
 M[k].forEach(([n,mx])=>{
  const r=document.createElement("div");r.className="row";
  r.innerHTML="<label>"+n+"</label><input type='range' min='0' max='"+mx+"' step='any'><input type='number' min='0' max='"+mx+"' step='0.1'>";
  const rg=r.children[1],nm=r.children[2];els[k].push([rg,nm]);
  const h=e=>{let v=parseFloat(e.target.value);if(isNaN(v))return;v=Math.min(mx,Math.max(0,v));
   rg.value=v;if(e.target===rg)nm.value=+v.toFixed(1);send(k)};
  rg.oninput=h;nm.oninput=h;s.appendChild(r)});
 grid.appendChild(s)}
// Изменённая модель k отправляется серверу как источник цвета. Если vals
// не переданы (обычные поля), читаем числовые компоненты этой модели.
// Для палитры vals содержат RGB, разобранный из HEX ниже.
async function send(k,vals){
 vals=vals||els[k].map(e=>parseFloat(e[1].value)||0);
 const res=await fetch("/api/convert?model="+k+"&v="+vals.join(","));
 if(!res.ok)return;const d=await res.json();
 // Обновляем остальные модели данными сервера. Источник k пропускаем:
 // это сохраняет ввод пользователя, например исходные доли CMYK или тон
 // серого цвета, которые обратное преобразование через RGB может изменить.
 // toFixed(1) округляет только показ в числовых полях до десятых;
 // ползунок получает исходное значение x из ответа сервера.
 for(const m in M){if(m===k)continue;
  d[m].forEach((x,i)=>{els[m][i][0].value=x;els[m][i][1].value=+x.toFixed(1)})}
 // Образец и палитра используют HEX с целыми RGB-каналами; вычисления
 // моделей выполнены сервером до этого округления.
 document.getElementById("sw").style.background=d.hex;
 document.getElementById("hex").textContent=d.hex;
 document.getElementById("pal").value=d.hex.toLowerCase()}
document.getElementById("pal").oninput=e=>{const h=e.target.value;
 // HEX имеет вид #RRGGBB. Пары с позиций 1,3,5 — красный, зелёный, синий.
 // parseInt(...,16) переводит каждую пару из шестнадцатеричной записи в число
 // [0,255], например FF → 255. Здесь разбирается формат записи RGB;
 // преобразование в CMYK и HLS затем выполняет сервер через send("RGB",rgb).
 const rgb=[1,3,5].map(i=>parseInt(h.substr(i,2),16));
 rgb.forEach((x,i)=>{els.RGB[i][0].value=x;els.RGB[i][1].value=x});send("RGB",rgb)};
els.RGB.forEach((e,i)=>{const x=[91,75,219][i];e[0].value=x;e[1].value=x});
send("RGB",[91,75,219]);
</script></body></html>`
