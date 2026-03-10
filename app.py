from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from functools import wraps
import sqlite3, hashlib, os, csv, io, random, string
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'seguros-pro-clave-2025-monteros')
DB = os.environ.get('DB_PATH', 'seguros.db')

# ─── DB ───────────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                rol TEXT DEFAULT 'operador',
                sucursal TEXT DEFAULT 'ambas',
                creado TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS polizas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                npoliza TEXT NOT NULL,
                aseguradora TEXT NOT NULL,
                sucursal TEXT NOT NULL,
                nombre TEXT NOT NULL,
                dni TEXT,
                domicilio TEXT,
                cp TEXT,
                localidad TEXT DEFAULT 'San Miguel de Tucuman',
                provincia TEXT DEFAULT 'Tucuman',
                cond_iva TEXT DEFAULT 'CONSUMIDOR FINAL',
                marca TEXT,
                modelo TEXT,
                anio TEXT,
                patente TEXT,
                motor TEXT,
                chasis TEXT,
                tipo_vehiculo TEXT DEFAULT 'Automovil Nacional',
                carroceria TEXT DEFAULT 'Sedan',
                uso TEXT DEFAULT 'PARTICULAR',
                origen TEXT DEFAULT 'Nacional',
                cobertura TEXT DEFAULT 'A',
                modalidad TEXT DEFAULT 'trimestral_unico',
                prima REAL DEFAULT 0,
                rec_financiero REAL DEFAULT 0,
                iva REAL DEFAULT 0,
                otros_impuestos REAL DEFAULT 0,
                premio REAL DEFAULT 0,
                fecha_inicio TEXT NOT NULL,
                fecha_venc TEXT NOT NULL,
                forma_pago TEXT DEFAULT 'Efectivo',
                obs TEXT,
                activa INTEGER DEFAULT 1,
                creado TEXT DEFAULT CURRENT_TIMESTAMP,
                usuario_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS cobros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                cliente TEXT NOT NULL,
                aseguradora TEXT,
                sucursal TEXT,
                concepto TEXT,
                metodo TEXT,
                monto REAL NOT NULL,
                notas TEXT,
                poliza_id INTEGER,
                usuario_id INTEGER,
                creado TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS siniestros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_denuncia TEXT,
                aseguradora TEXT NOT NULL,
                sucursal TEXT DEFAULT 'Roca',
                tipo_siniestro TEXT NOT NULL,
                fecha_siniestro TEXT NOT NULL,
                fecha_denuncia TEXT,
                nombre_asegurado TEXT NOT NULL,
                dni_asegurado TEXT,
                npoliza TEXT,
                patente TEXT,
                vehiculo TEXT,
                anio_vehiculo TEXT,
                lugar_siniestro TEXT,
                descripcion TEXT NOT NULL,
                danos TEXT,
                tercero_nombre TEXT,
                tercero_patente TEXT,
                tercero_tel TEXT,
                tercero_seguro TEXT,
                estado TEXT DEFAULT 'Abierto',
                obs TEXT,
                usuario_id INTEGER,
                creado TEXT DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        # Admin por defecto
        admin_pw = hashlib.sha256('admin123'.encode()).hexdigest()
        try:
            db.execute("INSERT INTO usuarios (nombre,email,password,rol,sucursal) VALUES (?,?,?,?,?)",
                      ('Administrador','admin@seguros.com', admin_pw,'admin','ambas'))
            db.commit()
        except: pass

try:
    from dateutil.relativedelta import relativedelta
except:
    os.system('pip install python-dateutil --break-system-packages -q')
    from dateutil.relativedelta import relativedelta

init_db()

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def gen_npoliza():
    while True:
        n = str(random.randint(100000, 999999))
        with get_db() as db:
            exists = db.execute("SELECT id FROM polizas WHERE npoliza=?", (n,)).fetchone()
        if not exists: return n

def dias_venc(v):
    try: return (datetime.strptime(v,'%Y-%m-%d').date() - date.today()).days
    except: return 999

def estado(v):
    d = dias_venc(v)
    if d < 0:   return 'Vencida','exp'
    if d <= 30: return f'Vence en {d}d','warn'
    return 'Vigente','ok'

def fmt_fecha(s):
    if not s: return '—'
    try:
        p = s.split('-')
        return f"{p[2]}/{p[1]}/{p[0]}"
    except: return s

def fmt_peso(n):
    try: return f"${float(n):,.2f}".replace(',','X').replace('.',',').replace('X','.')
    except: return '$0,00'

def sucursal_usuario():
    return session.get('sucursal','ambas')

def puede_ver_sucursal(suc):
    us = sucursal_usuario()
    return us == 'ambas' or us == suc

def calcular_cuotas(modalidad, prima, fecha_inicio):
    """Devuelve lista de (fecha_venc, importe) según modalidad"""
    try:
        fi = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
    except:
        fi = date.today()
    cuotas = []
    if modalidad == 'trimestral_unico':
        cuotas = [(fi.strftime('%Y-%m-%d'), prima)]
    elif modalidad == 'trimestral_mensual':
        imp = round(prima / 3, 2)
        for i in range(3):
            d = fi + relativedelta(months=i)
            cuotas.append((d.strftime('%Y-%m-%d'), imp))
    elif modalidad == 'bimestral_unico':
        cuotas = [(fi.strftime('%Y-%m-%d'), prima)]
    return cuotas

def fecha_venc_por_modalidad(fecha_inicio, modalidad):
    try:
        fi = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
    except:
        fi = date.today()
    if modalidad in ('trimestral_unico','trimestral_mensual'):
        return (fi + relativedelta(months=3)).strftime('%Y-%m-%d')
    elif modalidad == 'bimestral_unico':
        return (fi + relativedelta(months=2)).strftime('%Y-%m-%d')
    return (fi + relativedelta(months=3)).strftime('%Y-%m-%d')

# ─── AUTH ─────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def dec(*a,**kw):
        if 'user_id' not in session: return redirect(url_for('login'))
        return f(*a,**kw)
    return dec

def admin_required(f):
    @wraps(f)
    def dec(*a,**kw):
        if session.get('rol') != 'admin':
            flash('Solo administradores','error')
            return redirect(url_for('index'))
        return f(*a,**kw)
    return dec

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        pw    = hash_pw(request.form.get('password',''))
        with get_db() as db:
            u = db.execute("SELECT * FROM usuarios WHERE email=? AND password=?", (email,pw)).fetchone()
        if u:
            session.update({'user_id':u['id'],'nombre':u['nombre'],'rol':u['rol'],'sucursal':u['sucursal']})
            return redirect(url_for('index'))
        flash('Email o contraseña incorrectos','error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login'))

@app.route('/cambiar-password', methods=['POST'])
@login_required
def cambiar_password():
    actual  = hash_pw(request.form.get('actual',''))
    nueva   = request.form.get('nueva','')
    repetir = request.form.get('repetir','')
    if nueva != repetir:
        flash('Las contraseñas no coinciden','error')
        return redirect(url_for('usuarios'))
    with get_db() as db:
        u = db.execute("SELECT * FROM usuarios WHERE id=? AND password=?", (session['user_id'],actual)).fetchone()
        if not u:
            flash('Contraseña actual incorrecta','error')
            return redirect(url_for('usuarios'))
        db.execute("UPDATE usuarios SET password=? WHERE id=?", (hash_pw(nueva),session['user_id']))
        db.commit()
    flash('Contraseña actualizada','ok')
    return redirect(url_for('usuarios'))

# ─── DASHBOARD ────────────────────────────────────────────────────────────────
@app.route('/')
@login_required
def index():
    suc = sucursal_usuario()
    with get_db() as db:
        if suc == 'ambas':
            polizas = db.execute("SELECT * FROM polizas WHERE activa=1 ORDER BY fecha_venc").fetchall()
            cobros_mes = db.execute("SELECT * FROM cobros WHERE strftime('%Y-%m',fecha)=strftime('%Y-%m','now')").fetchall()
        else:
            polizas = db.execute("SELECT * FROM polizas WHERE activa=1 AND sucursal=? ORDER BY fecha_venc",(suc,)).fetchall()
            cobros_mes = db.execute("SELECT * FROM cobros WHERE strftime('%Y-%m',fecha)=strftime('%Y-%m','now') AND sucursal=?",(suc,)).fetchall()
    activas    = len(polizas)
    vencen     = len([p for p in polizas if 0 <= dias_venc(p['fecha_venc']) <= 30])
    total_mes  = sum(c['monto'] for c in cobros_mes)
    clientes_u = len(set(p['dni'] or p['nombre'] for p in polizas))
    return render_template('index.html',
        polizas=polizas[:10], activas=activas, vencen=vencen,
        total_mes=total_mes, clientes=clientes_u,
        estado=estado, fmt_fecha=fmt_fecha, fmt_peso=fmt_peso)

# ─── PÓLIZAS ──────────────────────────────────────────────────────────────────
@app.route('/polizas')
@login_required
def polizas():
    aseg = request.args.get('aseg','')
    suc_f= request.args.get('suc','')
    q    = request.args.get('q','')
    suc  = sucursal_usuario()
    sql  = "SELECT * FROM polizas WHERE activa=1"
    params = []
    if suc != 'ambas':
        sql += " AND sucursal=?"; params.append(suc)
    elif suc_f:
        sql += " AND sucursal=?"; params.append(suc_f)
    if aseg:
        sql += " AND aseguradora=?"; params.append(aseg)
    if q:
        sql += " AND (nombre LIKE ? OR patente LIKE ? OR dni LIKE ? OR npoliza LIKE ?)"
        params += [f'%{q}%']*4
    sql += " ORDER BY fecha_venc"
    with get_db() as db:
        lista = db.execute(sql, params).fetchall()
    return render_template('polizas.html', polizas=lista, estado=estado,
        fmt_fecha=fmt_fecha, fmt_peso=fmt_peso, aseg=aseg, q=q, suc_f=suc_f)

@app.route('/polizas/nueva', methods=['POST'])
@login_required
def nueva_poliza():
    f = request.form
    fecha_inicio = f.get('fecha_inicio') or date.today().strftime('%Y-%m-%d')
    modalidad    = f.get('modalidad','trimestral_unico')
    fecha_venc   = f.get('fecha_venc') or fecha_venc_por_modalidad(fecha_inicio, modalidad)
    prima        = float(f.get('prima') or 0)
    npoliza      = f.get('npoliza') or gen_npoliza()
    suc          = f.get('sucursal') or sucursal_usuario()
    if suc == 'ambas': suc = 'Roca'

    with get_db() as db:
        db.execute("""INSERT INTO polizas
            (npoliza,aseguradora,sucursal,nombre,dni,domicilio,cp,localidad,provincia,
             cond_iva,marca,modelo,anio,patente,motor,chasis,tipo_vehiculo,carroceria,
             uso,origen,cobertura,modalidad,prima,rec_financiero,iva,otros_impuestos,
             premio,fecha_inicio,fecha_venc,forma_pago,obs,usuario_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (npoliza, f['aseguradora'], suc, f['nombre'],
             f.get('dni'), f.get('domicilio'), f.get('cp'),
             f.get('localidad','San Miguel de Tucuman'),
             f.get('provincia','Tucuman'),
             f.get('cond_iva','CONSUMIDOR FINAL'),
             f.get('marca'), f.get('modelo'), f.get('anio'),
             f.get('patente','').upper(), f.get('motor'), f.get('chasis'),
             f.get('tipo_vehiculo','Automovil Nacional'),
             f.get('carroceria','Sedan'),
             f.get('uso','PARTICULAR'), f.get('origen','Nacional'),
             'A', modalidad, prima,
             float(f.get('rec_financiero') or 0),
             float(f.get('iva') or 0),
             float(f.get('otros_impuestos') or 0),
             float(f.get('premio') or prima),
             fecha_inicio, fecha_venc,
             f.get('forma_pago','Efectivo'),
             f.get('obs'), session['user_id']))
        db.commit()
    flash(f'Póliza {npoliza} creada correctamente','ok')
    return redirect(url_for('polizas'))

@app.route('/polizas/eliminar/<int:pid>', methods=['POST'])
@login_required
def eliminar_poliza(pid):
    with get_db() as db:
        db.execute("UPDATE polizas SET activa=0 WHERE id=?",(pid,))
        db.commit()
    flash('Póliza archivada','ok')
    return redirect(request.referrer or url_for('polizas'))

@app.route('/api/fecha-venc')
def api_fecha_venc():
    inicio   = request.args.get('inicio', date.today().strftime('%Y-%m-%d'))
    modalidad= request.args.get('modalidad','trimestral_unico')
    return jsonify({'fecha_venc': fecha_venc_por_modalidad(inicio, modalidad)})

@app.route('/api/gen-npoliza')
@login_required
def api_gen_npoliza():
    return jsonify({'npoliza': gen_npoliza()})

# ─── CLIENTES ─────────────────────────────────────────────────────────────────
@app.route('/clientes')
@login_required
def clientes():
    q   = request.args.get('q','')
    suc = sucursal_usuario()
    sql = "SELECT nombre,dni,domicilio,localidad,provincia,COUNT(*) as num FROM polizas WHERE activa=1"
    params = []
    if suc != 'ambas':
        sql += " AND sucursal=?"; params.append(suc)
    if q:
        sql += " AND (nombre LIKE ? OR dni LIKE ?)"; params += [f'%{q}%',f'%{q}%']
    sql += " GROUP BY COALESCE(NULLIF(dni,''),nombre) ORDER BY nombre"
    with get_db() as db:
        lista = db.execute(sql, params).fetchall()
    return render_template('clientes.html', clientes=lista, q=q)

# ─── VENCIMIENTOS ─────────────────────────────────────────────────────────────
@app.route('/vencimientos')
@login_required
def vencimientos():
    tab = request.args.get('tab','proximos')
    suc = sucursal_usuario()
    with get_db() as db:
        if suc == 'ambas':
            todas = db.execute("SELECT * FROM polizas WHERE activa=1 ORDER BY fecha_venc").fetchall()
        else:
            todas = db.execute("SELECT * FROM polizas WHERE activa=1 AND sucursal=? ORDER BY fecha_venc",(suc,)).fetchall()
    proximas = [p for p in todas if 0 <= dias_venc(p['fecha_venc']) <= 30]
    vencidas = [p for p in todas if dias_venc(p['fecha_venc']) < 0]
    return render_template('vencimientos.html',
        proximas=proximas, vencidas=vencidas, todas=todas,
        estado=estado, fmt_fecha=fmt_fecha, dias_venc=dias_venc, tab=tab)

# ─── CAJA ─────────────────────────────────────────────────────────────────────
@app.route('/caja')
@login_required
def caja():
    suc = sucursal_usuario()
    with get_db() as db:
        if suc == 'ambas':
            cobros  = db.execute("SELECT * FROM cobros ORDER BY fecha DESC,id DESC").fetchall()
            clientes_l = db.execute("SELECT DISTINCT nombre FROM polizas WHERE activa=1 ORDER BY nombre").fetchall()
        else:
            cobros  = db.execute("SELECT * FROM cobros WHERE sucursal=? ORDER BY fecha DESC,id DESC",(suc,)).fetchall()
            clientes_l = db.execute("SELECT DISTINCT nombre FROM polizas WHERE activa=1 AND sucursal=? ORDER BY nombre",(suc,)).fetchall()
    mes = datetime.now().strftime('%Y-%m')
    cobros_mes = [c for c in cobros if c['fecha'].startswith(mes)]
    total_mes  = sum(c['monto'] for c in cobros_mes)
    metodos = {}
    asegs   = {}
    sucs    = {}
    for c in cobros_mes:
        metodos[c['metodo']] = metodos.get(c['metodo'],0) + c['monto']
        asegs[c['aseguradora']] = asegs.get(c['aseguradora'],0) + c['monto']
        s = c['sucursal'] or '—'
        sucs[s] = sucs.get(s,0) + c['monto']
    return render_template('caja.html',
        cobros=cobros, total_mes=total_mes, metodos=metodos,
        asegs=asegs, sucs=sucs, clientes=clientes_l,
        fmt_fecha=fmt_fecha, fmt_peso=fmt_peso)

@app.route('/caja/cobro', methods=['POST'])
@login_required
def nuevo_cobro():
    f   = request.form
    suc = f.get('sucursal') or sucursal_usuario()
    if suc == 'ambas': suc = 'Roca'
    with get_db() as db:
        db.execute("""INSERT INTO cobros (fecha,cliente,aseguradora,sucursal,concepto,metodo,monto,notas,usuario_id)
                      VALUES (?,?,?,?,?,?,?,?,?)""",
            (f['fecha'], f['cliente'], f.get('aseguradora'), suc,
             f.get('concepto'), f['metodo'],
             float(f.get('monto') or 0), f.get('notas'), session['user_id']))
        db.commit()
    flash('Cobro registrado','ok')
    return redirect(url_for('caja'))

@app.route('/caja/eliminar/<int:cid>', methods=['POST'])
@login_required
def eliminar_cobro(cid):
    with get_db() as db:
        db.execute("DELETE FROM cobros WHERE id=?",(cid,))
        db.commit()
    flash('Cobro eliminado','ok')
    return redirect(url_for('caja'))

# ─── DOCUMENTOS / PDF ─────────────────────────────────────────────────────────
@app.route('/documentos/<int:pid>/<tipo>')
@login_required
def generar_doc(pid, tipo):
    with get_db() as db:
        p = db.execute("SELECT * FROM polizas WHERE id=?", (pid,)).fetchone()
    if not p:
        flash('Póliza no encontrada','error')
        return redirect(url_for('polizas'))
    from pdf_generator import generar_pdf
    buf = generar_pdf(dict(p), tipo)
    if not buf:
        flash('Documento no disponible para esta aseguradora','error')
        return redirect(url_for('polizas'))
    nombre = f"{tipo}_{p['npoliza']}_{p['aseguradora'].replace(' ','_')}.pdf"
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name=nombre)

# ─── USUARIOS ─────────────────────────────────────────────────────────────────
@app.route('/usuarios')
@login_required
@admin_required
def usuarios():
    with get_db() as db:
        lista = db.execute("SELECT id,nombre,email,rol,sucursal,creado FROM usuarios ORDER BY id").fetchall()
    return render_template('usuarios.html', usuarios=lista)

@app.route('/usuarios/nuevo', methods=['POST'])
@login_required
@admin_required
def nuevo_usuario():
    f = request.form
    try:
        with get_db() as db:
            db.execute("INSERT INTO usuarios (nombre,email,password,rol,sucursal) VALUES (?,?,?,?,?)",
                      (f['nombre'], f['email'].lower(), hash_pw(f['password']),
                       f.get('rol','operador'), f.get('sucursal','Roca')))
            db.commit()
        flash(f"Usuario {f['nombre']} creado",'ok')
    except:
        flash('Error: ese email ya existe','error')
    return redirect(url_for('usuarios'))

@app.route('/usuarios/eliminar/<int:uid>', methods=['POST'])
@login_required
@admin_required
def eliminar_usuario(uid):
    if uid == session['user_id']:
        flash('No podés eliminar tu propio usuario','error')
        return redirect(url_for('usuarios'))
    with get_db() as db:
        db.execute("DELETE FROM usuarios WHERE id=?",(uid,))
        db.commit()
    flash('Usuario eliminado','ok')
    return redirect(url_for('usuarios'))

# ─── EXPORT ───────────────────────────────────────────────────────────────────
@app.route('/exportar/polizas')
@login_required
def exportar_polizas():
    suc = sucursal_usuario()
    with get_db() as db:
        if suc == 'ambas':
            rows = db.execute("SELECT * FROM polizas WHERE activa=1 ORDER BY nombre").fetchall()
        else:
            rows = db.execute("SELECT * FROM polizas WHERE activa=1 AND sucursal=? ORDER BY nombre",(suc,)).fetchall()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['NPoliza','Aseguradora','Sucursal','Nombre','DNI','Domicilio','CP','Localidad',
                'Provincia','Marca','Modelo','Año','Patente','Motor','Chasis',
                'TipoVehiculo','Carroceria','Uso','Modalidad','Prima','Premio',
                'FechaInicio','FechaVenc','FormaPago','Estado'])
    for r in rows:
        est,_ = estado(r['fecha_venc'])
        w.writerow([r['npoliza'],r['aseguradora'],r['sucursal'],r['nombre'],r['dni'],
                    r['domicilio'],r['cp'],r['localidad'],r['provincia'],
                    r['marca'],r['modelo'],r['anio'],r['patente'],r['motor'],r['chasis'],
                    r['tipo_vehiculo'],r['carroceria'],r['uso'],r['modalidad'],
                    r['prima'],r['premio'],r['fecha_inicio'],r['fecha_venc'],r['forma_pago'],est])
    out.seek(0)
    from flask import Response
    return Response(out.getvalue(), mimetype='text/csv',
        headers={"Content-Disposition":f"attachment;filename=polizas_{date.today()}.csv"})

@app.route('/exportar/cobros')
@login_required
def exportar_cobros():
    suc = sucursal_usuario()
    with get_db() as db:
        if suc == 'ambas':
            rows = db.execute("SELECT * FROM cobros ORDER BY fecha DESC").fetchall()
        else:
            rows = db.execute("SELECT * FROM cobros WHERE sucursal=? ORDER BY fecha DESC",(suc,)).fetchall()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['Fecha','Cliente','Aseguradora','Sucursal','Concepto','Método','Monto','Notas'])
    for r in rows:
        w.writerow([r['fecha'],r['cliente'],r['aseguradora'],r['sucursal'],
                    r['concepto'],r['metodo'],r['monto'],r['notas']])
    out.seek(0)
    from flask import Response
    return Response(out.getvalue(), mimetype='text/csv',
        headers={"Content-Disposition":f"attachment;filename=cobros_{date.today()}.csv"})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT',5000)))

@app.route('/api/buscar-cliente')
@login_required
def api_buscar_cliente():
    q = request.args.get('q','').strip()
    if len(q) < 2:
        return jsonify([])
    suc = sucursal_usuario()
    sql = """SELECT DISTINCT nombre, dni, domicilio, cp, localidad, provincia,
                    cond_iva, marca, modelo, anio, patente, motor, chasis,
                    tipo_vehiculo, carroceria, uso, origen
             FROM polizas WHERE activa=1
             AND (nombre LIKE ? OR dni LIKE ? OR patente LIKE ?)"""
    params = [f'%{q}%', f'%{q}%', f'%{q}%']
    if suc != 'ambas':
        sql += " AND sucursal=?"
        params.append(suc)
    sql += " ORDER BY nombre LIMIT 12"
    with get_db() as db:
        rows = db.execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])

def gen_ndenuncia():
    prefix = datetime.now().strftime('%Y%m%d')
    with get_db() as db:
        count = db.execute("SELECT COUNT(*) FROM siniestros WHERE numero_denuncia LIKE ?", (f'{prefix}%',)).fetchone()[0]
    return f"{prefix}-{str(count+1).zfill(3)}"

# ─── SINIESTROS ───────────────────────────────────────────────────────────────
@app.route('/siniestros')
@login_required
def siniestros():
    q        = request.args.get('q','')
    estado_f = request.args.get('estado_f','')
    suc      = sucursal_usuario()
    sql      = "SELECT * FROM siniestros WHERE 1=1"
    params   = []
    if suc != 'ambas':
        sql += " AND sucursal=?"; params.append(suc)
    if estado_f:
        sql += " AND estado=?"; params.append(estado_f)
    if q:
        sql += " AND (nombre_asegurado LIKE ? OR npoliza LIKE ? OR patente LIKE ? OR dni_asegurado LIKE ?)"
        params += [f'%{q}%']*4
    sql += " ORDER BY fecha_siniestro DESC, id DESC"
    with get_db() as db:
        lista = db.execute(sql, params).fetchall()
    total      = len(lista)
    abiertos   = sum(1 for s in lista if s['estado'] == 'Abierto')
    en_proceso = sum(1 for s in lista if s['estado'] == 'En proceso')
    cerrados   = sum(1 for s in lista if s['estado'] == 'Cerrado')
    return render_template('siniestros.html',
        lista=lista, q=q, estado_f=estado_f,
        total=total, abiertos=abiertos, en_proceso=en_proceso, cerrados=cerrados,
        fmt_fecha=fmt_fecha, date=date)

@app.route('/siniestros/nuevo', methods=['POST'])
@login_required
def nuevo_siniestro():
    f   = request.form
    suc = f.get('sucursal') or sucursal_usuario()
    if suc == 'ambas': suc = 'Roca'
    ndenuncia = f.get('numero_denuncia','').strip() or gen_ndenuncia()
    with get_db() as db:
        db.execute("""INSERT INTO siniestros
            (numero_denuncia,aseguradora,sucursal,tipo_siniestro,fecha_siniestro,fecha_denuncia,
             nombre_asegurado,dni_asegurado,npoliza,patente,vehiculo,anio_vehiculo,
             lugar_siniestro,descripcion,danos,
             tercero_nombre,tercero_patente,tercero_tel,tercero_seguro,
             estado,obs,usuario_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ndenuncia, f['aseguradora'], suc, f['tipo_siniestro'],
             f['fecha_siniestro'], f.get('fecha_denuncia'),
             f['nombre_asegurado'], f.get('dni_asegurado'),
             f.get('npoliza'), f.get('patente','').upper(),
             f.get('vehiculo'), f.get('anio_vehiculo'),
             f.get('lugar_siniestro'), f['descripcion'], f.get('danos'),
             f.get('tercero_nombre'), f.get('tercero_patente'),
             f.get('tercero_tel'), f.get('tercero_seguro'),
             f.get('estado','Abierto'), f.get('obs'),
             session['user_id']))
        db.commit()
    flash(f'Siniestro {ndenuncia} registrado','ok')
    return redirect(url_for('siniestros'))

@app.route('/siniestros/eliminar/<int:sid>', methods=['POST'])
@login_required
def eliminar_siniestro(sid):
    with get_db() as db:
        db.execute("DELETE FROM siniestros WHERE id=?", (sid,))
        db.commit()
    flash('Siniestro eliminado','ok')
    return redirect(url_for('siniestros'))

@app.route('/siniestros/detalle/<int:sid>')
@login_required
def detalle_siniestro(sid):
    with get_db() as db:
        s = db.execute("SELECT * FROM siniestros WHERE id=?", (sid,)).fetchone()
    if not s: return jsonify({'error':'no encontrado'}), 404
    return jsonify(dict(s))

@app.route('/siniestros/pdf/<int:sid>')
@login_required
def pdf_siniestro(sid):
    with get_db() as db:
        s = db.execute("SELECT * FROM siniestros WHERE id=?", (sid,)).fetchone()
    if not s:
        flash('Siniestro no encontrado','error')
        return redirect(url_for('siniestros'))
    from pdf_generator import generar_pdf_siniestro
    buf = generar_pdf_siniestro(dict(s))
    nombre = f"siniestro_{s['numero_denuncia'].replace('-','_')}.pdf"
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=nombre)

@app.route('/exportar/siniestros')
@login_required
def exportar_siniestros():
    suc = sucursal_usuario()
    with get_db() as db:
        if suc == 'ambas':
            rows = db.execute("SELECT * FROM siniestros ORDER BY fecha_siniestro DESC").fetchall()
        else:
            rows = db.execute("SELECT * FROM siniestros WHERE sucursal=? ORDER BY fecha_siniestro DESC",(suc,)).fetchall()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['Nº Denuncia','Fecha','Aseguradora','Tipo','Asegurado','DNI','Póliza','Patente','Vehículo','Lugar','Estado'])
    for r in rows:
        w.writerow([r['numero_denuncia'],r['fecha_siniestro'],r['aseguradora'],
                    r['tipo_siniestro'],r['nombre_asegurado'],r['dni_asegurado'],
                    r['npoliza'],r['patente'],r['vehiculo'],r['lugar_siniestro'],r['estado']])
    out.seek(0)
    from flask import Response
    return Response(out.getvalue(), mimetype='text/csv',
        headers={"Content-Disposition":f"attachment;filename=siniestros_{date.today()}.csv"})
