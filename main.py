import re
import argparse
import json
from pathlib import Path
import requests

try:
    from generar_html import crear_html
except ImportError:
    crear_html = None


# Carpeta base donde reside este script (para rutas relativas y portabilidad)
BASE_DIR = Path(__file__).resolve().parent


# ==============================================================================
# DICCIONARIOS Y CONFIGURACIONES
# ==============================================================================

# Códigos de moneda estándar según la norma internacional ISO 4217
MONEDAS_ISO = {
    'USD': 'USD',
    'ARS': 'ARS',
    'UYU': 'UYU',
    'CLP': 'CLP',
    'BRL': 'BRL',
    'EUR': 'EUR'
}

# Mapeo de símbolos, abreviaturas y nombres hacia sus respectivos códigos ISO 4217
MAPEO_MONEDAS = {
    'USD': 'USD',
    'U$S': 'USD',
    'U$D': 'USD',
    'U$': 'USD',
    'US$': 'USD', 
    'DÓLARES': 'USD', 
    'DOLARES': 'USD',
    'DÓLAR': 'USD',
    'DOLAR': 'USD',
    'ARS': 'ARS',
    'AR$': 'ARS',
    '$AR': 'ARS',
    '$': 'ARS', 
    'PESOS ARGENTINOS': 'ARS', 
    'PESO ARGENTINO': 'ARS',
    'PESOS URUGUAYOS': 'UYU',
    'PESO URUGUAYO': 'UYU',
    '$U': 'UYU',
    'CLP$': 'CLP',
    'PESOS CHILENOS': 'CLP', 
    'PESO CHILENO': 'CLP',
    'PESOS': 'ARS',
    'PESO': 'ARS',
    'UYU': 'UYU',
    'CLP': 'CLP', 
    'BRL': 'BRL', 
    'R$': 'BRL',
    'REALES': 'BRL',
    'REAL': 'BRL',
    'EUR': 'EUR',
    'EUROS': 'EUR',
    'EURO': 'EUR',
    '€': 'EUR'
}

# Factores multiplicadores para cantidades expresadas en palabras o abreviaturas
MULTIPLICADORES = {
    'MIL MILLONES': 1000000000,
    'MIL MILLÓN': 1000000000,
    'MIL MILLON': 1000000000,
    'MIL': 1000, 
    'K': 1000,
    'MILLON': 1000000, 
    'MILLÓN': 1000000, 
    'MILLONES': 1000000, 
    'M': 1000000,
    'BILLON': 1000000000000,
    'BILLÓN': 1000000000000,
    'BILLONES': 1000000000000,
    'B': 1000000000
}

# Lista de símbolos monetarios
LISTA_SIMBOLOS = ['$', 'U$S', 'U$D', 'US$', 'U$', '$U', 'AR$', '$AR', 'CLP$', 'R$', '€']

# Lista de denominaciones coloquiales de monedas
LISTA_COLOQUIAL = [
    'PESOS ARGENTINOS', 'PESO ARGENTINO',
    'PESOS URUGUAYOS', 'PESO URUGUAYO',
    'PESOS CHILENOS', 'PESO CHILENO',
    'PESOS', 'PESO',
    'DÓLARES', 'DOLARES', 'DÓLAR', 'DOLAR',
    'REALES', 'REAL',
    'EUROS', 'EURO'
]


# ==============================================================================
# EXPRESIONES REGULARES
# ==============================================================================

# Delimitador que indica el inicio de un bloque (noticia o aviso)
DIVIDIR_TXT = r"##"

# Alfabeto numérico y separadores según teoría de lenguajes formales
DIGITOS = r"[0-9]" 
PUNTO_COMA = r"(\.|,)" 

# Monto numérico construido con los símbolos anteriores (unión y concatenación)
MONTO = DIGITOS + r"+" + r"(" + PUNTO_COMA + DIGITOS + r"+)*"

# Espacios y conectores
ESPACIOS = r"( |\n|\t)*"
CONECTOR = r"(DE" + ESPACIOS + r"|)"

# Símbolo de porcentaje y número para porcentajes
SIGNO_PORCENTAJE = r"(%|POR CIENTO|PORCIENTO)"
NUMERO_PORCENTAJE = DIGITOS + r"+(" + PUNTO_COMA + DIGITOS + r"+)?"
ER_PORCENTAJE = r"(" + NUMERO_PORCENTAJE + ESPACIOS + SIGNO_PORCENTAJE + r")"

# construcción de expresiones regulares usando las listas y diccionarios
# se ordenan primero los mas largos para que se evalue "peso argentino" antes que "peso"
# y se usa re.escape para evitar errores con caracteres como el '$'.
patrones_monedas_iso = [re.escape(m) for m in sorted(MONEDAS_ISO.keys(), key=len, reverse=True)]
ISO_4217 = r"(" + "|".join(patrones_monedas_iso) + r")"

patrones_simbolos = [re.escape(s) for s in sorted(LISTA_SIMBOLOS, key=len, reverse=True)]
SIMBOLO = r"(" + "|".join(patrones_simbolos) + r")"

patrones_coloquial = [re.escape(c) for c in sorted(LISTA_COLOQUIAL, key=len, reverse=True)]
COLOQUIAL = r"(" + "|".join(patrones_coloquial) + r")"

# se usa \b por que si no detectaba la b en BRL como multiplicador
patrones_mult = [re.escape(m) for m in sorted(MULTIPLICADORES.keys(), key=len, reverse=True)]
MULTIPLICADOR = r"\b(" + "|".join(patrones_mult) + r")\b"


# ==============================================================================
# ESTRUCTURAS SINTÁCTICAS DE DINERO
# ==============================================================================

# 1. Estructura ISO + MONTO (ej: "USD 1000", "USD 1000 MILLONES")
ESTRUCTURA_ISO = r"(" + ISO_4217 + ESPACIOS + MONTO + r")"
ESTRUCTURA_ISO_2 = r"(" + MONTO + ESPACIOS + ISO_4217 + r")"
ISO_MULTIPLICADOR = r"(" + ISO_4217 + ESPACIOS + MONTO + ESPACIOS + MULTIPLICADOR + r")"

# 2. Estructura SIMBOLO + MONTO (ej: "$ 1000", "$ 1000 MILLONES", "u$s 4.500")
ESTRUCTURA_SIMBOLO = r"(" + SIMBOLO + ESPACIOS + MONTO + r")"
ESTRUCTURA_SIMBOLO_2 = r"(" + MONTO + ESPACIOS + SIMBOLO + r")"
SIMBOLO_MULTIPLICADOR = r"(" + SIMBOLO + ESPACIOS + MONTO + ESPACIOS + MULTIPLICADOR + r")"

# 3. Estructura MONTO + MULTIPLICADOR + FORMA COLOQUIAL (ej: "50 MILLONES DE PESOS", "1000 DOLARES")
ESTRUCTURA_COLOQUIAL = r"(" + MONTO + ESPACIOS + MULTIPLICADOR + ESPACIOS + CONECTOR + ESPACIOS + COLOQUIAL + r")"
ESTRUCTURA_COLOQUIAL_SIMPLE = r"(" + MONTO + ESPACIOS + COLOQUIAL + r")"

# 4. Estructura con monto y multiplicador suelto (ej: "6 millones de contado", "10 mil")
ESTRUCTURA_SOLO_MULTIPLICADOR = r"(" + MONTO + ESPACIOS + MULTIPLICADOR + r")"

# Unión de todas las estructuras posibles de dinero
ESTRUCTURAS_DINERO = (
    r"(" +
    ISO_MULTIPLICADOR + r"|" +
    SIMBOLO_MULTIPLICADOR + r"|" +
    ESTRUCTURA_COLOQUIAL + r"|" +
    ESTRUCTURA_ISO + r"|" +
    ESTRUCTURA_ISO_2 + r"|" +
    ESTRUCTURA_SIMBOLO + r"|" +
    ESTRUCTURA_SIMBOLO_2 + r"|" +
    ESTRUCTURA_COLOQUIAL_SIMPLE + r"|" +
    ESTRUCTURA_SOLO_MULTIPLICADOR +
    r")"
)

# Patrón para identificar descuentos/recargos a aplicar sobre el precio exhibido (promociones)
# Distingue promociones activas ("con 15% de descuento") de variaciones estadísticas ("subió 7%")
ER_PROMO_APLICABLE = (
    r"(?:CON\s+)?(" + NUMERO_PORCENTAJE + r")\s*%\s*"
    r"(?:DE\s+)?(DESCUENTO|OFF|REBAJA|MENOS|RECARGO)"
)


# ==============================================================================
# OBTENCIÓN DE COTIZACIONES Y CONVERSIÓN DE MONEDAS
# ==============================================================================

def obtener_cotizacion(moneda, cotizacion_manual=None):
    """
    Obtiene el valor de una moneda extranjera en pesos argentinos (ARS).
    Si se pasó cotización manual por argumento, la utiliza.
    Si no, consulta la API oficial (dolarapi.com) o usa el archivo local cotizaciones.json.
    """
    if moneda == "ARS":
        return 1.0

    # Si hay cotización manual ingresada por argumento la usamos
    if cotizacion_manual is not None:
        return float(cotizacion_manual)
    
    # Intento de consulta en línea a la API pública
    url = "https://dolarapi.com/v1/cotizaciones"
    try:
        respuesta = requests.get(url, timeout=3)
        if respuesta.status_code == 200:
            datos = respuesta.json()
            for c in datos:
                if c.get("moneda") == moneda:
                    return float(c.get("venta", c.get("compra", 1200)))
    except Exception:
        pass  # Si no hay conexión o falla la API, pasamos al archivo local

    # Modo sin conexión: lectura de cotizaciones.json guardado en el proyecto
    ruta_cotizaciones = BASE_DIR / "cotizaciones.json"
    if ruta_cotizaciones.exists():
        try:
            with open(ruta_cotizaciones, 'r', encoding='utf-8') as f:
                lista_cotizaciones = json.load(f)
                for c in lista_cotizaciones:
                    if c.get("moneda") == moneda:
                        return float(c.get("venta", 1200))
        except Exception:
            pass

    return None


def convertir_moneda(monto, moneda_origen, moneda_destino, cotizacion_manual=None):
    """
    Convierte un monto entre cualquier par de monedas triangulando con ARS como base.
    Soporta cotización manual tanto si la moneda extranjera es origen como destino.
    """
    if not moneda_destino or moneda_origen == moneda_destino:
        return None

    # 1. Tasa de la moneda de origen respecto a ARS
    if moneda_origen == "ARS":
        tasa_origen = 1.0
    elif cotizacion_manual and moneda_destino == "ARS":
        tasa_origen = float(cotizacion_manual)
    else:
        tasa_origen = obtener_cotizacion(moneda_origen, cotizacion_manual if moneda_origen != "ARS" else None)

    # 2. Tasa de la moneda de destino respecto a ARS
    if moneda_destino == "ARS":
        tasa_destino = 1.0
    elif cotizacion_manual and moneda_destino != "ARS":
        tasa_destino = float(cotizacion_manual)
    else:
        tasa_destino = obtener_cotizacion(moneda_destino)

    if not tasa_origen or not tasa_destino:
        return {"error": f"No se pudo cotizar {moneda_origen} a {moneda_destino}"}

    # Conversión universal pasando por ARS:
    monto_en_pesos = monto * tasa_origen
    monto_final = monto_en_pesos / tasa_destino

    return {
        "moneda_destino": moneda_destino,
        "monto_convertido": round(monto_final, 2)
    }


# ==============================================================================
# RESOLUCIÓN DE AMBIGÜEDAD Y PROCESAMIENTO NUMÉRICO
# ==============================================================================

def resolver_ambiguedad(texto):
    """
    Distingue si los puntos y comas corresponden a separadores de miles o decimales.
    Regla: '1.500' es 1500 (3 dígitos finales = miles); '1,5' es uno y medio.
    """
    monto_str = re.sub(r"[^\d.,]", "", texto)
    if not monto_str:
        return 0.0

    # 1. Caso donde coexisten punto y coma (ej: '1.234,56' o '1,234.56')
    if '.' in monto_str and ',' in monto_str:
        if monto_str.rfind('.') > monto_str.rfind(','):
            # Formato anglosajón: '1,234.56' -> borramos comas de miles
            return float(monto_str.replace(',', ''))
        else:
            # Formato latino: '1.234,56' -> borramos puntos de miles y cambiamos coma por punto
            return float(monto_str.replace('.', '').replace(',', '.'))
    
    # 2. Caso donde solo hay puntos (ej: '1.500' o '1.5')
    elif '.' in monto_str:
        partes = monto_str.split('.')
        # Si la última parte tiene exactamente 3 dígitos, se asume separador de miles
        if len(partes[-1]) == 3 and len(partes) > 1:
            return float(monto_str.replace('.', ''))
        else:
            return float(monto_str)
            
    # 3. Caso donde solo hay comas (ej: '1,5' o '1,500')
    elif ',' in monto_str:
        partes = monto_str.split(',')
        if len(partes[-1]) == 3 and len(partes) > 1:
            return float(monto_str.replace(',', ''))
        else:
            return float(monto_str.replace(',', '.'))
            
    # 4. Número entero simple sin separadores (ej: '1500')
    return float(monto_str)


def resolver_monto(texto):
    """
    Extrae el valor numérico considerando multiplicadores (millones, mil, M, etc.).
    """
    factor = 1
    m = re.search(MULTIPLICADOR, texto, re.IGNORECASE)
    if m:
        palabra_mult = m.group(1).upper()
        if palabra_mult in MULTIPLICADORES:
            factor = MULTIPLICADORES[palabra_mult]
        texto = texto.replace(m.group(0), "", 1)

    return resolver_ambiguedad(texto) * factor


def reconocer_moneda(texto):
    """
    Identifica la moneda presente en un texto y retorna su código estándar ISO 4217.
    Si no encuentra ninguna moneda explícita, asume ARS (moneda local por defecto).
    """
    texto_upper = texto.upper()
    patrones_ordenados = sorted(MAPEO_MONEDAS.keys(), key=len, reverse=True)
    
    for patron in patrones_ordenados:
        if patron in texto_upper:
            return MAPEO_MONEDAS[patron]
            
    return "ARS"


def formatear_monto(monto, moneda):
    """
    Normaliza la representación visual de un monto a formato estándar:
    - ARS: $6.000.000 o $1.234,56
    - USD: USD 4.500
    - Otras: CODIGO <monto>
    """
    if float(monto).is_integer():
        num_str = f"{int(monto):,}".replace(",", ".")
    else:
        num_str = f"{monto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    if moneda == "ARS":
        return f"${num_str}"
    elif moneda == "USD":
        return f"USD {num_str}"
    else:
        return f"{moneda} {num_str}"


def verificar_promo_pendiente(texto_bloque):
    """
    Busca si en el texto de la noticia hay una promoción o descuento activo que deba
    calcularse sobre el precio exhibido (ej: 'con 15% de descuento', '10% off').
    Ignora variaciones históricas ya aplicadas ('representa un aumento del 9%').
    """
    match = re.search(ER_PROMO_APLICABLE, texto_bloque, re.IGNORECASE)
    if match:
        texto_porc = match.group(1)
        porcentaje = resolver_ambiguedad(texto_porc)
        es_recargo = "RECARGO" in match.group(0).upper()
        return {
            "porcentaje": porcentaje,
            "es_recargo": es_recargo
        }
    return None


# ==============================================================================
# LECTURA Y PROCESAMIENTO DE NOTICIAS
# ==============================================================================

def leer_archivo(ruta):
    """Lee el archivo de texto plano en UTF-8."""
    with open(ruta, 'r', encoding='utf-8') as f:
        content = f.read()
    return content


def extraer_texto(ruta=None):
    """
    Divide el archivo de entrada en bloques de noticias utilizando '##' como separador.
    """
    if ruta is None:
        ruta = BASE_DIR / "data.txt"
    bloques_validos = []
    content = leer_archivo(ruta)
    bloques = re.split(DIVIDIR_TXT, content)

    for b in bloques:
        bloque_limpio = b.strip()
        if bloque_limpio:
            bloques_validos.append(bloque_limpio)

    return bloques_validos


def procesar_bloque_noticia(bloque, moneda_destino=None, cotizacion_manual=None):
    """
    Procesa un bloque de noticia individual:
    - Extrae el título y los montos detectados.
    - Genera la noticia normalizada (con los precios reemplazados in-place).
    - Aplica descuentos/aumentos pendientes si corresponden agregando 'Precio Final:'.
    - Si se especificó --a, genera también la noticia convertida a la divisa solicitada.
    """
    lineas = bloque.splitlines()
    titulo = lineas[0].strip() if lineas else "Sin título"

    # Encontramos todas las apariciones de montos en el bloque
    matches = list(re.finditer(ESTRUCTURAS_DINERO, bloque, re.IGNORECASE))
    
    montos_detalle = []
    texto_normalizado = bloque
    texto_convertido = bloque if moneda_destino else None

    # Procesamos los reemplazos de atrás hacia adelante para no alterar los índices de caracteres
    for match in reversed(matches):
        texto_capturado = match.group(0).strip()
        monto_num = resolver_monto(texto_capturado)
        moneda_orig = reconocer_moneda(texto_capturado)
        
        # 1. Monto normalizado en su moneda original
        monto_norm_str = formatear_monto(monto_num, moneda_orig)
        ini, fin = match.span()
        texto_normalizado = texto_normalizado[:ini] + monto_norm_str + texto_normalizado[fin:]

        # 2. Monto convertido si se solicitó --a
        monto_conv_num = None
        if moneda_destino:
            if moneda_orig == moneda_destino:
                monto_conv_num = monto_num
            else:
                res_conv = convertir_moneda(monto_num, moneda_orig, moneda_destino, cotizacion_manual)
                if res_conv and "monto_convertido" in res_conv:
                    monto_conv_num = res_conv["monto_convertido"]
                else:
                    monto_conv_num = monto_num
            
            monto_conv_str = formatear_monto(monto_conv_num, moneda_destino)
            texto_convertido = texto_convertido[:ini] + monto_conv_str + texto_convertido[fin:]

        detalle = {
            "texto_original": texto_capturado,
            "monto_original": monto_num,
            "moneda_original": moneda_orig
        }
        if moneda_destino:
            detalle["monto_convertido"] = monto_conv_num
            detalle["moneda_destino"] = moneda_destino

        montos_detalle.append(detalle)

    # Invertimos para que montos_detalle quede en el orden original de lectura
    montos_detalle.reverse()

    # Verificamos si hay promociones o descuentos a calcular al final de la noticia
    promo = verificar_promo_pendiente(bloque)
    if promo and montos_detalle:
        p = promo["porcentaje"]
        monto_base = montos_detalle[0]["monto_original"]
        moneda_base = montos_detalle[0]["moneda_original"]

        # Cálculo de precio final con descuento o recargo
        if promo["es_recargo"]:
            final_num = monto_base * (1 + p / 100)
        else:
            final_num = monto_base * (1 - p / 100)

        final_norm_str = formatear_monto(final_num, moneda_base)
        texto_normalizado += f" Precio Final: {final_norm_str}"

        # Si hay conversión, calculamos el precio final en la moneda destino
        if moneda_destino:
            if moneda_base == moneda_destino:
                final_conv_num = final_num
            else:
                res_final_conv = convertir_moneda(final_num, moneda_base, moneda_destino, cotizacion_manual)
                final_conv_num = res_final_conv.get("monto_convertido", final_num)
            final_conv_str = formatear_monto(final_conv_num, moneda_destino)
            texto_convertido += f" Precio Final: {final_conv_str}"

    resultado = {
        "titulo": titulo,
        "noticia_original": bloque,
        "noticia_normalizada": texto_normalizado,
        "montos_detalle": montos_detalle
    }

    if moneda_destino:
        resultado["noticia_convertida"] = texto_convertido

    return resultado


# ==============================================================================
# PUNTO DE ENTRADA Y ARGUMENTOS CLI
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Trabajo Práctico Integrador - FTI: Tema 10 (Precios y montos de dinero)."
    )
    ####
    #argumentos
    ####
    #archivo. opcional
    parser.add_argument("archivo",nargs="?",default=None,help="Archivo de noticias a procesar (por defecto usa data.txt en la carpeta del script).")

    # 
    parser.add_argument("--ruta",type=str,default=None,help="Ruta alternativa al archivo de texto.")

    # moneda destino
    parser.add_argument("--a",type=str,choices=list(MONEDAS_ISO.keys()),help="Moneda a la que se desea convertir los montos (ej: ARS, USD, EUR, CLP, etc.).")

    # cotizacion manual. opcional
    parser.add_argument("--cotizacion",type=float,help="Cotización manual para la conversión.")
    
    # por si no se quiere todo el json
    parser.add_argument("--solo-texto",action="store_true",help="Muestra únicamente las noticias procesadas con formato de texto plano.")

    args = parser.parse_args()

    # Prioridad: archivo posicional > flag --ruta > data.txt local
    ruta_elegida = args.archivo or args.ruta or (BASE_DIR / "data.txt")

    bloques = extraer_texto(ruta_elegida)
    noticias_procesadas = []

    for bloque in bloques:
        resultado_bloque = procesar_bloque_noticia(
            bloque,
            moneda_destino=args.a,
            cotizacion_manual=args.cotizacion
        )
        noticias_procesadas.append(resultado_bloque)

    if crear_html:
        crear_html(noticias_procesadas, BASE_DIR / "gaceta.html", moneda_destino=args.a)


    # Salida por consola
    if args.solo_texto:
        for n in noticias_procesadas:
            texto_a_mostrar = n.get("noticia_convertida") or n["noticia_normalizada"]
            print(f"## {n['titulo']}\n{texto_a_mostrar}\n")
    else:
        print(json.dumps(noticias_procesadas, indent=4, ensure_ascii=False))
