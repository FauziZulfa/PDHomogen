from flask import Flask, render_template, request, jsonify
from sympy import (symbols, sympify, simplify, latex, integrate, log, exp,
                   Rational, S, logcombine, Mul, E, cancel, together, Integral)
import traceback

app = Flask(__name__)
x, y, v, t = symbols('x y v t')


def perbaiki_latex(s):
    """Ganti notasi LaTeX SymPy dengan notasi matematika standar."""
    s = s.replace('\\log', '\\ln')
    s = s.replace('\\operatorname{atan}', '\\arctan')
    s = s.replace('\\operatorname{asin}', '\\arcsin')
    s = s.replace('\\operatorname{acos}', '\\arccos')
    return s


def coba_ekstrak_log(ekspresi):
    """Cek apakah ekspresi = c * log(g). Kembalikan (True, c, g) atau (False,_,_)."""
    gabungan = logcombine(ekspresi, force=True)
    if gabungan.func == log:
        return True, S(1), gabungan.args[0]
    if gabungan.is_Mul:
        koef, bagian_log = S(1), None
        for a in gabungan.args:
            if a.func == log:
                if bagian_log is not None:
                    return False, None, None
                bagian_log = a
            else:
                koef *= a
        if bagian_log is not None:
            return True, koef, bagian_log.args[0]
    return False, None, None


def selesaikan_pd_homogen(str_pers, pakai_awal=False, x0_val=None, y0_val=None):
    """Selesaikan PD homogen derajat 0: dy/dx = f(x,y)"""
    langkah = []
    str_pers = str_pers.replace('^', '**')

    try:
        f = sympify(str_pers, locals={'x': x, 'y': y, 'e': E})
    except Exception:
        return {'error': 'Tidak dapat memparse persamaan. Gunakan format seperti: (x+y)/(x-y)'}

    # Validasi: hanya x dan y yang diizinkan
    diizinkan = {x, y}
    variabel_lain = f.free_symbols - diizinkan
    if variabel_lain:
        nama = ', '.join(str(s) for s in variabel_lain)
        return {'error': f'Variabel tidak diizinkan: {nama}. Hanya x dan y yang diperbolehkan.'}

    # Langkah 1: Persamaan awal
    langkah.append({'title': 'Langkah 1: Persamaan yang Diberikan',
                    'latex': perbaiki_latex(f'\\frac{{dy}}{{dx}} = {latex(f)}')})

    # Langkah 2: Uji kehomogenan
    f_cek = f.subs([(x, t * x), (y, t * y)])
    f_sederhana = simplify(f_cek)
    adalah_homogen = t not in f_sederhana.free_symbols

    langkah.append({
        'title': 'Langkah 2: Uji Kehomogenan (substitusi x→tx, y→ty)',
        'latex': perbaiki_latex(f'f(tx, ty) = {latex(f_cek)}'),
        'latex2': perbaiki_latex(f'= {latex(f_sederhana)}'),
        'result': 'Karena f(tx, ty) = f(x, y), persamaan homogen derajat 0 ✓' if adalah_homogen
                  else 'f(tx, ty) ≠ f(x, y), persamaan BUKAN homogen derajat 0 ✗'
    })
    if not adalah_homogen:
        return {'error': 'Persamaan bukan homogen derajat 0.', 'steps': langkah}

    # Langkah 3: Substitusi y = vx
    f_v = simplify(f.subs(y, v * x))
    langkah.append({'title': 'Langkah 3: Substitusi y = vx  →  dy/dx = v + x·dv/dx',
                    'latex': perbaiki_latex(f'v + x\\frac{{dv}}{{dx}} = {latex(f_v)}')})

    # Langkah 4: Pemisahan variabel
    h_v = simplify(f_v - v)

    if h_v == 0:
        langkah.append({'title': 'Langkah 4: Pemisahan Variabel',
                        'latex': 'x\\frac{dv}{dx} = 0 \\implies v = C'})
        langkah.append({'title': 'Langkah 5: Substitusi Balik v = y/x',
                        'latex': '\\frac{y}{x} = C \\implies y = Cx'})
        nilai_c = None
        if pakai_awal and x0_val is not None and y0_val is not None:
            nilai_c = perbaiki_latex(latex(simplify(S(y0_val) / S(x0_val))))
        return {'solution_latex': 'y = Cx', 'c_expression': 'C = \\frac{y}{x}',
                'c_value': nilai_c,
                'particular': f'y = {nilai_c} \\cdot x' if nilai_c else None,
                'steps': langkah}

    langkah.append({
        'title': 'Langkah 4: Pemisahan Variabel',
        'latex': perbaiki_latex(f'x\\frac{{dv}}{{dx}} = {latex(h_v)}'),
        'latex2': perbaiki_latex(f'\\frac{{dv}}{{{latex(h_v)}}} = \\frac{{dx}}{{x}}')
    })

    # Langkah 5: Integrasi kedua ruas
    hasil_integral = simplify(integrate(S(1) / h_v, v))
    langkah.append({
        'title': 'Langkah 5: Integrasi Kedua Ruas',
        'latex': perbaiki_latex(f'\\int \\frac{{dv}}{{{latex(h_v)}}} = \\int \\frac{{dx}}{{x}}'),
        'latex2': perbaiki_latex(f'{latex(hasil_integral)} = \\ln|x| + C')
    })

    # Cek apakah integral tidak bisa dievaluasi secara analitik
    ada_integral_mentah = hasil_integral.has(Integral)

    # Langkah 6: Cek apakah bisa dieksponensiasi (semua suku ln)
    if not ada_integral_mentah:
        adalah_log, koef, bag_dalam = coba_ekstrak_log(hasil_integral)
    else:
        adalah_log, koef, bag_dalam = False, None, None

    if adalah_log and simplify(koef - 1) == 0:
        # ln(g(v)) = ln|x| + C  =>  g(v) = Cx
        bag_dalam_xy = simplify(bag_dalam.subs(v, y / x))
        ekspresi_c = cancel(together(bag_dalam_xy / x))
        langkah.append({
            'title': 'Langkah 6: Eksponensiasi (eliminasi ln)',
            'latex': perbaiki_latex(f'\\ln({latex(bag_dalam)}) = \\ln|x| + C'),
            'latex2': perbaiki_latex(f'{latex(bag_dalam)} = e^C \\cdot |x| = C \\cdot x')
        })
        langkah.append({
            'title': 'Langkah 7: Substitusi Balik v = y/x',
            'latex': perbaiki_latex(f'{latex(bag_dalam_xy)} = Cx')
        })
        solusi_latex = perbaiki_latex(f'{latex(bag_dalam_xy)} = Cx')
        ekspresi_c_latex = perbaiki_latex(f'C = {latex(ekspresi_c)}')

        nilai_c = None
        solusi_khusus = None
        if pakai_awal and x0_val is not None and y0_val is not None:
            try:
                x0, y0 = S(x0_val), S(y0_val)
                hsl_c = simplify(ekspresi_c.subs([(x, x0), (y, y0)]))
                nilai_c = perbaiki_latex(latex(hsl_c))
                solusi_khusus = perbaiki_latex(f'{latex(bag_dalam_xy)} = {latex(hsl_c)} \\cdot x')
            except Exception:
                nilai_c = 'Error'

        return {'solution_latex': solusi_latex, 'c_expression': ekspresi_c_latex,
                'c_value': nilai_c, 'particular': solusi_khusus, 'steps': langkah}

    elif adalah_log and simplify(koef - 1) != 0:
        # c*ln(g(v)) = ln|x|+C => g(v)^c = Cx
        bag_dalam_xy = simplify(bag_dalam.subs(v, y / x))
        pangkat = simplify(koef)
        ekspresi_c = cancel(together(bag_dalam_xy**pangkat / x))
        langkah.append({
            'title': 'Langkah 6: Eksponensiasi (eliminasi ln)',
            'latex': perbaiki_latex(f'{latex(pangkat)} \\cdot \\ln({latex(bag_dalam)}) = \\ln|x| + C'),
            'latex2': perbaiki_latex(f'{latex(bag_dalam)}^{{{latex(pangkat)}}} = C \\cdot x')
        })
        langkah.append({
            'title': 'Langkah 7: Substitusi Balik v = y/x',
            'latex': perbaiki_latex(f'{latex(bag_dalam_xy)}^{{{latex(pangkat)}}} = Cx')
        })
        solusi_latex = perbaiki_latex(f'{latex(bag_dalam_xy)}^{{{latex(pangkat)}}} = Cx')
        ekspresi_c_latex = perbaiki_latex(f'C = {latex(ekspresi_c)}')

        nilai_c = None
        solusi_khusus = None
        if pakai_awal and x0_val is not None and y0_val is not None:
            try:
                x0, y0 = S(x0_val), S(y0_val)
                hsl_c = simplify(ekspresi_c.subs([(x, x0), (y, y0)]))
                nilai_c = perbaiki_latex(latex(hsl_c))
                solusi_khusus = perbaiki_latex(f'{latex(bag_dalam_xy)}^{{{latex(pangkat)}}} = {latex(hsl_c)} \\cdot x')
            except Exception:
                nilai_c = 'Error'

        return {'solution_latex': solusi_latex, 'c_expression': ekspresi_c_latex,
                'c_value': nilai_c, 'particular': solusi_khusus, 'steps': langkah}

    else:
        # Solusi non-log
        if ada_integral_mentah:
            # Integral tidak bisa dihitung analitik — tetap dalam v
            langkah.append({
                'title': 'Langkah 6: Solusi Umum (dalam v)',
                'latex': perbaiki_latex(f'{latex(hasil_integral)} = \\ln|x| + C'),
                'latex2': 'v = \\frac{y}{x}'
            })
            solusi_latex = perbaiki_latex(f'{latex(hasil_integral)} = \\ln|x| + C \\;\\; \\left(v = \\frac{{y}}{{x}}\\right)')
            ekspresi_c_latex = perbaiki_latex(f'C = {latex(hasil_integral)} - \\ln|x| \\;\\; \\left(v = \\frac{{y}}{{x}}\\right)')

            nilai_c = None
            solusi_khusus = None
            if pakai_awal and x0_val is not None and y0_val is not None:
                try:
                    x0, y0 = S(x0_val), S(y0_val)
                    v0 = S(y0_val) / S(x0_val)
                    hsl_c = simplify(hasil_integral.subs(v, v0) - log(abs(x0)))
                    nilai_c = perbaiki_latex(latex(hsl_c))
                    solusi_khusus = perbaiki_latex(f'{latex(hasil_integral)} = \\ln|x| + {latex(hsl_c)} \\;\\; \\left(v = \\frac{{y}}{{x}}\\right)')
                except Exception:
                    nilai_c = 'Error'
        else:
            # Integral terhitung — substitusi v = y/x
            sol_xy = simplify(hasil_integral.subs(v, y / x))
            langkah.append({
                'title': 'Langkah 6: Substitusi Balik v = y/x',
                'latex': perbaiki_latex(f'{latex(sol_xy)} = \\ln|x| + C')
            })
            langkah.append({
                'title': 'Langkah 7: Solusi Umum',
                'latex': perbaiki_latex(f'{latex(sol_xy)} = \\ln|x| + C'),
                'latex2': perbaiki_latex(f'C = {latex(sol_xy)} - \\ln|x|')
            })
            solusi_latex = perbaiki_latex(f'{latex(sol_xy)} = \\ln|x| + C')
            ekspresi_c_latex = perbaiki_latex(f'C = {latex(sol_xy)} - \\ln|x|')

            nilai_c = None
            solusi_khusus = None
            if pakai_awal and x0_val is not None and y0_val is not None:
                try:
                    x0, y0 = S(x0_val), S(y0_val)
                    hsl_c = simplify(sol_xy.subs([(x, x0), (y, y0)]) - log(abs(x0)))
                    nilai_c = perbaiki_latex(latex(hsl_c))
                    solusi_khusus = perbaiki_latex(f'{latex(sol_xy)} = \\ln|x| + {latex(hsl_c)}')
                except Exception:
                    nilai_c = 'Error'

        return {'solution_latex': solusi_latex, 'c_expression': ekspresi_c_latex,
                'c_value': nilai_c, 'particular': solusi_khusus, 'steps': langkah}


# ─── Quiz ─────────────────────────────────────────────────────────────────────
QUIZ = [
    {
        "id": 1,
        "question": "Solusi umum dari \\(\\frac{dy}{dx} = \\frac{y}{x}\\) adalah:",
        "options": [
            "\\(y = x + C\\)",
            "\\(y = Cx\\)",
            "\\(y = Cx^2\\)",
            "\\(y = \\frac{C}{x}\\)",
            "\\(y = x \\ln|x| + C\\)"
        ],
        "answer": 1,
        "explanation": "Substitusi \\(y=vx\\): \\(v + x\\frac{dv}{dx} = v\\), sehingga \\(x\\frac{dv}{dx}=0\\), maka \\(v=C\\), jadi \\(y=Cx\\)."
    },
    {
        "id": 2,
        "question": "Solusi umum dari \\(\\frac{dy}{dx} = \\frac{x+y}{x}\\) adalah:",
        "options": [
            "\\(y = Cx\\)",
            "\\(y = x^2 + Cx\\)",
            "\\(y = x \\ln|x| + Cx\\)",
            "\\(y = \\frac{x+C}{x}\\)",
            "\\(y = x \\cdot e^x + C\\)"
        ],
        "answer": 2,
        "explanation": "Substitusi \\(y=vx\\): \\(v+x\\frac{dv}{dx}=1+v\\), maka \\(x\\frac{dv}{dx}=1\\). Integrasikan: \\(v=\\ln|x|+C\\), jadi \\(y=x\\ln|x|+Cx\\)."
    },
    {
        "id": 3,
        "question": "Solusi umum dari \\(\\frac{dy}{dx} = \\frac{x+2y}{x}\\) adalah:",
        "options": [
            "\\(y = Cx^2\\)",
            "\\(x + y = Cx^2\\)",
            "\\(y = 2x \\ln|x| + Cx\\)",
            "\\(x - y = Cx^2\\)",
            "\\(y = x + Cx^2\\)"
        ],
        "answer": 1,
        "explanation": "Substitusi \\(y=vx\\): \\(x\\frac{dv}{dx}=1+v\\). Integrasikan: \\(\\ln|1+v|=\\ln|x|+C\\), sehingga \\(1+v=Cx\\), maka \\(x+y=Cx^2\\)."
    },
    {
        "id": 4,
        "question": "Solusi umum dari \\(\\frac{dy}{dx} = \\frac{2y}{x}\\) adalah:",
        "options": [
            "\\(y = 2x + C\\)",
            "\\(y = Ce^{2x}\\)",
            "\\(y = Cx\\)",
            "\\(y = Cx^2\\)",
            "\\(y = 2Cx\\)"
        ],
        "answer": 3,
        "explanation": "Substitusi \\(y=vx\\): \\(x\\frac{dv}{dx}=v\\). Integrasikan: \\(\\ln|v|=\\ln|x|+C\\), sehingga \\(v=Cx\\), maka \\(y=Cx^2\\)."
    },
    {
        "id": 5,
        "question": "Solusi umum dari \\(\\frac{dy}{dx} = \\frac{x^2+y^2}{2xy}\\) adalah:",
        "options": [
            "\\(x^2 + y^2 = Cx\\)",
            "\\(x^2 - y^2 = Cx\\)",
            "\\(y^2 = Cx\\)",
            "\\(x^2 = Cy\\)",
            "\\(xy = C\\)"
        ],
        "answer": 1,
        "explanation": "Substitusi \\(y=vx\\): \\(x\\frac{dv}{dx}=\\frac{1-v^2}{2v}\\). Integrasikan: \\(-\\ln|1-v^2|=\\ln|x|+C\\), sehingga \\(\\frac{1}{1-v^2}=Cx\\), maka \\(x^2-y^2=Cx\\)."
    },
    {
        "id": 6,
        "question": "Solusi umum dari \\(\\frac{dy}{dx} = \\frac{3x+y}{x}\\) adalah:",
        "options": [
            "\\(y = 3Cx\\)",
            "\\(y = x(3\\ln|x| + C)\\)",
            "\\(y = 3x + C\\)",
            "\\(y = Cx^3\\)",
            "\\(3x + y = Cx^2\\)"
        ],
        "answer": 1,
        "explanation": "Substitusi \\(y=vx\\): \\(x\\frac{dv}{dx}=3\\). Integrasikan: \\(v=3\\ln|x|+C\\), jadi \\(y=x(3\\ln|x|+C)\\)."
    },
    {
        "id": 7,
        "question": "Solusi khusus dari \\(\\frac{dy}{dx} = \\frac{y}{x}\\) dengan \\(y(1) = 2\\) adalah:",
        "options": [
            "\\(y = 2x\\)",
            "\\(y = x + 1\\)",
            "\\(y = 2x^2\\)",
            "\\(y = \\frac{2}{x}\\)",
            "\\(y = x + 2\\)"
        ],
        "answer": 0,
        "explanation": "Solusi umum: \\(y=Cx\\). Substitusi \\(y(1)=2\\): \\(2=C \\cdot 1\\), maka \\(C=2\\). Jadi \\(y=2x\\)."
    },
    {
        "id": 8,
        "question": "Solusi khusus dari \\(\\frac{dy}{dx} = \\frac{x+2y}{x}\\) dengan \\(y(1) = 0\\) adalah:",
        "options": [
            "\\(y = x^2 - x\\)",
            "\\(y = x \\ln|x|\\)",
            "\\(y = x\\)",
            "\\(y = x^2 + x\\)",
            "\\(y = 2x - 1\\)"
        ],
        "answer": 0,
        "explanation": "Solusi umum: \\(x+y=Cx^2\\). Substitusi \\(y(1)=0\\): \\(1+0=C\\), maka \\(C=1\\). Jadi \\(x+y=x^2\\), yaitu \\(y=x^2-x\\)."
    },
    {
        "id": 9,
        "question": "Solusi khusus dari \\(\\frac{dy}{dx} = \\frac{2y}{x}\\) dengan \\(y(1) = 3\\) adalah:",
        "options": [
            "\\(y = 3x\\)",
            "\\(y = 3x^2\\)",
            "\\(y = \\frac{3}{x^2}\\)",
            "\\(y = x^2 + 2\\)",
            "\\(y = 6x\\)"
        ],
        "answer": 1,
        "explanation": "Solusi umum: \\(y=Cx^2\\). Substitusi \\(y(1)=3\\): \\(3=C\\), maka \\(y=3x^2\\)."
    },
    {
        "id": 10,
        "question": "Solusi khusus dari \\(\\frac{dy}{dx} = \\frac{x+y}{x}\\) dengan \\(y(1) = 0\\) adalah:",
        "options": [
            "\\(y = x^2\\)",
            "\\(y = \\ln|x|\\)",
            "\\(y = x \\ln|x|\\)",
            "\\(y = x - 1\\)",
            "\\(y = x + \\ln|x|\\)"
        ],
        "answer": 2,
        "explanation": "Solusi umum: \\(y=x\\ln|x|+Cx\\). Substitusi \\(y(1)=0\\): \\(0=0+C\\), maka \\(C=0\\). Jadi \\(y=x\\ln|x|\\)."
    },
]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/solve', methods=['POST'])
def selesaikan():
    try:
        data = request.json
        str_pers = data.get('equation', '').strip()
        pakai_awal = data.get('useInitial', False)
        x0 = data.get('x0', None)
        y0 = data.get('y0', None)
        if not str_pers:
            return jsonify({'error': 'Persamaan tidak boleh kosong.'}), 400
        hasil = selesaikan_pd_homogen(str_pers, pakai_awal, x0, y0)
        return jsonify(hasil)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Terjadi kesalahan: {str(e)}'}), 500


@app.route('/api/quiz', methods=['GET'])
def get_quiz():
    return jsonify(QUIZ)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
