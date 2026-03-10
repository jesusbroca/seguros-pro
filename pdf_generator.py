"""
Generador de PDFs - Replica exacta de documentos reales
NRE: Mercosur, Certificado de Cobertura, Frente de Póliza (+Anexo)
ATM: Mercosur, Certificado de Cobertura, Tarjeta de Circulación
"""
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable, Image as RLImage, PageBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
import io, os
from datetime import datetime, date

BASE   = os.path.dirname(os.path.abspath(__file__))
LOGOS  = os.path.join(BASE, 'static', 'logos')
FIRMAS = os.path.join(BASE, 'static', 'firmas')

# Colores exactos
C_NRE_COPPER = colors.HexColor('#b87333')
C_NRE_LINE   = colors.HexColor('#cccccc')
C_ATM_DARK   = colors.HexColor('#6b1f3a')
C_BLACK      = colors.black
C_DGRAY      = colors.HexColor('#333333')
C_GRAY       = colors.HexColor('#666666')
C_LGRAY      = colors.HexColor('#999999')
C_WHITE      = colors.white
C_BORDER     = colors.HexColor('#cccccc')
C_TBORDER    = colors.HexColor('#dddddd')

def fmt_fecha(s):
    if not s: return '—'
    try:
        p = s.split('-'); return f"{p[2]}/{p[1]}/{p[0]}"
    except: return s

def fmt_peso(n):
    try: return f"{float(n):,.2f}".replace(',','X').replace('.',',').replace('X','.')
    except: return '0,00'

def img_path(folder, name):
    p = os.path.join(folder, name)
    return p if os.path.exists(p) else None

def draw_img(c, path, x, y, w, h):
    if path and os.path.exists(path):
        try: c.drawImage(path, x, y, w, h, mask='auto')
        except: pass

def cuotas_list(p):
    from app import calcular_cuotas
    return calcular_cuotas(p.get('modalidad','trimestral_unico'),
                           p.get('prima',0), p.get('fecha_inicio',''))

# ═══════════════════════════════════════════════════════════════════════════════
# NRE — CERTIFICADO DE COBERTURA
# ═══════════════════════════════════════════════════════════════════════════════
def nre_cert_cobertura(p):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    def T(x, y, txt, sz=8, bold=False, color=C_BLACK, align='left'):
        c.setFillColor(color)
        c.setFont('Helvetica-Bold' if bold else 'Helvetica', sz)
        if align == 'center': c.drawCentredString(x, y, str(txt or ''))
        elif align == 'right': c.drawRightString(x, y, str(txt or ''))
        else: c.drawString(x, y, str(txt or ''))

    def L(x1,y1,x2,y2, color=C_BORDER, w=0.5):
        c.setStrokeColor(color); c.setLineWidth(w); c.line(x1,y1,x2,y2)

    # ── Logo NRE (izq arriba)
    draw_img(c, img_path(LOGOS,'nre.png'), 14*mm, H-32*mm, 38*mm, 26*mm)

    # ── Info fiscal derecha
    fi = ['C.U.I.T. Nro: 30-71233712-1',
          'Imp. Internos a los Seguros',
          'Iva Responsable Inscripto',
          'Ing. Brutos: CONV MULT. Nro Resp. Inscripto']
    c.setFont('Helvetica', 7); c.setFillColor(C_GRAY)
    for i, f in enumerate(fi):
        c.drawRightString(196*mm, H-14*mm - i*4*mm, f)

    # ── Línea separadora
    L(14*mm, H-33*mm, 196*mm, H-33*mm, C_BORDER, 0.5)

    # ── Título
    T(W/2, H-42*mm, 'CERTIFICADO DE COBERTURA', 14, True, C_BLACK, 'center')
    L(14*mm, H-44.5*mm, 196*mm, H-44.5*mm, C_BORDER, 0.5)

    T(14*mm, H-50*mm, f"Certificado de cobertura a la fecha {fmt_fecha(p.get('fecha_inicio',''))}", 8)

    # ── Datos (dos columnas)
    y = H-59*mm
    vig = f"{fmt_fecha(p.get('fecha_inicio',''))} - {fmt_fecha(p.get('fecha_venc',''))}"

    def row(label, val, x=14*mm, xv=48*mm, yr=0, x2=None, l2=None, v2=None, xv2=None):
        T(x, yr, label+':', 8, True)
        T(xv, yr, val or '—', 8)
        if l2 and x2:
            T(x2, yr, l2+':', 8, True)
            T(xv2 or x2+28*mm, yr, v2 or '—', 8)

    row('Asergurado', (p.get('nombre','')).upper(), yr=y)
    y -= 5.5*mm
    row('Domicilio', p.get('domicilio',''), yr=y,
        x2=105*mm, l2='Sección', v2='Automotores', xv2=128*mm)
    y -= 5.5*mm
    row('C.P.', p.get('cp',''), xv=28*mm, yr=y)
    T(42*mm, y, 'Localidad:', 8, True); T(60*mm, y, p.get('localidad',''), 8)
    T(105*mm, y, 'Propuesta:', 8, True); T(128*mm, y, p.get('npoliza',''), 8)
    y -= 5.5*mm
    row('Provincia', p.get('provincia',''), yr=y,
        x2=105*mm, l2='Endoso', v2='0', xv2=128*mm)
    y -= 5.5*mm
    row('Cond. Iva', p.get('cond_iva','CONSUMIDOR FINAL'), yr=y,
        x2=105*mm, l2='Operación', v2='Emisión', xv2=128*mm)
    y -= 5.5*mm
    row('CUIT / DNI', p.get('dni',''), yr=y,
        x2=105*mm, l2='Fecha de Emisión', v2=fmt_fecha(p.get('fecha_inicio','')), xv2=148*mm)
    y -= 5.5*mm
    T(105*mm, y, 'Lugar:', 8, True); T(128*mm, y, 'C.A.B.A', 8)
    y -= 5.5*mm
    T(105*mm, y, 'Vigencia:', 8, True); T(128*mm, y, vig, 8)
    y -= 5.5*mm
    T(105*mm, y, 'Periodo Facturado:', 8, True); T(148*mm, y, vig, 8)
    y -= 5.5*mm
    T(105*mm, y, 'Moneda:', 8, True); T(128*mm, y, 'Pesos', 8)

    # ── OBJETO DEL SEGURO / SUMAS ASEGURADAS
    y -= 8*mm
    L(14*mm, y+3*mm, 196*mm, y+3*mm, C_BORDER)
    T(14*mm, y-2*mm, 'OBJETO DEL SEGURO:', 9, True)
    T(196*mm, y-2*mm, 'SUMAS ASEGURADAS:', 9, True, align='right')
    L(14*mm, y-4*mm, 196*mm, y-4*mm, C_BORDER)

    y -= 12*mm
    auto = f"{p.get('marca','')} {p.get('modelo','')}"
    row('Marca y Modelo', auto, yr=y)
    y -= 5.5*mm
    row('Tipo de Vehículo', p.get('tipo_vehiculo','Automovil Nacional'), yr=y,
        x2=100*mm, l2='Accesorios', v2='0,00', xv2=130*mm)
    y -= 5.5*mm
    row('Carroceria', p.get('carroceria','Sedan'), yr=y,
        x2=100*mm, l2='Año', v2=p.get('anio',''), xv2=120*mm)
    y -= 5.5*mm
    row('Uso', p.get('uso','PARTICULAR'), yr=y,
        x2=100*mm, l2='Patente', v2=p.get('patente',''), xv2=120*mm)
    y -= 5.5*mm
    row('Motor', p.get('motor',''), yr=y,
        x2=100*mm, l2='Chasis', v2=p.get('chasis',''), xv2=120*mm)

    # ── COBERTURA
    y -= 8*mm
    L(14*mm, y+3*mm, 196*mm, y+3*mm, C_BORDER)
    T(14*mm, y-2*mm, 'COBERTURA:', 8, True); T(46*mm, y-2*mm, 'A', 8)
    y -= 6*mm
    T(14*mm, y, 'ACCESORIOS:', 8, True)
    L(14*mm, y-2*mm, 196*mm, y-2*mm, C_BORDER)
    y -= 6*mm
    T(14*mm, y, 'R.C. por acontecimiento $ 350.000.000  R. 39.927 / 16 SSN', 7.5)
    y -= 4.5*mm
    T(14*mm, y, 'Incluye Seguro Obligatorio de Responsabilidad Civil Resolución Nro 39.927 / 16 SSn', 7.5)

    # ── Footer con firma
    y_foot = 38*mm
    T(14*mm, y_foot, 'NRE SEGUROS S.A', 7.5)
    T(14*mm, y_foot-4.5*mm, 'Corrientes 1464 Piso 4 - C1043AAQ - C.A.B.A.', 7.5)
    T(14*mm, y_foot-9*mm, 'Tel: 011-4345-2551 -www.nre.com.ar', 7.5)

    # Firma NRE
    firma = img_path(FIRMAS, 'firma_nre.png')
    draw_img(c, firma, 130*mm, y_foot-12*mm, 60*mm, 18*mm)

    c.save(); buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════════════════════
# NRE — MERCOSUR
# ═══════════════════════════════════════════════════════════════════════════════
def nre_mercosur(p):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    def T(x, y, txt, sz=8, bold=False, color=C_BLACK, align='left'):
        c.setFillColor(color)
        c.setFont('Helvetica-Bold' if bold else 'Helvetica', sz)
        if align=='center': c.drawCentredString(x,y,str(txt or ''))
        elif align=='right': c.drawRightString(x,y,str(txt or ''))
        else: c.drawString(x,y,str(txt or ''))

    def L(x1,y1,x2,y2,col=C_BORDER,w=0.5):
        c.setStrokeColor(col); c.setLineWidth(w); c.line(x1,y1,x2,y2)

    def BOX(x,y,w2,h2): 
        c.setStrokeColor(C_BORDER); c.setLineWidth(0.5)
        c.rect(x,y-h2,w2,h2)

    # Logo
    draw_img(c, img_path(LOGOS,'nre.png'), 14*mm, H-32*mm, 38*mm, 26*mm)

    # Título
    T(W/2, H-18*mm, 'MERCOSUR / MERCOSUL', 14, True, C_BLACK, 'center')
    L(14*mm, H-33*mm, 196*mm, H-33*mm, C_BORDER, 0.5)

    # Textos bilingüe
    y = H-40*mm
    c.setFont('Helvetica', 7); c.setFillColor(C_BLACK)
    lines_bi = [
        "CERTIFICADO DE APOLICE DE SEGURO DE RESPONSABILIDADE CIVIL DO PROPIETARIO E/DU CONDUTOR DE VEHICULOS DE PASSEIO OU DE ALUGEL NAO",
        "MATRICULADOS O PAIS DE INGRESO EM VIAGEM INTERNACIONAL.",
        "DAÑOS CAUSADOS A PESSOAS OU OJETOS NAO TRANSPORTADOS.",
        "CERTIFICADO DE PÓLIZA DE SEGURO DE RESPONSABILIDAD CIVIL DEL PROPIETARIO Y/O DEL CONDUCTOR DE VEHÍCULOS DE RUTA O ALQUILER NO",
        "MATRICULADOS O PAÍS DE ENTRADA EN VIAJE INTERNACIONAL.",
        "DAÑOS CAUSADOS A PERSONAS O COSAS NO TRANSPORTADAS.",
    ]
    for ln in lines_bi:
        c.drawString(14*mm, y, ln); y -= 4*mm

    # Grid de datos
    y -= 4*mm
    vig = f"{fmt_fecha(p.get('fecha_inicio',''))} - {fmt_fecha(p.get('fecha_venc',''))}"
    auto = f"{p.get('marca','')} {p.get('modelo','')}  -  {p.get('anio','')}"
    dom = f"{p.get('domicilio','')}  -  {p.get('localidad','').upper()}"

    campos = [
        ('Seguradora - Aseguradora', 'NRE SEGUROS S.A.', 'Pais - Pais', 'ARGENTINA'),
        ('Segurado - Asegurado', p.get('nombre','').upper(), 'Número', p.get('npoliza','')),
        ('Endereco - Domicilio', dom, 'Vigencia', vig),
        ('Marca Modelo Ano - Marca Modelo Año', auto, None, None),
    ]

    for label1, val1, label2, val2 in campos:
        BOX(14*mm, y, 88*mm, 14*mm)
        BOX(102*mm, y, 94*mm, 14*mm)
        c.setFont('Helvetica-Bold',7); c.setFillColor(C_GRAY)
        c.drawString(15.5*mm, y-3.5*mm, label1)
        c.setFont('Helvetica',8); c.setFillColor(C_BLACK)
        c.drawString(15.5*mm, y-9*mm, str(val1 or ''))
        if label2:
            c.setFont('Helvetica-Bold',7); c.setFillColor(C_GRAY)
            c.drawString(103.5*mm, y-3.5*mm, label2)
            c.setFont('Helvetica',8); c.setFillColor(C_BLACK)
            c.drawString(103.5*mm, y-9*mm, str(val2 or ''))
        y -= 14*mm

    # Texto certifica
    y -= 3*mm
    c.setFont('Helvetica', 7.5); c.setFillColor(C_BLACK)
    c.drawString(14*mm, y, "Certifica que o veículo cujos dados enumeram-se anteriormente está amparado no risco de responsabilidade civil de acordo com os valores e condições estabelecidos na Resolução do Grupo")
    y -= 4*mm
    c.drawString(14*mm, y, "Mercado Comum aos países integrantes do Mercosul.")
    y -= 4.5*mm
    c.drawString(14*mm, y, "Certifica que el vehiculo cuyos datos se detallan anteriormente se encuentra amparado en el riesgo de responsabilidad civil conforme a los montos y condiciones establecidas en la Resolución del")
    y -= 4*mm
    c.drawString(14*mm, y, "Grupo Mercado Común a los paises integrantes del Mercosur.")

    # Países + firma
    y -= 8*mm
    T(14*mm, y, 'Esta cobertura compreende os siguientes países:', 8, True)
    T(130*mm, y, 'Assinatura e carimbo da Seguradora', 8, True)
    y -= 4.5*mm
    T(14*mm, y, 'Esta cobertura comprende los siguientes países:', 8, True)
    T(130*mm, y, 'Firma y Sello de la Aseguradora', 8, True)
    y -= 6*mm
    T(14*mm, y, 'URUGUAY - BRASIL - PARAGUAY - CHILE - ARGENTINA', 9, True)

    # Firma NRE
    firma = img_path(FIRMAS, 'firma_nre.png')
    draw_img(c, firma, 128*mm, y-8*mm, 64*mm, 20*mm)

    # Ciudad y fecha
    y -= 18*mm
    T(14*mm, y, 'Cidade - Ciudad', 8, True)
    T(80*mm, y, 'Data - Fecha', 8, True)
    y -= 5*mm
    T(14*mm, y, 'C.A.B.A.', 8)
    now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    T(80*mm, y, f"{fmt_fecha(p.get('fecha_inicio',''))} {now[11:]}", 8)
    T(196*mm, y-4*mm, '.............................................',8,align='right')
    T(196*mm, y-8*mm, 'Luciano Fernandez (Presidente)', 7.5, align='right')

    # Sumas aseguradas
    y -= 16*mm
    c.setFillColor(C_BLACK); c.setStrokeColor(C_BLACK); c.setLineWidth(0.5)
    c.rect(14*mm, y-6*mm, 182*mm, 6*mm)
    T(W/2, y-4*mm, 'IMPORTANCIAS SEGURADAS E LIMITES DE RESPONSABILIDADE POR VEICULO E EVENTO. SUMAS ASEGURADAS Y LIMITES MAXIMOS DE RESPONSABILIDAD POR', 6.5, True, C_BLACK, 'center')
    y -= 6*mm
    c.rect(14*mm, y-6*mm, 182*mm, 6*mm)
    T(W/2, y-4*mm, 'VEHICULO Y EVENTO. DANOS A TERCEROS NAO TRANSPORTADOS / DAÑOS A TERCEROS NO TRANSPORTADOS,', 6.5, True, C_BLACK, 'center')
    y -= 6*mm
    c.rect(14*mm, y-6*mm, 182*mm, 6*mm)
    T(W/2, y-4.5*mm, 'MUERTE E/ OU DAÑOS PESSOASI - MUERTE Y/O DAÑOS PERSONALES:', 7, True, C_BLACK, 'center')
    y -= 6*mm
    c.setFont('Helvetica', 7.5); c.setFillColor(C_BLACK)
    c.drawString(20*mm, y-3*mm, 'POR PESSOA / POR PERSONA U$S 40.000')
    c.drawRightString(196*mm, y-3*mm, 'LIMITE MAXIMO POR EVENTO U$S 200.000')
    y -= 6*mm
    c.rect(14*mm, y-6*mm, 182*mm, 6*mm)
    T(W/2, y-4.5*mm, 'DAÑOS MATERIALES - DAÑOS MATERIALES:', 7, True, C_BLACK, 'center')
    y -= 6*mm
    c.setFont('Helvetica', 7.5)
    c.drawString(20*mm, y-3*mm, 'POR TERCEIRO / POR TERCERO U$S 20.000')
    c.drawRightString(196*mm, y-3*mm, 'LIMITE MAXIMO POR EVENTO U$S 40.000')

    # Tabla países
    y -= 12*mm
    paises_data = [
        ('BRASIL','PARAGUAY','URUGUAY','CHILE','BOLIVIA'),
        ('AGF SEGUROS S.A.\nFLAVIO PINHEIRO NETO &\nADVOGADOS',
         'EL COMERCIO\nPARAGUAYO S.A.\n(+595 21) 492324 INT. 1077',
         'MAPFRE URUGUAY\nSEGUROS S.A.\nCRISTIAN SOUZA RUFF\nABOGADOS\n00598 20908 3537',
         'HANNA &\nCO.LTD.',
         'FORTALEZA SEGUROS Y\nRASEGUROS S.A.\n(5913)3487273-3497675'),
    ]
    col_w = 36*mm
    for j, pais in enumerate(paises_data[0]):
        c.setFillColor(C_BLACK); c.setStrokeColor(C_BORDER); c.setLineWidth(0.5)
        c.rect(14*mm + j*col_w, y-6*mm, col_w, 6*mm)
        T(14*mm + j*col_w + col_w/2, y-4.5*mm, pais, 7.5, True, C_BLACK, 'center')
    y -= 6*mm
    for j, nom in enumerate(paises_data[1]):
        c.rect(14*mm + j*col_w, y-16*mm, col_w, 16*mm)
        lines = nom.split('\n')
        ly = y - 3*mm
        for ln in lines:
            T(14*mm + j*col_w + 1*mm, ly, ln, 6)
            ly -= 3.5*mm

    # Footer NRE
    y2 = 18*mm
    L(14*mm, y2, 196*mm, y2, C_BORDER)
    T(14*mm, y2-5*mm, 'NRE SEGUROS S.A.  -  25 de mayo 432 Piso 7 - C1043ACA - C.A.B.A.', 7, color=C_GRAY)

    # Tarjeta seguro obligatorio (recuadro inferior)
    y3 = y2 - 8*mm
    tw = 182*mm; tx = 14*mm
    c.setStrokeColor(C_BORDER); c.setLineWidth(0.5)
    c.rect(tx, y3-32*mm, tw, 32*mm)
    L(tx+tw/2, y3, tx+tw/2, y3-32*mm, C_BORDER)
    T(tx+tw/4, y3-4*mm, 'ESTA ES SU TARJETA DE SEGURO OBLIGATORIO', 7, True, C_BLACK, 'center')
    draw_img(c, img_path(LOGOS,'nre.png'), tx+2*mm, y3-18*mm, 28*mm, 12*mm)
    T(tx+32*mm, y3-9*mm, f"Asegurado:  {p.get('nombre','').upper()}", 7, True)
    T(tx+32*mm, y3-13.5*mm, f"Número:  {p.get('npoliza','')}   Cobertura:  A", 7)
    T(tx+32*mm, y3-18*mm, f"Vigencia:  {fmt_fecha(p.get('fecha_inicio',''))} - {fmt_fecha(p.get('fecha_venc',''))}", 7)
    T(tx+32*mm, y3-22*mm, f"Marca:  {p.get('marca','')} {p.get('modelo','')}", 7)
    T(tx+32*mm, y3-26*mm, f"Tipo:  {p.get('tipo_vehiculo','')}   Dominio:  {p.get('patente','')}", 7)
    T(tx+32*mm, y3-30*mm, f"Motor:  {p.get('motor','')}   Chasis:  {p.get('chasis','')}", 7)
    # Derecha tarjeta
    T(tx+tw/2+3*mm, y3-4*mm, 'NRE ASISTENCIA', 7, True)
    T(tx+tw/2+3*mm, y3-9*mm, 'SEGURO OBLIGATORIO AUTOMOTOR CONFORME DECRETO 1716/08', 6.5)
    T(tx+tw/2+3*mm, y3-13*mm, '(Reglamentario de la Ley Nacional de Transito y Seguridad Vial Nº 26363)', 6.5)
    draw_img(c, img_path(FIRMAS,'firma_nre.png'), tx+tw-44*mm, y3-30*mm, 40*mm, 14*mm)

    c.save(); buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════════════════════
# NRE — FRENTE DE PÓLIZA (2 páginas: frente + anexo)
# ═══════════════════════════════════════════════════════════════════════════════
def nre_frente_poliza(p):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    def T(x, y, txt, sz=8, bold=False, color=C_BLACK, align='left'):
        c.setFillColor(color)
        c.setFont('Helvetica-Bold' if bold else 'Helvetica', sz)
        if align=='center': c.drawCentredString(x,y,str(txt or ''))
        elif align=='right': c.drawRightString(x,y,str(txt or ''))
        else: c.drawString(x,y,str(txt or ''))

    def L(x1,y1,x2,y2,col=C_BORDER,w=0.5):
        c.setStrokeColor(col); c.setLineWidth(w); c.line(x1,y1,x2,y2)

    # ── Logo
    draw_img(c, img_path(LOGOS,'nre.png'), 14*mm, H-32*mm, 38*mm, 26*mm)

    # ── Título
    T(W/2, H-18*mm, 'FRENTE DE POLIZA', 16, True, C_BLACK, 'center')

    # ── Info fiscal
    fi = ['C.U.I.T. Nº 30-71233712-1',
          'Imp. Internos a los Seguros',
          'I.V.A. Responsable Inscripto',
          'Ing. Brutos: CONV. MULT. Nº Resp Insc']
    c.setFont('Helvetica', 7); c.setFillColor(C_GRAY)
    for i, f in enumerate(fi):
        c.drawRightString(196*mm, H-13*mm - i*4*mm, f)

    # Codigo SSN
    T(W/2-10*mm, H-22*mm, 'Codigo de Seguimiento SSN:', 7, color=C_GRAY, align='center')
    T(W/2-10*mm, H-26*mm, f"Póliza impresa en fecha: {fmt_fecha(p.get('fecha_inicio',''))}", 7, color=C_GRAY, align='center')

    L(14*mm, H-33*mm, 196*mm, H-33*mm, C_BORDER, 0.5)

    # ── Texto intro
    y = H-40*mm
    c.setFont('Helvetica-Bold', 7.5); c.setFillColor(C_BLACK)
    intro = "NRE Compañia de seguros S.A. en adelante ('El Asegurador') bajo las Condiciones Generales y Particulares de la presente"
    c.drawString(14*mm, y, intro)
    y -= 4.5*mm
    c.drawString(14*mm, y, "póliza, las que han sido convenidas de buena fe y de conformidad con la solicitud de seguros presentada por:")

    # ── Datos asegurado
    y -= 8*mm
    vig = f"{fmt_fecha(p.get('fecha_inicio',''))} - {fmt_fecha(p.get('fecha_venc',''))}"
    mod_label = {'trimestral_unico':'Trimestral','trimestral_mensual':'Trimestral',
                 'bimestral_unico':'Bimestral'}.get(p.get('modalidad',''),'Trimestral')

    def drow(label, val, x=14*mm, xv=48*mm, y2=None, x2=None, l2=None, v2=None, xv2=None):
        T(x, y2, label+':', 8, True)
        T(xv, y2, str(val or ''), 8)
        if l2 and x2:
            T(x2, y2, l2+':', 8, True)
            T(xv2 or x2+28*mm, y2, str(v2 or ''), 8)

    drow('Asegurado', p.get('nombre','').upper(), y2=y)
    y -= 5.5*mm
    drow('Domicilio', p.get('domicilio',''), y2=y,
         x2=105*mm, l2='Sección', v2='Automotores', xv2=130*mm)
    y -= 5.5*mm
    drow('C.P.', p.get('cp',''), xv=28*mm, y2=y)
    T(105*mm, y, 'Póliza:', 8, True); T(124*mm, y, p.get('npoliza',''), 8)
    y -= 5.5*mm
    drow('Localidad', p.get('localidad',''), y2=y,
         x2=105*mm, l2='Endoso', v2='0', xv2=124*mm)
    y -= 5.5*mm
    drow('Provincia', p.get('provincia',''), y2=y,
         x2=105*mm, l2='Operación', v2='Emisión', xv2=130*mm)
    y -= 5.5*mm
    drow('Cond. Iva', p.get('cond_iva','CONSUMIDOR FINAL'), y2=y,
         x2=105*mm, l2='Fecha de Emisión', v2=fmt_fecha(p.get('fecha_inicio','')), xv2=150*mm)
    y -= 5.5*mm
    drow('CUIT / DNI', p.get('dni',''), y2=y,
         x2=105*mm, l2='Lugar', v2='C.A.B.A', xv2=124*mm)
    y -= 5.5*mm
    T(105*mm, y, 'Vigencia:', 8, True); T(130*mm, y, mod_label, 8)
    y -= 5.5*mm
    T(105*mm, y, 'Vigencia:', 8, True); T(130*mm, y, vig, 8)
    y -= 5.5*mm
    T(105*mm, y, 'Periodo Facturado:', 8, True); T(150*mm, y, vig, 8)
    y -= 5.5*mm
    T(105*mm, y, 'Moneda:', 8, True); T(130*mm, y, 'Pesos', 8)

    # En adelante
    y -= 6*mm
    c.setFont('Helvetica', 7.5)
    c.drawString(14*mm, y, 'En adelante, ("El Asegurado") el que se declara parte integrante de este contrato,')
    c.drawString(105*mm, y, 'Periodo Facturado: '+vig)
    y -= 4.5*mm
    c.drawString(14*mm, y, 'asegura contra los riesgos y/o bienes que se detallan a continuación.')

    # ── Cláusulas
    y -= 7*mm
    L(14*mm, y+2*mm, 196*mm, y+2*mm, C_BORDER)
    T(14*mm, y-2.5*mm, 'Forman parte de esta póliza los anexos, Condiciones Generales y Particulares y las Clausulas siguientes, quedando nulas las no mencionadas.', 7, True)
    y -= 7*mm
    T(14*mm, y, 'CLAUSULAS:', 7.5, True)
    y -= 4.5*mm
    clausulas = "CG-RC 01.1, CG-RC 02.1, CG-RC 03.1, CG-RC 04.1, CG-RC 05.1, CG-CO 05.1, CG-CO 06.2, CG-CO 07.1, CG-CO 08.1, CG-CO 09.1, CG-CO 10.1, CG-CO 11.1, CG-CO 12.1, CG-CO 13.1, CG-CO 14.1, CG-CO 15.1, CG-CO 16.1, CG-CO 17.1, CG-CO 18.1, CA-RC 02.1, CA-RC 05.1, CA-RC 05.2, CA-CC 09.1, CA-CO 04.1, CA-CO 06.1, CA-CO 14.1, CO-EX 02.1, SO-RC 6.1"
    # Wrap clausulas
    c.setFont('Helvetica', 7.5); c.setFillColor(C_BLACK)
    words = clausulas.split(', '); line_t = ''
    for w in words:
        test = line_t + (', ' if line_t else '') + w
        if c.stringWidth(test,'Helvetica',7.5) > 178*mm:
            c.drawString(14*mm, y, line_t); y -= 4*mm; line_t = w
        else: line_t = test
    if line_t: c.drawString(14*mm, y, line_t); y -= 4*mm

    y -= 2*mm
    T(14*mm, y, 'Limite de R.C. detallado en Condiciones Particulares comprensivo por acontecimiento.', 7.5)
    y -= 4.5*mm
    T(14*mm, y, 'Incluye Seguro Obligatorio de Responsabilidad Civil. Resolución N° 39.927/16 SSN - Reglamento de la Ley Nacional de Tránsito y Seguridad Vial N° 26.363.', 7.5)

    # ── Plan de pago
    y -= 7*mm
    L(14*mm, y+2*mm, 196*mm, y+2*mm, C_BORDER)

    prima   = float(p.get('prima') or 0)
    rec_fin = float(p.get('rec_financiero') or 0)
    iva_val = float(p.get('iva') or 0)
    otros   = float(p.get('otros_impuestos') or 0)
    subtotal= prima + rec_fin
    premio  = float(p.get('premio') or prima)
    cuotas  = cuotas_list(p)
    forma   = p.get('forma_pago','Efectivo')

    # Tabla plan pago
    c.setFont('Helvetica-Bold',8)
    c.drawString(14*mm, y-3*mm, 'Plan de Pago')
    c.drawString(80*mm, y-3*mm, f'Forma de Pago:')
    c.setFont('Helvetica',8)
    c.drawString(112*mm, y-3*mm, forma)

    # Totales derecha
    tots = [
        ('Prima:', fmt_peso(prima), True),
        ('Rec Financiero', fmt_peso(rec_fin), False),
        ('SUB-TOTAL', fmt_peso(subtotal), True),
        ('I.V.A.', fmt_peso(iva_val), False),
        ('I.V.A. Percepción', '0,00', False),
        ('Percepción IIBB', '0,00', False),
        ('Otros Impuestos', fmt_peso(otros), False),
    ]
    ty = y - 8*mm
    c.setStrokeColor(C_BORDER); c.setLineWidth(0.3)
    c.rect(128*mm, ty-len(tots)*5.5*mm, 68*mm, len(tots)*5.5*mm)
    for label, val, bold in tots:
        c.setFont('Helvetica-Bold' if bold else 'Helvetica', 8)
        c.setFillColor(C_BLACK)
        c.drawString(130*mm, ty, label)
        c.drawRightString(195*mm, ty, val)
        ty -= 5.5*mm

    # Cuotas izquierda
    cy = y - 8*mm
    c.setFont('Helvetica-Bold', 8)
    c.drawString(14*mm, cy, 'Vencimiento')
    c.drawString(55*mm, cy, 'Importe')
    cy -= 5.5*mm
    c.setStrokeColor(C_BORDER); c.setLineWidth(0.3)
    c.rect(14*mm, cy-len(cuotas)*5.5*mm, 90*mm, len(cuotas)*5.5*mm)
    for fc, imp in cuotas:
        c.setFont('Helvetica', 8); c.setFillColor(C_BLACK)
        c.drawString(16*mm, cy-3*mm, fmt_fecha(fc))
        c.drawString(55*mm, cy-3*mm, fmt_peso(imp))
        cy -= 5.5*mm

    # Premio y Total
    ty -= 2*mm
    L(128*mm, ty+1*mm, 196*mm, ty+1*mm, C_BLACK, 0.5)
    c.setFont('Helvetica-Bold', 9); c.setFillColor(C_BLACK)
    c.drawString(130*mm, ty, 'PREMIO')
    c.drawRightString(196*mm, ty, fmt_peso(premio))
    ty -= 6*mm
    c.drawString(130*mm, ty, 'TOTAL A PAGAR')
    c.drawRightString(196*mm, ty, fmt_peso(premio))

    # Productor
    c.setFont('Helvetica-Bold', 8)
    c.drawString(14*mm, min(ty,cy)-5*mm, 'Productor / Organizador')
    c.setFont('Helvetica', 8)
    c.drawString(14*mm, min(ty,cy)-10*mm, '998316')

    # ── Textos legales
    y_leg = min(ty, cy, min(ty,cy)-10*mm) - 12*mm
    legales = [
        "La entidad aseguradora dispone de un Servicio de Atención al Asegurado, ( 0-800-2222-872) que atenderá las consultas y reclamos que presenten los tomadores de seguros, asegurados,",
        "beneficiarios y/o derechohabientes. El Servicio de Atención al Asegurado está integrado por un RESPONSABLE y un SUPLENTE, cuyos datos de contacto encontrará disponibles en la página web",
        "(www.nre.com.ar). En caso de que el reclamo no haya sido resuelto o haya sido desestimado, total o parcialmente, o que haya sido denegada su admisión, podrá comunicarse con la Superintendencia",
        "de Seguros de la Nación por teléfono al 0800-666-8400, correo electrónico a denuncias@ssn.gob.ar o formulario web a través de www.argentina.gob.ar",
        "Cuando el texto difiera del contenido de la propuesta, la diferencia se considerará aprobada por el asegurado si no reclama dentro de un mes.",
        "El vehículo asegurado deberá contar con el respectivo grabado indeleble del dominio en determinadas partes de la carrocería conforme lo disponga la normativa de aquellas jurisdicciones en las que",
        "el mismo es obligatorio",
        "El vocablo \"Asegurador\" y \"Tomador\" o \"Contratante\" se usan indistintamente en la póliza, por lo que debe dársele el significado que corresponde, según las circunstancias del caso.",
        "La Red Federal de Asistencia a Víctimas y Familiares de Víctimas de Siniestros Viales brinda asesoramiento legal, psicológico, social y de rehabilitación en la post emergencia vial a nivel nacional.",
        "Usted puede comunicarse a la línea telefónica única y gratuita 0800-122-7464 de lunes a viernes de 8 a 20 hs. Correo electrónico: oav@seguridadvial.gob.ar.",
    ]
    c.setFont('Helvetica', 6.5); c.setFillColor(C_DGRAY)
    for leg in legales:
        c.drawString(14*mm, y_leg, leg); y_leg -= 3.8*mm

    y_leg -= 5*mm
    c.setFont('Helvetica', 7.5)
    c.drawString(14*mm, y_leg, "La presente póliza se suscribe mediante firma facsimilar conforme con lo previsto en el punto 7.8 del")
    y_leg -= 4.5*mm
    c.drawString(14*mm, y_leg, "Reglamento General de la Actividad Aseguradora.")
    y_leg -= 6*mm
    c.drawString(14*mm, y_leg, "Esta póliza ha sido aprobada por la Superintendencia de Seguros de la Nación MEDIANTE")
    y_leg -= 4.5*mm
    c.drawString(14*mm, y_leg, "LA RESOLUCIÓN N° 1091 / 2018")

    # Firma
    firma = img_path(FIRMAS, 'firma_nre.png')
    draw_img(c, firma, 128*mm, y_leg-2*mm, 64*mm, 20*mm)

    # ════════════════════════ PÁGINA 2 — ANEXO ════════════════════════
    c.showPage()
    W, H = A4

    # Header anexo
    draw_img(c, img_path(LOGOS,'nre.png'), 14*mm, H-32*mm, 38*mm, 26*mm)
    T(W/2, H-18*mm, 'ANEXO DE POLIZA', 14, True, C_BLACK, 'center')
    c.setFont('Helvetica', 7); c.setFillColor(C_GRAY)
    c.drawRightString(196*mm, H-13*mm, 'C.U.I.T. Nº 30-71233712-1')
    L(14*mm, H-33*mm, 196*mm, H-33*mm, C_BORDER)

    # Tabla header
    y = H-42*mm
    headers = ['Sección','Póliza','Endoso','Vigencia']
    widths  = [45*mm, 35*mm, 20*mm, 82*mm]
    c.setFillColor(C_BLACK); c.setStrokeColor(C_BORDER); c.setLineWidth(0.5)
    c.rect(14*mm, y-6*mm, 182*mm, 6*mm)
    xx = 14*mm
    for h, w2 in zip(headers, widths):
        T(xx+2*mm, y-4.5*mm, h, 7.5, True)
        xx += w2
    y -= 6*mm
    c.rect(14*mm, y-6*mm, 182*mm, 6*mm)
    vig_an = f"{fmt_fecha(p.get('fecha_inicio',''))} a las 12 hrs - {fmt_fecha(p.get('fecha_venc',''))} a las 12 hrs"
    vals = ['4 - Automotores', p.get('npoliza',''), '0', vig_an]
    xx = 14*mm
    for v, w2 in zip(vals, widths):
        T(xx+2*mm, y-4.5*mm, v, 7.5)
        xx += w2

    # ITEM NRO 1
    y -= 14*mm
    T(14*mm, y, 'ITEM NRO 1:', 8, True)

    # OBJETO / SUMAS
    y -= 6*mm
    L(14*mm, y+2*mm, 196*mm, y+2*mm, C_BORDER)
    T(20*mm, y-2.5*mm, 'OBJETO DEL SEGURO:', 8, True)
    T(196*mm, y-2.5*mm, 'SUMAS ASEGURADAS:', 8, True, align='right')
    L(14*mm, y-4*mm, 196*mm, y-4*mm, C_BORDER)

    y -= 12*mm
    def arow(lab, val, x=20*mm, xv=65*mm, yr=0, x2=None, l2=None, v2=None, xv2=None):
        T(x, yr, lab+':', 7.5, True)
        T(xv, yr, str(val or ''), 7.5)
        if l2 and x2:
            T(x2, yr, l2+':', 7.5, True)
            T(xv2 or x2+28*mm, yr, str(v2 or ''), 7.5)

    arow('Tipo de Vehículo', p.get('tipo_vehiculo',''), yr=y,
         x2=105*mm, l2='Carroceria', v2=p.get('carroceria',''), xv2=130*mm)
    T(165*mm, y, 'Casco Vehiculo:', 7.5, True); T(195*mm, y, '0,00', 7.5, align='right')
    y -= 5.5*mm
    arow('Marca y Modelo', f"{p.get('marca','')} {p.get('modelo','')}", yr=y)
    y -= 5.5*mm
    arow('Uso', p.get('uso',''), yr=y,
         x2=105*mm, l2='Año', v2=p.get('anio',''), xv2=125*mm)
    y -= 5.5*mm
    arow('Patente', p.get('patente',''), yr=y,
         x2=105*mm, l2='Motor', v2=p.get('motor',''), xv2=125*mm)
    y -= 5.5*mm
    arow('Chasis', p.get('chasis',''), yr=y)
    y -= 5.5*mm
    T(20*mm, y, 'Asegurado:', 7.5, True); T(44*mm, y, p.get('nombre','').upper(), 7.5)
    T(130*mm, y, 'CUIT / DNI:', 7.5, True); T(152*mm, y, p.get('dni',''), 7.5)
    y -= 5.5*mm
    T(20*mm, y, 'Domicilio:', 7.5, True); T(44*mm, y, p.get('domicilio',''), 7.5)
    y -= 5.5*mm
    T(20*mm, y, 'CP / Localidad:', 7.5, True)
    T(52*mm, y, f"{p.get('cp','')} - {p.get('localidad','').upper()}", 7.5)
    y -= 5.5*mm
    T(20*mm, y, 'Provincia:', 7.5, True); T(44*mm, y, p.get('provincia',''), 7.5)

    # Observaciones
    y -= 8*mm
    T(20*mm, y, 'Observaciones:', 7.5, True)
    y -= 6*mm
    L(14*mm, y, 196*mm, y, C_BORDER)

    # Cobertura
    y -= 7*mm
    T(20*mm, y, 'COBERTURA:', 7.5, True); T(48*mm, y, 'A - Responsabilidad Civil', 7.5)
    y -= 6*mm

    # Tabla franquicias
    tab_data = [
        ['', 'FRANQUICIA', 'LIMITE'],
        ['RC Terceros Transportados *', 'Responsabilidad Civil', ''],
        ['RC Terceros No Transportados *', 'Responsabilidad Civil', ''],
        ['RC daños a cosas *', 'Responsabilidad Civil', ''],
    ]
    col_ws = [75*mm, 80*mm, 27*mm]
    c.setStrokeColor(C_BORDER); c.setLineWidth(0.4)
    th = 5.5*mm
    for i, row in enumerate(tab_data):
        xx = 14*mm
        for j, (cell, cw) in enumerate(zip(row, col_ws)):
            c.rect(xx, y-th, cw, th)
            bold = (i==0)
            c.setFont('Helvetica-Bold' if bold else 'Helvetica', 7)
            c.setFillColor(C_BLACK)
            c.drawString(xx+1.5*mm, y-3.5*mm, cell)
            xx += cw
        y -= th

    y -= 5*mm
    c.setFont('Helvetica', 6.5); c.setFillColor(C_DGRAY)
    c.drawString(14*mm, y, "(*) Responsabilidad Civil: El límite de suma asegurada por acontecimiento es de $ 350.000.000 (dicho límite incluye RC terceros transportados, RC terceros no transportados y RC daños a cosas).")
    y -= 5*mm
    T(20*mm, y, 'Cláusula de Ajuste de Suma Asegurada:', 7, True); T(88*mm, y, 'Sin Cláusula de Ajuste de Suma Asegurada', 7)

    # Cláusulas
    y -= 7*mm
    T(20*mm, y, 'CLAUSULAS:', 7.5, True)
    y -= 4.5*mm
    c.setFont('Helvetica', 7); c.setFillColor(C_BLACK)
    words = clausulas.split(', '); line_t = ''
    for w in words:
        test = line_t + (', ' if line_t else '') + w
        if c.stringWidth(test,'Helvetica',7) > 172*mm:
            c.drawString(20*mm, y, line_t); y -= 3.8*mm; line_t = w
        else: line_t = test
    if line_t: c.drawString(20*mm, y, line_t); y -= 3.8*mm

    y -= 5*mm
    T(20*mm, y, 'Acreedor prendario:', 7.5, True); T(62*mm, y, 'No posee', 7.5)

    # Footer
    y2 = 22*mm
    L(14*mm, y2, 196*mm, y2, C_BORDER)
    T(W/2, y2-5*mm, '25 de mayo 432 Piso 7- C1043AAQ - C.A.B.A.', 7.5, False, C_GRAY, 'center')

    c.save(); buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════════════════════
# ATM — CERTIFICADO DE COBERTURA
# ═══════════════════════════════════════════════════════════════════════════════
def atm_cert_cobertura(p):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    def T(x, y, txt, sz=8, bold=False, color=C_BLACK, align='left'):
        c.setFillColor(color)
        c.setFont('Helvetica-Bold' if bold else 'Helvetica', sz)
        if align=='center': c.drawCentredString(x,y,str(txt or ''))
        elif align=='right': c.drawRightString(x,y,str(txt or ''))
        else: c.drawString(x,y,str(txt or ''))

    def L(x1,y1,x2,y2,col=C_BORDER,w=0.5):
        c.setStrokeColor(col); c.setLineWidth(w); c.line(x1,y1,x2,y2)

    def RECT(x,y,w2,h2,fill=False,fc=C_WHITE):
        c.setStrokeColor(C_BORDER); c.setLineWidth(0.5)
        c.setFillColor(fc)
        c.rect(x,y-h2,w2,h2,fill=1 if fill else 0,stroke=1)

    # ── Logo ATM izquierda
    draw_img(c, img_path(LOGOS,'atm.png'), 14*mm, H-36*mm, 42*mm, 32*mm)

    # ── Título derecha
    RECT(110*mm, H-10*mm, 86*mm, 12*mm, True, C_BLACK)
    T(153*mm, H-17.5*mm, 'CERTIFICADO DE COBERTURA', 10, True, C_WHITE, 'center')

    L(14*mm, H-37*mm, 196*mm, H-37*mm, C_BORDER, 0.5)

    # ── Datos cabecera
    y = H-44*mm
    vig_str = f"desde las 12:00:00hs del {fmt_fecha(p.get('fecha_inicio',''))} hasta las 12:00:00hs del {fmt_fecha(p.get('fecha_venc',''))}"
    nro_cert = f"0 - {p.get('npoliza','')}"

    RECT(14*mm, y, 182*mm, 6*mm)
    T(15*mm, y-4.5*mm, f"Lugar y Fecha :  C.A.B.A., {fmt_fecha(p.get('fecha_inicio',''))}", 8)
    y -= 6*mm
    RECT(14*mm, y, 182*mm, 6*mm)
    T(15*mm, y-4.5*mm, f"Vigencia  :  {vig_str}", 7.5)
    y -= 6*mm
    RECT(14*mm, y, 91*mm, 6*mm)
    RECT(105*mm, y, 91*mm, 6*mm)
    T(15*mm, y-4.5*mm, f"N° Certificado :  {nro_cert}", 7.5)
    T(106*mm, y-4.5*mm, f"Item  :  1     Póliza  :  3 - {p.get('npoliza','')}", 7.5)
    y -= 6*mm
    RECT(14*mm, y, 182*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'Asegurado', 8, True); T(46*mm, y-4.5*mm, f":  {p.get('nombre','').upper()}", 8)
    y -= 6*mm
    RECT(14*mm, y, 182*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'Dirección', 8, True); T(46*mm, y-4.5*mm, f":  {p.get('domicilio','')}", 8)
    y -= 6*mm
    RECT(14*mm, y, 91*mm, 6*mm); RECT(105*mm, y, 91*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'Localidad', 8, True)
    T(46*mm, y-4.5*mm, f":  {p.get('localidad','')}", 8)
    T(106*mm, y-4.5*mm, f"CP :  {p.get('cp','')}   Provincia : {p.get('provincia','')}", 8)
    y -= 6*mm
    RECT(14*mm, y, 91*mm, 6*mm); RECT(105*mm, y, 91*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'Cond. IVA', 8, True)
    T(46*mm, y-4.5*mm, f":  {p.get('cond_iva','CONSUMIDOR FINAL')}", 8)
    T(106*mm, y-4.5*mm, f"CUIT  :  {p.get('dni','')}", 8)

    # ── Datos vehículo
    y -= 8*mm
    RECT(14*mm, y, 182*mm, 6*mm, True, colors.HexColor('#f5f5f5'))
    T(15*mm, y-4.5*mm, 'Datos del vehículo', 8, True)
    y -= 6*mm

    RECT(14*mm, y, 91*mm, 6*mm); RECT(105*mm, y, 91*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'Marca', 8, True); T(34*mm, y-4.5*mm, f":  {p.get('marca','')}", 8)
    T(106*mm, y-4.5*mm, 'Modelo', 8, True); T(126*mm, y-4.5*mm, f":  {p.get('modelo','')}", 8)
    y -= 6*mm
    RECT(14*mm, y, 45*mm, 6*mm); RECT(59*mm, y, 46*mm, 6*mm); RECT(105*mm, y, 45*mm, 6*mm); RECT(150*mm, y, 46*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'Año', 8, True); T(27*mm, y-4.5*mm, f":  {p.get('anio','')}", 8)
    T(60*mm, y-4.5*mm, 'Suma asegurada:', 8, True); T(92*mm, y-4.5*mm, '$0,00', 8)
    T(106*mm, y-4.5*mm, 'Uso', 8, True); T(115*mm, y-4.5*mm, f":  {p.get('uso','')}", 8)
    T(151*mm, y-4.5*mm, 'Origen', 8, True); T(166*mm, y-4.5*mm, f":  {p.get('origen','')}", 8)
    y -= 6*mm
    RECT(14*mm, y, 91*mm, 6*mm); RECT(105*mm, y, 91*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'Tipo', 8, True); T(28*mm, y-4.5*mm, f":  {p.get('tipo_vehiculo','')}", 8)
    T(106*mm, y-4.5*mm, 'Carrocería:', 8, True); T(130*mm, y-4.5*mm, p.get('carroceria',''), 8)
    y -= 6*mm
    RECT(14*mm, y, 91*mm, 6*mm); RECT(105*mm, y, 91*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'Dominio', 8, True); T(34*mm, y-4.5*mm, f":  {p.get('patente','')}", 8)
    y -= 6*mm
    RECT(14*mm, y, 91*mm, 6*mm); RECT(105*mm, y, 91*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'Motor', 8, True); T(30*mm, y-4.5*mm, f":  {p.get('motor','')}", 8)
    T(106*mm, y-4.5*mm, 'Chasis', 8, True); T(122*mm, y-4.5*mm, f":  {p.get('chasis','')}", 8)

    # ── Accesorios
    y -= 8*mm
    RECT(14*mm, y, 182*mm, 6*mm, True, colors.HexColor('#f5f5f5'))
    T(15*mm, y-4.5*mm, 'Accesorios', 8, True)
    y -= 6*mm; RECT(14*mm, y, 182*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'NO POSEE', 8)

    # ── Texto
    y -= 8*mm
    RECT(14*mm, y, 182*mm, 6*mm, True, colors.HexColor('#f5f5f5'))
    T(15*mm, y-4.5*mm, 'Texto', 8, True)
    y -= 6*mm; RECT(14*mm, y, 182*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'NO POSEE', 8)

    # ── Datos cobertura
    y -= 8*mm
    RECT(14*mm, y, 182*mm, 6*mm, True, colors.HexColor('#f5f5f5'))
    T(15*mm, y-4.5*mm, 'Datos de la cobertura', 8, True)
    y -= 6*mm; RECT(14*mm, y, 182*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'RESPONSABILIDAD CIVIL LIMITADA A PESOS 160.000.000,00.', 8)
    y -= 6*mm; RECT(14*mm, y, 182*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'RESPONSABILIDAD CIVIL SIN ASISTENCIA', 8)
    y -= 6*mm; RECT(14*mm, y, 182*mm, 6*mm)
    cov_line = 'RESPONSABILIDAD CIVIL HASTA' + '.'*58 + '  $ 160.000.000,00'
    T(15*mm, y-4.5*mm, cov_line, 7.5)

    # ── Footer
    y_foot = 50*mm
    T(14*mm, y_foot, 'Acreedor Prendario:', 7.5)
    T(14*mm, y_foot-5*mm, f"Fecha Emisión:      {fmt_fecha(p.get('fecha_inicio',''))}", 7.5)
    T(14*mm, y_foot-10*mm, 'VALIDEZ DEL CERTIFICADO 30 DIAS', 7.5, True)

    # Firma ATM
    firma = img_path(FIRMAS, 'firma_atm.png')
    draw_img(c, firma, 120*mm, y_foot+5*mm, 70*mm, 30*mm)

    L(14*mm, 20*mm, 196*mm, 20*mm, C_BORDER)
    T(W/2, 15*mm, 'ATM Compañía de Seguros S.A. - Florida 833 2do Piso, Edificio Thompson - (C1005AAQ) Bs.As. - Argentina', 7, color=C_GRAY, align='center')
    T(W/2, 11*mm, 'Tel. / Fax: 0810-345-0492 (ATM) - www.atmseguros.com.ar', 7, color=C_GRAY, align='center')

    c.save(); buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════════════════════
# ATM — MERCOSUR
# ═══════════════════════════════════════════════════════════════════════════════
def atm_mercosur(p):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    def T(x, y, txt, sz=8, bold=False, color=C_BLACK, align='left'):
        c.setFillColor(color)
        c.setFont('Helvetica-Bold' if bold else 'Helvetica', sz)
        if align=='center': c.drawCentredString(x,y,str(txt or ''))
        elif align=='right': c.drawRightString(x,y,str(txt or ''))
        else: c.drawString(x,y,str(txt or ''))

    def L(x1,y1,x2,y2,col=C_BORDER,w=0.5):
        c.setStrokeColor(col); c.setLineWidth(w); c.line(x1,y1,x2,y2)

    def RECT(x,y,w2,h2,fill=False,fc=C_WHITE,stroke=True):
        c.setStrokeColor(C_BORDER if stroke else C_WHITE)
        c.setLineWidth(0.5); c.setFillColor(fc)
        c.rect(x,y-h2,w2,h2,fill=1 if fill else 0,stroke=1 if stroke else 0)

    # Logo ATM
    draw_img(c, img_path(LOGOS,'atm.png'), 14*mm, H-36*mm, 42*mm, 32*mm)

    # Título
    T(W/2+10*mm, H-15*mm, 'MERCOSUL / MERCOSUR', 14, True, C_BLACK, 'center')

    # Texto REIMPRESIÓN
    T(14*mm, H-38*mm, f"REIMPRESIÓN DE PÓLIZA ORIGINAL {fmt_fecha(p.get('fecha_inicio',''))}", 7, color=C_GRAY)
    L(14*mm, H-39*mm, 196*mm, H-39*mm, C_BORDER, 0.5)

    # Tabla sección/póliza/vigencia
    y = H-46*mm
    RECT(14*mm, y, 182*mm, 6*mm, True, C_BLACK)
    T(15*mm, y-4.5*mm, 'SECCIÓN', 7.5, True, C_WHITE)
    T(55*mm, y-4.5*mm, 'PÓLIZA', 7.5, True, C_WHITE)
    T(90*mm, y-4.5*mm, 'VIGENCIA', 7.5, True, C_WHITE, 'center')
    T(155*mm, y-4.5*mm, 'TÉRMINO', 7.5, True, C_WHITE)
    T(176*mm, y-4.5*mm, 'CLIENTE', 7.5, True, C_WHITE)

    y -= 6*mm
    RECT(14*mm, y, 182*mm, 12*mm)
    T(15*mm, y-4.5*mm, 'AUTOMOTORES', 7.5)
    T(55*mm, y-4.5*mm, p.get('npoliza',''), 7.5)
    # Vigencia en dos líneas
    fi_str = f"Desde 12:00:00 hs."
    fi_str2 = fmt_fecha(p.get('fecha_inicio',''))
    ha_str = f"Hasta 12:00:00 hs."
    ha_str2 = fmt_fecha(p.get('fecha_venc',''))
    T(80*mm, y-3*mm, fi_str, 7); T(80*mm, y-7.5*mm, fi_str2, 7)
    T(115*mm, y-3*mm, ha_str, 7); T(115*mm, y-7.5*mm, ha_str2, 7)
    mod = p.get('modalidad','trimestral_unico')
    term = '365 Días' if 'bimestral' not in mod else '60 Días'
    T(155*mm, y-4.5*mm, term, 7.5)
    T(176*mm, y-4.5*mm, p.get('dni','')[:7] if p.get('dni') else '', 7)

    # Textos bilingüe
    y -= 14*mm
    c.setFont('Helvetica',7); c.setFillColor(C_BLACK)
    bils = [
        "Certificado de póliza única de seguro de responsabilidad civil del propietario y/o conductor de vehículos de paseo o de alquiler no matriculados en el país",
        "de ingreso en viaje internacional, daños causados a personas o cosas no transportadas.",
        "Certificado de apolice unica de seguro de responsabilidade civil do propietario e/ou conductor de vehículos de passeio ou de aluguel nao matriculados no",
        "pais de ingresso em viagem internacional, danos causados a pessoas ou objetos nao transportados.",
    ]
    for b in bils: c.drawString(14*mm, y, b); y -= 4*mm

    # Datos asegurado
    y -= 3*mm
    for seccion in ['Datos del Asegurado', 'Datos del Tomador']:
        RECT(14*mm, y, 182*mm, 6*mm, True, colors.HexColor('#f0f0f0'))
        T(15*mm, y-4.5*mm, seccion, 8, True)
        y -= 6*mm
        RECT(14*mm, y, 91*mm, 6*mm); RECT(105*mm, y, 91*mm, 6*mm)
        T(15*mm, y-4.5*mm, 'Nombre y Apellido / Razón Social :', 7.5, True)
        T(83*mm, y-4.5*mm, p.get('nombre','').upper(), 7.5)
        y -= 6*mm
        RECT(14*mm, y, 182*mm, 6*mm)
        T(15*mm, y-4.5*mm, 'Domicilio :', 7.5, True); T(45*mm, y-4.5*mm, p.get('domicilio',''), 7.5)
        y -= 6*mm
        RECT(14*mm, y, 60*mm, 6*mm); RECT(74*mm, y, 60*mm, 6*mm); RECT(134*mm, y, 62*mm, 6*mm)
        T(15*mm, y-4.5*mm, 'Localidad :', 7.5, True); T(40*mm, y-4.5*mm, p.get('localidad',''), 7.5)
        T(75*mm, y-4.5*mm, 'CP :', 7.5, True); T(88*mm, y-4.5*mm, p.get('cp',''), 7.5)
        T(135*mm, y-4.5*mm, 'Provincia :', 7.5, True); T(158*mm, y-4.5*mm, p.get('provincia',''), 7.5)
        y -= 6*mm
        RECT(14*mm, y, 91*mm, 6*mm); RECT(105*mm, y, 91*mm, 6*mm)
        T(15*mm, y-4.5*mm, 'DNI :', 7.5, True); T(32*mm, y-4.5*mm, p.get('dni',''), 7.5)
        T(106*mm, y-4.5*mm, 'Condición de IVA :', 7.5, True); T(140*mm, y-4.5*mm, p.get('cond_iva','CONSUMIDOR FINAL'), 7.5)
        y -= 8*mm

    # Datos vehículo
    RECT(14*mm, y, 182*mm, 6*mm, True, colors.HexColor('#f0f0f0'))
    T(15*mm, y-4.5*mm, 'Datos del Vehículo Asegurado', 8, True)
    y -= 6*mm
    RECT(14*mm, y, 91*mm, 6*mm); RECT(105*mm, y, 91*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'Marca/Marca :', 7.5, True); T(50*mm, y-4.5*mm, p.get('marca',''), 7.5)
    T(106*mm, y-4.5*mm, 'Modelo/Modelo :', 7.5, True); T(140*mm, y-4.5*mm, p.get('modelo',''), 7.5)
    y -= 6*mm
    RECT(14*mm, y, 91*mm, 6*mm); RECT(105*mm, y, 91*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'Placa/Matrícula :', 7.5, True); T(55*mm, y-4.5*mm, p.get('patente',''), 7.5)
    T(106*mm, y-4.5*mm, 'Ano/Año :', 7.5, True); T(130*mm, y-4.5*mm, p.get('anio',''), 7.5)
    y -= 6*mm
    RECT(14*mm, y, 91*mm, 6*mm); RECT(105*mm, y, 91*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'Chassis/Chasis :', 7.5, True); T(55*mm, y-4.5*mm, p.get('chasis',''), 7.5)

    # Certifica
    y -= 8*mm
    c.setFont('Helvetica',7.5)
    c.drawString(14*mm,y,"Certifica que el vehículo, cuyos datos se detallan anteriormente, se encuentra amparado en el riesgo de responsabilidad civil conforme a los montos y")
    y-=4*mm
    c.drawString(14*mm,y,"condiciones establecidas en la resolución del grupo mercado común a los países integrantes del mercosur.")
    y-=4*mm
    c.drawString(14*mm,y,"Certifica que o vehículo, cujos datos enumeran-se anteriormente, esta amparado no risco de responsabilidade civil, segundo os valores e condicones")
    y-=4*mm
    c.drawString(14*mm,y,"esteblecidas na resolucao do grupo mercado comun para os paises integrantes de mercosul.")

    # Sumas aseguradas
    y -= 8*mm
    RECT(14*mm, y, 182*mm, 6*mm, True, C_BLACK)
    T(W/2, y-4.5*mm, 'DANOS A TERCEIROS NAO TRANSPORTADOS / DAÑOS A TERCEROS NO TRANSPORTADOS', 7, True, C_WHITE, 'center')
    y -= 6*mm
    RECT(14*mm, y, 91*mm, 6*mm, True, colors.HexColor('#f0f0f0'))
    RECT(105*mm, y, 91*mm, 6*mm, True, colors.HexColor('#f0f0f0'))
    T(W/4+7*mm, y-4.5*mm, 'Muerte y/o daños personales / Morte e/eu danos pessoais', 7, True, C_BLACK, 'center')
    T(3*W/4+7*mm, y-4.5*mm, 'Daños materiales / Danos materiais', 7, True, C_BLACK, 'center')
    y -= 6*mm
    RECT(14*mm, y, 91*mm, 6*mm); RECT(105*mm, y, 91*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'Por persona / Por pessoa', 7); T(68*mm, y-4.5*mm, 'U$S  40000.00', 7)
    T(106*mm, y-4.5*mm, 'Por bien / Por bein', 7); T(148*mm, y-4.5*mm, 'U$S  20000.00', 7)
    y -= 6*mm
    RECT(14*mm, y, 91*mm, 6*mm); RECT(105*mm, y, 91*mm, 6*mm)
    T(15*mm, y-4.5*mm, 'Limite Máximo por evento', 7); T(68*mm, y-4.5*mm, 'U$S  200000.00', 7)
    T(106*mm, y-4.5*mm, 'Limite Máximo por evento', 7); T(148*mm, y-4.5*mm, 'U$S  40000.00', 7)

    # Firma
    firma = img_path(FIRMAS, 'firma_atm.png')
    draw_img(c, firma, 115*mm, y-35*mm, 75*mm, 32*mm)

    # Tabla países
    y -= 50*mm
    paises = ['BOLIVIA','BRASIL','CHILE','PARAGUAY','PERÚ','URUGUAY']
    nombres = ['BISA S.A. DE SEGUROS','AGF BRASIL SEGUROS S.A.','APS – ABOGADOS\nLIQUIDADORES DE SEGUROS',
               'EL COMERCIO PARAGUAYO\nS.A. CÍA DE SEGUROS\nGENERALES','IRIARTE & ASOCIADOS S.A.','ESTUDIO BARRERA']
    domicilios = ['AV.EL TROMPILLO 632,\nSANTA CRUZ DE LA SIERRA',
                  'RUA CONSELHEIRO\nCRISPINIANO, 58 2º ANDAR',
                  'FIDEL OTEIZA 1971 OF. 502,\nPROVIDENCIA – SANTIAGO DE\nCHILE',
                  'ALBERDI 466 – ASUNCIÓN DEL\nPARAGUAY',
                  'AV.COMANDANTE ESPINAR Nº\n203 PISO 7, MIRAFLORES, LIMA',
                  'AV. JUNCAL 1408\nMONTEVIDEO, R.O. URUGUAY']
    col_w = 182*mm / 6
    for j, pais in enumerate(paises):
        RECT(14*mm+j*col_w, y, col_w, 7*mm, True, C_BLACK)
        T(14*mm+j*col_w+col_w/2, y-5*mm, pais, 7.5, True, C_WHITE, 'center')
    y -= 7*mm
    for j, (nom, dom) in enumerate(zip(nombres, domicilios)):
        RECT(14*mm+j*col_w, y, col_w, 8*mm)
        T(14*mm+j*col_w+1*mm, y-3.5*mm, nom, 5.5)
    y -= 8*mm
    for j, dom in enumerate(domicilios):
        RECT(14*mm+j*col_w, y, col_w, 10*mm)
        ly = y-3*mm
        for ln in dom.split('\n'):
            T(14*mm+j*col_w+1*mm, ly, ln, 5.5); ly -= 3.5*mm

    c.save(); buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════════════════════
# ATM — TARJETA DE CIRCULACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
def atm_tarjeta_circulacion(p):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    def T(x, y, txt, sz=8, bold=False, color=C_BLACK, align='left'):
        c.setFillColor(color)
        c.setFont('Helvetica-Bold' if bold else 'Helvetica', sz)
        if align=='center': c.drawCentredString(x,y,str(txt or ''))
        elif align=='right': c.drawRightString(x,y,str(txt or ''))
        else: c.drawString(x,y,str(txt or ''))

    def L(x1,y1,x2,y2,col=C_BORDER,w=0.5):
        c.setStrokeColor(col); c.setLineWidth(w); c.line(x1,y1,x2,y2)

    # ── MITAD SUPERIOR — Bienvenida ATM ──────────────────────────────────────
    draw_img(c, img_path(LOGOS,'atm.png'), W-70*mm, H-38*mm, 55*mm, 34*mm)

    y = H-45*mm
    T(14*mm, y, '¡Hola!', 10, True)
    y -= 5*mm
    T(14*mm, y, 'Gracias por confiar en ATM Seguros.', 10, True)
    y -= 5*mm
    c.setFont('Helvetica', 8.5)
    c.drawString(14*mm, y, 'Te sugerimos que revises las condiciones de tu póliza para conocer los alcances de tus coberturas y beneficios.')
    y -= 4.5*mm
    c.drawString(14*mm, y, 'Ante cualquier duda o consulta, comunicate con tu Productor Asesor o con Atención al Asegurado.')

    # Box atención
    y -= 10*mm
    c.setFillColor(colors.HexColor('#f5f5f5')); c.setStrokeColor(C_BORDER); c.setLineWidth(0.5)
    c.rect(14*mm, y-20*mm, 182*mm, 20*mm, fill=1)
    T(16*mm, y-6*mm, 'Atención al Asegurado', 11, True, C_ATM_DARK)
    T(16*mm, y-11*mm, 'Lunes a Viernes de 9 a 19 hs.', 9, False, colors.HexColor('#444444'))
    # Número grande
    T(80*mm, y-10*mm, '0810 345 0492', 16, True, C_ATM_DARK)
    T(80*mm, y-15*mm, 'contacto@atmseguros.com.ar', 8, False, C_GRAY)

    # App + beneficios
    y -= 24*mm
    T(14*mm, y, 'Descargá nuestra App o ingresá', 8)
    y -= 4.5*mm
    T(14*mm, y, 'al Portal de Asegurados', 8)
    y -= 4.5*mm
    T(14*mm, y, 'tupoliza.atmseguros.com.ar', 8, True)
    for item in ['• Tarjeta de circulación','• Póliza digital','• Cupones de pago','• Denuncia de siniestros']:
        y -= 4*mm; T(16*mm, y, item, 7.5)
    T(110*mm, y+12*mm, 'Podés acceder a descuentos', 8)
    T(110*mm, y+7.5*mm, 'exclusivos en la adquisición de', 8)
    T(110*mm, y+3*mm, 'accesorios y servicios en', 8)
    T(110*mm, y-1.5*mm, 'beneficios.atmseguros.com.ar', 8, True)

    # ── COMO ACTUAR EN CASO DE SINIESTRO ──
    y -= 12*mm
    T(14*mm, y, 'COMO ACTUAR EN CASO DE SINIESTRO', 12, True)
    L(14*mm, y-2*mm, 196*mm, y-2*mm, C_BLACK, 1)

    y -= 10*mm
    siniestros = [
        ("Obtené los datos de los vehículos involucrados:", "• Patente, marca, propietario y seguro\n• Conductor: Nombre, teléfono, domicilio y registro"),
        ("Si existen lesionados, asistilos y solicitá ayuda a emergencias médicas (107), bomberos (100) y/o policía (101).", None),
        ("Hacé la denuncia de tu siniestro a través de tu productor de seguros, portal o App Móvil de Asegurados\ndentro de los 3 días de ocurrido.", None),
        ("En caso de robo realizá la denuncia policial.", None),
    ]
    c.setFillColor(C_ATM_DARK)
    for main_txt, sub_txt in siniestros:
        # Bullet
        c.circle(17*mm, y-1.5*mm, 2*mm, fill=1)
        c.setFont('Helvetica', 8.5); c.setFillColor(C_BLACK)
        c.drawString(22*mm, y, main_txt)
        if sub_txt:
            for ln in sub_txt.split('\n'):
                y -= 4.5*mm
                c.setFont('Helvetica', 8); c.drawString(110*mm, y, ln)
        y -= 9*mm
        c.setFillColor(C_ATM_DARK)

    # Separador
    L(14*mm, y+3*mm, 196*mm, y+3*mm, C_ATM_DARK, 2)

    # ── MITAD INFERIOR — TARJETA FÍSICA ──────────────────────────────────────
    y -= 4*mm
    th = 58*mm  # altura total zona tarjeta
    mid = W/2

    # Mitad izquierda
    draw_img(c, img_path(LOGOS,'atm.png'), 14*mm, y-2*mm, 32*mm, 22*mm)
    T(55*mm, y-4*mm, f"Póliza Nro.   03 - {p.get('npoliza','')}", 9, True)
    L(14*mm, y-25*mm, mid-5*mm, y-25*mm, C_ATM_DARK, 1.5)

    yc = y-28*mm
    datos = [
        ('Asegurado:', p.get('nombre','').upper()),
        ('Domicilio:', f"{p.get('domicilio','')} - {p.get('localidad','').upper()}"),
        ('Vehículo:', f"{p.get('marca','')} {p.get('modelo','')}"),
        ('Patente:', p.get('patente','')),
        ('Año:', p.get('anio','')),
        ('Motor:', p.get('motor','')),
        ('Chasis:', p.get('chasis','')),
    ]
    for label, val in datos:
        T(14*mm, yc, label, 7.5, True); T(40*mm, yc, str(val or ''), 7.5)
        yc -= 4.5*mm

    yc -= 2*mm
    T(14*mm, yc, f"Vigencia desde {fmt_fecha(p.get('fecha_inicio',''))} al {fmt_fecha(p.get('fecha_venc',''))}", 8, True, C_ATM_DARK)

    yc -= 7*mm
    T(14*mm, yc, 'ATM COMPAÑÍA DE SEGUROS S.A.', 7.5, True)
    T(14*mm, yc-4.5*mm, 'ATENCIÓN AL ASEGURADO 0810 345 0492', 7)

    # Firma lado izquierdo (pequeña)
    firma = img_path(FIRMAS, 'firma_atm.png')
    draw_img(c, firma, 14*mm, yc-22*mm, 40*mm, 14*mm)

    # Separador vertical
    L(mid, y+2*mm, mid, y-th, C_BORDER, 0.5)

    # Mitad derecha — En caso de choque
    rx = mid + 5*mm
    c.setFillColor(colors.HexColor('#f0f0f0')); c.setStrokeColor(C_BORDER); c.setLineWidth(0.4)
    c.rect(rx, y-7*mm, 91*mm, 7*mm, fill=1)
    T(rx+2*mm, y-5*mm, 'En caso de choque o accidente ', 7.5)
    T(rx+60*mm, y-5*mm, 'obtené los siguientes datos', 7.5, True)

    yc2 = y - 9*mm
    for lab in ['DEL TERCERO Nombre, dirección, teléfono, registro',
                'DEL VEHÍCULO Marca, patente, propietario, seguro',
                'DEL/LOS TESTIGOS Nombre, dirección, teléfono']:
        c.rect(rx, yc2-5*mm, 91*mm, 5*mm, fill=0)
        T(rx+2*mm, yc2-3.5*mm, lab, 7)
        yc2 -= 5*mm

    yc2 -= 5*mm
    T(rx+2*mm, yc2, 'Comunicate con tu PAS o llamá al', 7.5, True)
    T(rx+65*mm, yc2, '0810 345 0492', 8.5, True, C_ATM_DARK)
    T(rx+2*mm, yc2-4.5*mm, 'Lunes a viernes de 09 a 19hs.', 7)

    yc2 -= 10*mm
    legal = ("SEGURO OBLIGATORIO AUTOMOTOR CONFORME DECRETO 1706/08. "
             "(Reglamento de la Ley Nacional de Tránsito y Seguridad Vial Nº26363). "
             "La posesión de este comprobante obligatorio será prueba suficiente de la vigencia del seguro "
             "obligatorio de automotores exigido por el Artículo 68 de la Ley Nº24449. "
             "Conforme el artículo 2 de la Disposición Nº70/2009 de la AGENCIA NACIONAL DE SEGURIDAD VIAL, "
             "la falta de portación del recibo de pago de la prima del seguro obligatorio por parte del conductor del "
             "vehículo, no podrá ser aducida por la Autoridad de Constatación para determinar el incumplimiento de "
             "los requisitos para la circulación.")
    # Wrap texto legal
    c.setFont('Helvetica', 6); c.setFillColor(C_BLACK)
    words = legal.split(' '); line_t = ''
    max_w = 87*mm
    for w in words:
        test = line_t + (' ' if line_t else '') + w
        if c.stringWidth(test,'Helvetica',6) > max_w:
            c.drawString(rx+2*mm, yc2, line_t); yc2 -= 3.5*mm; line_t = w
        else: line_t = test
    if line_t: c.drawString(rx+2*mm, yc2, line_t)

    # Firma derecha
    draw_img(c, firma, rx+55*mm, yc2-18*mm, 34*mm, 14*mm)
    T(rx+56*mm, yc2-20*mm, 'Daniel Giglio', 6.5)
    T(rx+56*mm, yc2-24*mm, 'Presidente', 6.5)

    c.save(); buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════════════════════
# DISPATCHER
# ═══════════════════════════════════════════════════════════════════════════════
DOCUMENTOS = {
    'NRE': {
        'mercosur':       nre_mercosur,
        'cert_cobertura': nre_cert_cobertura,
        'frente_poliza':  nre_frente_poliza,
    },
    'ATM': {
        'mercosur':            atm_mercosur,
        'cert_cobertura':      atm_cert_cobertura,
        'tarjeta_circulacion': atm_tarjeta_circulacion,
    },
}
NOMBRES_DOC = {
    'mercosur':            'Mercosur',
    'cert_cobertura':      'Certificado de Cobertura',
    'frente_poliza':       'Frente de Póliza',
    'tarjeta_circulacion': 'Tarjeta de Circulación',
}

def generar_pdf(poliza, tipo):
    aseg = poliza.get('aseguradora','')
    ak   = 'NRE' if 'NRE' in aseg.upper() else ('ATM' if 'ATM' in aseg.upper() else None)
    if not ak: return None
    fn = DOCUMENTOS.get(ak,{}).get(tipo)
    if not fn: return None
    return fn(poliza)

def docs_disponibles(aseguradora):
    ak = 'NRE' if 'NRE' in aseguradora.upper() else ('ATM' if 'ATM' in aseguradora.upper() else None)
    if not ak: return {}
    return {k: NOMBRES_DOC[k] for k in DOCUMENTOS.get(ak,{}).keys()}


# ═══════════════════════════════════════════════════════════════════════════════
# DENUNCIA DE SINIESTRO — NRE y ATM
# ═══════════════════════════════════════════════════════════════════════════════
def generar_pdf_siniestro(s):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    def T(x, y, txt, sz=8, bold=False, color=C_BLACK, align='left'):
        c.setFillColor(color)
        c.setFont('Helvetica-Bold' if bold else 'Helvetica', sz)
        if align=='center': c.drawCentredString(x,y,str(txt or ''))
        elif align=='right': c.drawRightString(x,y,str(txt or ''))
        else: c.drawString(x,y,str(txt or ''))

    def L(x1,y1,x2,y2,col=C_BORDER,w=0.5):
        c.setStrokeColor(col); c.setLineWidth(w); c.line(x1,y1,x2,y2)

    def RECT(x,y,w2,h2,fill=False,fc=C_WHITE):
        c.setStrokeColor(C_BORDER); c.setLineWidth(0.4)
        c.setFillColor(fc)
        c.rect(x,y-h2,w2,h2,fill=1 if fill else 0,stroke=1)

    aseg = s.get('aseguradora','')
    is_atm = 'ATM' in aseg.upper()
    accent = C_ATM_DARK if is_atm else C_NRE_COPPER
    logo_file = 'atm.png' if is_atm else 'nre.png'

    # ── ENCABEZADO ───────────────────────────────────────────────────────────
    draw_img(c, img_path(LOGOS, logo_file), 14*mm, H-36*mm, 44*mm, 28*mm)

    # Título caja derecha
    c.setFillColor(accent); c.rect(95*mm, H-32*mm, 101*mm, 20*mm, fill=1, stroke=0)
    T(145.5*mm, H-18*mm, 'DENUNCIA DE SINIESTRO', 13, True, C_WHITE, 'center')
    T(145.5*mm, H-24*mm, aseg, 9, False, C_WHITE, 'center')

    L(14*mm, H-37*mm, 196*mm, H-37*mm, accent, 1.5)

    # Nº denuncia y fecha
    T(14*mm, H-43*mm, f"Nº Denuncia:", 8, True)
    T(44*mm, H-43*mm, s.get('numero_denuncia',''), 10, True, accent)
    T(120*mm, H-43*mm, f"Fecha de emisión:", 8, True)
    T(160*mm, H-43*mm, fmt_fecha(s.get('creado','')[:10] if s.get('creado') else ''), 8)

    estado_col = {'Abierto': colors.HexColor('#e85a4a'),
                  'En proceso': colors.HexColor('#e8c84a'),
                  'Cerrado': colors.HexColor('#4ae896')}.get(s.get('estado','Abierto'), C_GRAY)
    c.setFillColor(estado_col)
    c.roundRect(160*mm, H-52*mm, 32*mm, 7*mm, 3, fill=1, stroke=0)
    T(176*mm, H-47.5*mm, s.get('estado','Abierto'), 8, True, C_WHITE, 'center')

    # ── SECCIÓN 1: DATOS DEL SINIESTRO ───────────────────────────────────────
    y = H-58*mm
    c.setFillColor(accent); c.rect(14*mm, y, 182*mm, 7*mm, fill=1, stroke=0)
    T(105*mm, y+2*mm, '1. DATOS DEL SINIESTRO', 9, True, C_WHITE, 'center')
    y -= 2*mm

    fields1 = [
        [('Tipo de Siniestro', s.get('tipo_siniestro','')), ('Fecha del Siniestro', fmt_fecha(s.get('fecha_siniestro','')))],
        [('Fecha de Denuncia', fmt_fecha(s.get('fecha_denuncia',''))), ('Lugar del Siniestro', s.get('lugar_siniestro',''))],
    ]
    for row in fields1:
        y -= 7*mm
        for i,(lab,val) in enumerate(row):
            RECT(14*mm + i*91*mm, y, 91*mm, 7*mm)
            T(15*mm + i*91*mm, y-2*mm, lab+':', 7, True, C_GRAY)
            T(15*mm + i*91*mm, y-5.5*mm, val, 8, False, C_BLACK)

    # Descripción
    y -= 7*mm
    RECT(14*mm, y, 182*mm, 7*mm)
    T(15*mm, y-2*mm, 'Descripción del hecho:', 7, True, C_GRAY)
    desc = s.get('descripcion','')
    T(15*mm, y-5.5*mm, desc[:100] + ('...' if len(desc)>100 else ''), 7.5)
    if len(desc) > 100:
        y -= 5*mm
        RECT(14*mm, y, 182*mm, 5*mm)
        T(15*mm, y-4*mm, desc[100:200] + ('...' if len(desc)>200 else ''), 7.5)

    # Daños
    if s.get('danos'):
        y -= 6*mm
        RECT(14*mm, y, 182*mm, 6*mm)
        T(15*mm, y-2*mm, 'Daños declarados:', 7, True, C_GRAY)
        T(15*mm, y-5*mm, s.get('danos','')[:100], 7.5)

    # ── SECCIÓN 2: DATOS DEL ASEGURADO ───────────────────────────────────────
    y -= 10*mm
    c.setFillColor(accent); c.rect(14*mm, y, 182*mm, 7*mm, fill=1, stroke=0)
    T(105*mm, y+2*mm, '2. DATOS DEL ASEGURADO / VEHÍCULO', 9, True, C_WHITE, 'center')
    y -= 2*mm

    fields2 = [
        [('Nombre y Apellido', s.get('nombre_asegurado','')), ('DNI / CUIT', s.get('dni_asegurado',''))],
        [('Nº Póliza', s.get('npoliza','')), ('Patente / Dominio', s.get('patente',''))],
        [('Marca y Modelo', s.get('vehiculo','')), ('Año', s.get('anio_vehiculo',''))],
    ]
    for row in fields2:
        y -= 7*mm
        for i,(lab,val) in enumerate(row):
            RECT(14*mm + i*91*mm, y, 91*mm, 7*mm)
            T(15*mm + i*91*mm, y-2*mm, lab+':', 7, True, C_GRAY)
            T(15*mm + i*91*mm, y-5.5*mm, str(val or '—'), 8)

    # ── SECCIÓN 3: TERCERO (si hay) ───────────────────────────────────────────
    if any(s.get(k) for k in ['tercero_nombre','tercero_patente','tercero_tel','tercero_seguro']):
        y -= 10*mm
        c.setFillColor(accent); c.rect(14*mm, y, 182*mm, 7*mm, fill=1, stroke=0)
        T(105*mm, y+2*mm, '3. TERCERO INVOLUCRADO', 9, True, C_WHITE, 'center')
        y -= 2*mm
        terceros = [
            [('Nombre Tercero', s.get('tercero_nombre','')), ('Patente Tercero', s.get('tercero_patente',''))],
            [('Teléfono Tercero', s.get('tercero_tel','')), ('Seguro del Tercero', s.get('tercero_seguro',''))],
        ]
        for row in terceros:
            y -= 7*mm
            for i,(lab,val) in enumerate(row):
                RECT(14*mm + i*91*mm, y, 91*mm, 7*mm)
                T(15*mm + i*91*mm, y-2*mm, lab+':', 7, True, C_GRAY)
                T(15*mm + i*91*mm, y-5.5*mm, str(val or '—'), 8)

    # ── SECCIÓN 4: OBSERVACIONES ──────────────────────────────────────────────
    if s.get('obs'):
        y -= 10*mm
        c.setFillColor(accent); c.rect(14*mm, y, 182*mm, 7*mm, fill=1, stroke=0)
        T(105*mm, y+2*mm, '4. OBSERVACIONES / SEGUIMIENTO', 9, True, C_WHITE, 'center')
        y -= 2*mm
        y -= 10*mm
        RECT(14*mm, y, 182*mm, 10*mm)
        c.setFont('Helvetica', 7.5); c.setFillColor(C_BLACK)
        c.drawString(15*mm, y-4*mm, s.get('obs','')[:140])

    # ── FIRMAS ────────────────────────────────────────────────────────────────
    y_firm = 55*mm
    L(14*mm, y_firm, 196*mm, y_firm, accent, 1)

    # Caja firma asegurado
    c.setStrokeColor(C_BORDER); c.setLineWidth(0.4)
    c.rect(14*mm, y_firm-28*mm, 80*mm, 26*mm)
    T(54*mm, y_firm-6*mm, 'FIRMA DEL ASEGURADO', 7.5, True, C_GRAY, 'center')
    L(14*mm, y_firm-22*mm, 94*mm, y_firm-22*mm, C_BORDER, 0.4)
    T(54*mm, y_firm-26*mm, s.get('nombre_asegurado','').upper(), 7, False, C_GRAY, 'center')

    # Caja firma productor / aseguradora
    c.rect(116*mm, y_firm-28*mm, 80*mm, 26*mm)
    T(156*mm, y_firm-6*mm, 'SELLO Y FIRMA PRODUCTORA', 7.5, True, C_GRAY, 'center')
    # Firma de la aseguradora
    firma = img_path(FIRMAS, 'firma_atm.png' if is_atm else 'firma_nre.png')
    draw_img(c, firma, 130*mm, y_firm-26*mm, 50*mm, 18*mm)

    # ── FOOTER ────────────────────────────────────────────────────────────────
    L(14*mm, 22*mm, 196*mm, 22*mm, C_BORDER, 0.4)
    if is_atm:
        T(W/2, 17*mm, 'ATM Compañía de Seguros S.A. - Florida 833 2do Piso, Edificio Thompson - (C1005AAQ) Bs.As. - Tel: 0810-345-0492', 7, color=C_GRAY, align='center')
        T(W/2, 13*mm, 'www.atmseguros.com.ar', 7, color=C_GRAY, align='center')
    else:
        T(W/2, 17*mm, 'NRE SEGUROS S.A. - Corrientes 1464 Piso 4 - C1043AAQ - C.A.B.A. - Tel: 011-4345-2551', 7, color=C_GRAY, align='center')
        T(W/2, 13*mm, 'www.nre.com.ar', 7, color=C_GRAY, align='center')

    c.save(); buf.seek(0)
    return buf
