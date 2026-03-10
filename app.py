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
                celular TEXT,
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
                tipo_movimiento TEXT DEFAULT 'cobro',
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
        # Migraciones
        try: db.execute("ALTER TABLE polizas ADD COLUMN celular TEXT"); db.commit()
        except: pass
        try: db.execute("ALTER TABLE cobros ADD COLUMN tipo_movimiento TEXT DEFAULT 'cobro'"); db.commit()
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
    suc      = sucursal_usuario()
    fecha_desde = request.args.get('desde', '')
    fecha_hasta = request.args.get('hasta', '')
    # Default: mes actual
    mes_actual = datetime.now().strftime('%Y-%m')
    if not fecha_desde: fecha_desde = datetime.now().strftime('%Y-%m-01')
    if not fecha_hasta: fecha_hasta = datetime.now().strftime('%Y-%m-%d')

    with get_db() as db:
        base = "WHERE activa=1" + (" AND sucursal=?" if suc != 'ambas' else "")
        params = [suc] if suc != 'ambas' else []
        # Pólizas activas
        polizas_todas = db.execute(f"SELECT * FROM polizas {base} ORDER BY creado DESC", params).fetchall()
        # Pólizas recientes (10 más nuevas)
        recientes = polizas_todas[:10]
        # Stats del período filtrado
        pparams = params + [fecha_desde, fecha_hasta]
        pol_periodo = db.execute(
            f"SELECT * FROM polizas {base} AND fecha_inicio>=? AND fecha_inicio<=? ORDER BY fecha_inicio DESC",
            pparams).fetchall()
        # Cobros del período
        cbase = "WHERE fecha>=? AND fecha<=?" + (" AND sucursal=?" if suc != 'ambas' else "")
        cparams = [fecha_desde, fecha_hasta] + ([suc] if suc != 'ambas' else [])
        cobros_periodo = db.execute(f"SELECT * FROM cobros {cbase}", cparams).fetchall()

    activas    = len(polizas_todas)
    vencen     = len([p for p in polizas_todas if 0 <= dias_venc(p['fecha_venc']) <= 30])
    clientes_u = len(set(p['dni'] or p['nombre'] for p in polizas_todas))
    # Siniestros abiertos
    with get_db() as db:
        sin_params = [] if suc == 'ambas' else [suc]
        sin_sql = "SELECT COUNT(*) FROM siniestros WHERE estado='Abierto'" + (" AND sucursal=?" if suc != 'ambas' else "")
        siniestros_abiertos = db.execute(sin_sql, sin_params).fetchone()[0]
    # Stats período
    pol_nre    = sum(1 for p in pol_periodo if 'NRE' in p['aseguradora'])
    pol_atm    = sum(1 for p in pol_periodo if 'ATM' in p['aseguradora'])
    monto_per  = sum(p['premio'] for p in pol_periodo)
    cobros_per = sum(c['monto'] for c in cobros_periodo)

    return render_template('index.html',
        polizas=recientes, activas=activas, vencen=vencen,
        clientes=clientes_u, siniestros_abiertos=siniestros_abiertos,
        pol_periodo=len(pol_periodo), pol_nre=pol_nre, pol_atm=pol_atm,
        monto_periodo=monto_per, cobros_periodo=cobros_per,
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
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
             premio,fecha_inicio,fecha_venc,forma_pago,obs,celular,usuario_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
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
             f.get('obs'), f.get('celular'), session['user_id']))
        db.commit()
        # Cobro automático al emitir
        premio = float(f.get('premio') or prima)
        if premio > 0:
            db.execute("""INSERT INTO cobros (fecha,cliente,aseguradora,sucursal,concepto,metodo,monto,tipo_movimiento,notas,usuario_id)
                         VALUES (?,?,?,?,?,?,?,'cobro',?,?)""",
                (fecha_inicio, f['nombre'], f['aseguradora'], suc,
                 f'Emisión póliza {npoliza}', f.get('forma_pago','Efectivo'),
                 premio, f'Auto-generado al emitir póliza {npoliza}', session['user_id']))
            db.commit()
    flash(f'Póliza {npoliza} creada correctamente','ok')
    return redirect(url_for('polizas'))

@app.route('/polizas/editar/<int:pid>', methods=['POST'])
@login_required
def editar_poliza(pid):
    f = request.form
    fecha_inicio = f.get('fecha_inicio')
    modalidad    = f.get('modalidad','trimestral_unico')
    fecha_venc   = f.get('fecha_venc') or fecha_venc_por_modalidad(fecha_inicio, modalidad)
    prima        = float(f.get('prima') or 0)
    with get_db() as db:
        db.execute("""UPDATE polizas SET
            aseguradora=?,nombre=?,dni=?,domicilio=?,cp=?,localidad=?,provincia=?,
            cond_iva=?,marca=?,modelo=?,anio=?,patente=?,motor=?,chasis=?,
            tipo_vehiculo=?,carroceria=?,uso=?,origen=?,modalidad=?,prima=?,
            rec_financiero=?,iva=?,otros_impuestos=?,premio=?,fecha_inicio=?,
            fecha_venc=?,forma_pago=?,obs=?,celular=?
            WHERE id=?""",
            (f['aseguradora'], f['nombre'], f.get('dni'), f.get('domicilio'),
             f.get('cp'), f.get('localidad'), f.get('provincia'),
             f.get('cond_iva'), f.get('marca'), f.get('modelo'), f.get('anio'),
             f.get('patente','').upper(), f.get('motor'), f.get('chasis'),
             f.get('tipo_vehiculo'), f.get('carroceria'), f.get('uso'), f.get('origen'),
             modalidad, prima,
             float(f.get('rec_financiero') or 0), float(f.get('iva') or 0),
             float(f.get('otros_impuestos') or 0), float(f.get('premio') or prima),
             fecha_inicio, fecha_venc, f.get('forma_pago'), f.get('obs'),
             f.get('celular'), pid))
        db.commit()
    flash('Póliza actualizada correctamente','ok')
    return redirect(request.referrer or url_for('polizas'))

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
    sql = "SELECT nombre,dni,domicilio,localidad,provincia,cp,cond_iva,celular,COUNT(*) as num FROM polizas WHERE activa=1"
    params = []
    if suc != 'ambas':
        sql += " AND sucursal=?"; params.append(suc)
    if q:
        sql += " AND (nombre LIKE ? OR dni LIKE ?)"; params += [f'%{q}%',f'%{q}%']
    sql += " GROUP BY COALESCE(NULLIF(dni,''),nombre) ORDER BY nombre"
    with get_db() as db:
        lista = db.execute(sql, params).fetchall()
    return render_template('clientes.html', clientes=lista, q=q)

@app.route('/api/cliente')
@login_required
def api_cliente():
    dni    = request.args.get('dni','')
    nombre = request.args.get('nombre','')
    with get_db() as db:
        if dni:
            r = db.execute("SELECT nombre,dni,domicilio,cp,localidad,provincia,cond_iva,celular FROM polizas WHERE dni=? AND activa=1 LIMIT 1",(dni,)).fetchone()
        else:
            r = db.execute("SELECT nombre,dni,domicilio,cp,localidad,provincia,cond_iva,celular FROM polizas WHERE nombre=? AND activa=1 LIMIT 1",(nombre,)).fetchone()
    if not r: return jsonify({}), 404
    return jsonify(dict(r))

@app.route('/clientes/editar', methods=['POST'])
@login_required
def editar_cliente():
    f      = request.form
    dni    = f.get('dni_original','')
    nombre = f.get('nombre_original','')
    with get_db() as db:
        if dni:
            db.execute("""UPDATE polizas SET nombre=?,dni=?,domicilio=?,cp=?,localidad=?,
                         provincia=?,cond_iva=?,celular=? WHERE dni=? AND activa=1""",
                (f['nombre'],f.get('dni'),f.get('domicilio'),f.get('cp'),
                 f.get('localidad'),f.get('provincia'),f.get('cond_iva'),
                 f.get('celular'), dni))
        else:
            db.execute("""UPDATE polizas SET nombre=?,dni=?,domicilio=?,cp=?,localidad=?,
                         provincia=?,cond_iva=?,celular=? WHERE nombre=? AND activa=1""",
                (f['nombre'],f.get('dni'),f.get('domicilio'),f.get('cp'),
                 f.get('localidad'),f.get('provincia'),f.get('cond_iva'),
                 f.get('celular'), nombre))
        db.commit()
    flash(f"Cliente {f['nombre']} actualizado",'ok')
    return redirect(url_for('clientes'))

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
    suc  = sucursal_usuario()
    tab  = request.args.get('tab','todos')
    mes  = datetime.now().strftime('%Y-%m')
    with get_db() as db:
        base_sql = "SELECT * FROM cobros" + (" WHERE sucursal=? ORDER BY fecha DESC,id DESC" if suc != 'ambas' else " ORDER BY fecha DESC,id DESC")
        movs = db.execute(base_sql, [suc] if suc != 'ambas' else []).fetchall()
        clientes_l = db.execute("SELECT DISTINCT nombre FROM polizas WHERE activa=1" + (" AND sucursal=?" if suc != 'ambas' else "") + " ORDER BY nombre",
                                [suc] if suc != 'ambas' else []).fetchall()
    # Stats mes
    movs_mes = [m for m in movs if m['fecha'].startswith(mes)]
    ingresos_mes  = sum(m['monto'] for m in movs_mes if (m['tipo_movimiento'] or 'cobro') in ('cobro','ingreso'))
    gastos_mes    = sum(m['monto'] for m in movs_mes if (m['tipo_movimiento'] or 'cobro') == 'gasto')
    retiros_mes   = sum(m['monto'] for m in movs_mes if (m['tipo_movimiento'] or 'cobro') == 'retiro')
    balance_mes   = ingresos_mes - gastos_mes - retiros_mes
    cobros_poliza = sum(m['monto'] for m in movs_mes if (m['tipo_movimiento'] or 'cobro') == 'cobro')
    # Filtro por tab
    if tab == 'cobros':
        lista = [m for m in movs if (m['tipo_movimiento'] or 'cobro') == 'cobro']
    elif tab == 'ingresos':
        lista = [m for m in movs if (m['tipo_movimiento'] or 'cobro') == 'ingreso']
    elif tab == 'gastos':
        lista = [m for m in movs if (m['tipo_movimiento'] or 'cobro') == 'gasto']
    elif tab == 'retiros':
        lista = [m for m in movs if (m['tipo_movimiento'] or 'cobro') == 'retiro']
    else:
        lista = movs
    return render_template('caja.html',
        lista=lista, tab=tab,
        ingresos_mes=ingresos_mes, gastos_mes=gastos_mes,
        retiros_mes=retiros_mes, balance_mes=balance_mes,
        cobros_poliza=cobros_poliza,
        clientes=clientes_l, fmt_fecha=fmt_fecha, fmt_peso=fmt_peso)

@app.route('/caja/movimiento', methods=['POST'])
@login_required
def nuevo_movimiento():
    f    = request.form
    suc  = f.get('sucursal') or sucursal_usuario()
    if suc == 'ambas': suc = 'Roca'
    tipo = f.get('tipo_movimiento','ingreso')
    with get_db() as db:
        db.execute("""INSERT INTO cobros (fecha,cliente,aseguradora,sucursal,concepto,metodo,monto,tipo_movimiento,notas,usuario_id)
                      VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (f['fecha'], f.get('cliente') or tipo.capitalize(), f.get('aseguradora'),
             suc, f.get('concepto'), f.get('metodo','Efectivo'),
             float(f.get('monto') or 0), tipo, f.get('notas'), session['user_id']))
        db.commit()
    labels = {'ingreso':'Ingreso','gasto':'Gasto','retiro':'Retiro'}
    flash(f"{labels.get(tipo,'Movimiento')} registrado",'ok')
    return redirect(url_for('caja'))

@app.route('/caja/cobro', methods=['POST'])
@login_required
def nuevo_cobro():
    # Mantener compatibilidad — redirige a nuevo_movimiento
    return nuevo_movimiento()

@app.route('/caja/eliminar/<int:cid>', methods=['POST'])
@login_required
def eliminar_cobro(cid):
    with get_db() as db:
        db.execute("DELETE FROM cobros WHERE id=?",(cid,))
        db.commit()
    flash('Movimiento eliminado','ok')
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

@app.route('/exportar/vencimientos-excel')
@login_required
def exportar_vencimientos_excel():
    suc = sucursal_usuario()
    today = date.today()
    limite = (today + timedelta(days=30)).strftime('%Y-%m-%d')
    hoy_str = today.strftime('%Y-%m-%d')
    with get_db() as db:
        if suc == 'ambas':
            rows = db.execute("""SELECT * FROM polizas WHERE activa=1
                AND fecha_venc>=? AND fecha_venc<=? ORDER BY fecha_venc""",
                (hoy_str, limite)).fetchall()
        else:
            rows = db.execute("""SELECT * FROM polizas WHERE activa=1 AND sucursal=?
                AND fecha_venc>=? AND fecha_venc<=? ORDER BY fecha_venc""",
                (suc, hoy_str, limite)).fetchall()
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Vencimientos 30 días'
        headers = ['Nº Póliza','Aseguradora','Sucursal','Nombre','DNI','Celular',
                   'Domicilio','Localidad','Marca','Modelo','Año','Patente',
                   'Vencimiento','Días restantes','Premio','Modalidad']
        header_fill = PatternFill('solid', fgColor='1e2230')
        header_font = Font(bold=True, color='e8c84a')
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        for row_idx, r in enumerate(rows, 2):
            dias = (datetime.strptime(r['fecha_venc'],'%Y-%m-%d').date() - today).days
            ws.append([r['npoliza'], r['aseguradora'], r['sucursal'], r['nombre'],
                       r['dni'], r['celular'] or '', r['domicilio'], r['localidad'],
                       r['marca'], r['modelo'], r['anio'], r['patente'],
                       r['fecha_venc'], dias, r['premio'],
                       {'trimestral_unico':'Trim. único','trimestral_mensual':'Trim. mensual',
                        'bimestral_unico':'Bim. único'}.get(r['modalidad'],r['modalidad'])])
        for col in ws.columns:
            max_len = max((len(str(c.value or '')) for c in col), default=8)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 35)
        buf = io.BytesIO()
        wb.save(buf); buf.seek(0)
        return send_file(buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name=f'vencimientos_30dias_{date.today()}.xlsx')
    except ImportError:
        # fallback CSV si no hay openpyxl
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(['Póliza','Aseguradora','Sucursal','Nombre','DNI','Celular',
                    'Domicilio','Localidad','Marca','Modelo','Año','Patente','Vencimiento','Días','Premio'])
        for r in rows:
            dias = (datetime.strptime(r['fecha_venc'],'%Y-%m-%d').date() - today).days
            w.writerow([r['npoliza'],r['aseguradora'],r['sucursal'],r['nombre'],
                        r['dni'],r['celular'] or '',r['domicilio'],r['localidad'],
                        r['marca'],r['modelo'],r['anio'],r['patente'],r['fecha_venc'],dias,r['premio']])
        out.seek(0)
        from flask import Response
        return Response(out.getvalue(), mimetype='text/csv',
            headers={"Content-Disposition":f"attachment;filename=vencimientos_{date.today()}.csv"})

@app.route('/api/poliza/<int:pid>')
@login_required
def api_poliza(pid):
    with get_db() as db:
        p = db.execute("SELECT * FROM polizas WHERE id=?", (pid,)).fetchone()
    if not p: return jsonify({}), 404
    return jsonify(dict(p))

@app.route('/api/buscar-cliente')
@login_required
def api_buscar_cliente():
    q = request.args.get('q','').strip()
    if len(q) < 2:
        return jsonify([])
    suc = sucursal_usuario()
    # Busca todas las pólizas que coincidan — el frontend agrupa por cliente
    sql = """SELECT id, nombre, dni, domicilio, cp, localidad, provincia,
                    cond_iva, marca, modelo, anio, patente, motor, chasis,
                    tipo_vehiculo, carroceria, uso, origen, celular
             FROM polizas WHERE activa=1
             AND (nombre LIKE ? OR dni LIKE ? OR patente LIKE ?)"""
    params = [f'%{q}%', f'%{q}%', f'%{q}%']
    if suc != 'ambas':
        sql += " AND sucursal=?"
        params.append(suc)
    sql += " ORDER BY nombre, creado DESC LIMIT 30"
    with get_db() as db:
        rows = db.execute(sql, params).fetchall()
    # Agrupar por cliente (dni o nombre), listar sus patentes
    clientes = {}
    for r in rows:
        key = r['dni'] or r['nombre']
        if key not in clientes:
            clientes[key] = dict(r)
            clientes[key]['patentes'] = []
        pat = r['patente']
        if pat and pat not in [p2['patente'] for p2 in clientes[key]['patentes']]:
            clientes[key]['patentes'].append({
                'patente': pat, 'marca': r['marca'], 'modelo': r['modelo'],
                'anio': r['anio'], 'motor': r['motor'], 'chasis': r['chasis'],
                'tipo_vehiculo': r['tipo_vehiculo'], 'carroceria': r['carroceria'],
                'uso': r['uso'], 'origen': r['origen'], 'id': r['id']
            })
    return jsonify(list(clientes.values())[:12])

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

@app.route('/siniestros/estado/<int:sid>', methods=['POST'])
@login_required
def cambiar_estado_siniestro(sid):
    nuevo_estado = request.form.get('estado','Abierto')
    with get_db() as db:
        db.execute("UPDATE siniestros SET estado=? WHERE id=?", (nuevo_estado, sid))
        db.commit()
    return jsonify({'ok': True, 'estado': nuevo_estado})

@app.route('/siniestros/editar/<int:sid>', methods=['POST'])
@login_required
def editar_siniestro(sid):
    f = request.form
    with get_db() as db:
        db.execute("""UPDATE siniestros SET
            aseguradora=?,tipo_siniestro=?,fecha_siniestro=?,fecha_denuncia=?,
            nombre_asegurado=?,dni_asegurado=?,npoliza=?,patente=?,vehiculo=?,anio_vehiculo=?,
            lugar_siniestro=?,descripcion=?,danos=?,
            tercero_nombre=?,tercero_patente=?,tercero_tel=?,tercero_seguro=?,
            estado=?,obs=?
            WHERE id=?""",
            (f['aseguradora'], f['tipo_siniestro'], f['fecha_siniestro'], f.get('fecha_denuncia'),
             f['nombre_asegurado'], f.get('dni_asegurado'), f.get('npoliza'),
             f.get('patente','').upper(), f.get('vehiculo'), f.get('anio_vehiculo'),
             f.get('lugar_siniestro'), f['descripcion'], f.get('danos'),
             f.get('tercero_nombre'), f.get('tercero_patente'),
             f.get('tercero_tel'), f.get('tercero_seguro'),
             f.get('estado','Abierto'), f.get('obs'), sid))
        db.commit()
    flash('Siniestro actualizado','ok')
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
