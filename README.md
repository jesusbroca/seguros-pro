# SegurosPro v2 — Sistema de Gestión de Seguros

## Primer acceso
- URL: la que te asigne Railway (ej: https://seguros-pro.railway.app)
- Email: admin@seguros.com
- Contraseña: admin123
- ⚠ CAMBIÁ LA CONTRASEÑA al primer ingreso (Menú → Usuarios)

## Funciones
- Gestión de pólizas NRE y ATM con documentos PDF automáticos
- 2 sucursales: Roca y Sarmiento (cada usuario ve solo la suya)
- Admin ve ambas sucursales con totales separados
- Caja con cobros por método, aseguradora y sucursal
- Alertas de vencimientos a 30 días
- Exportación CSV de pólizas y cobros

## Documentos generados automáticamente
| Aseguradora | Documentos |
|------------|-----------|
| NRE | Mercosur 🌎 + Certificado de Cobertura 📄 + Frente de Póliza 📃 |
| ATM | Mercosur 🌎 + Certificado de Cobertura 📄 + Tarjeta de Circulación 🪪 |

## Cómo subir a Railway (paso a paso)

### Paso 1 — GitHub
1. Creá cuenta en https://github.com
2. Nuevo repositorio → "seguros-pro" (público)
3. Subí todos los archivos (botón "uploading an existing file")

### Paso 2 — Railway
1. Entrá a https://railway.app → Start a New Project
2. "Deploy from GitHub" → conectá tu cuenta → elegí "seguros-pro"
3. Railway detecta Python automáticamente y despliega

### Paso 3 — Variable de entorno
En Railway → tu proyecto → Variables → agregar:
```
SECRET_KEY = seguros-pro-clave-secreta-2025-monteros
```

### Paso 4 — Logos (opcional, mejora visual)
En Railway → tu proyecto → Variables → agregar:
(Los logos están como placeholders. Para reemplazarlos, subí
nre.png y atm.png en alta calidad a la carpeta static/logos/)

## Agregar nueva compañía (en el futuro)
1. Abrí pdf_generator.py
2. Copiá el bloque de funciones de NRE o ATM como plantilla
3. Creá las funciones para la nueva compañía
4. Agregala al diccionario DOCUMENTOS al final del archivo
5. Actualizá el select de aseguradora en _modal_poliza.html

## Estructura de archivos
```
seguros_v2/
├── app.py                    ← Servidor y rutas
├── pdf_generator.py          ← Generación de PDFs
├── requirements.txt
├── Procfile
├── seguros.db                ← Se crea automático
├── static/logos/
│   ├── nre.png               ← Logo NRE (reemplazar con original)
│   └── atm.png               ← Logo ATM (reemplazar con original)
└── templates/
    ├── base.html
    ├── login.html
    ├── index.html
    ├── polizas.html
    ├── clientes.html
    ├── vencimientos.html
    ├── caja.html
    ├── usuarios.html
    ├── _modal_poliza.html
    └── _docs_btns.html
```
