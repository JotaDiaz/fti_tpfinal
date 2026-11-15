import re
import argparse
import json
from pathlib import Path
import requests

try:
    from generar_html import crear_html
except ImportError:
    crear_html = None


# Carpeta base donde reside este script (para rutas relativas y portabilidad).
# Ejemplo: "/home/usuario/FTI/tp_final"
CARPETA_BASE_DEL_PROGRAMA = Path(__file__).resolve().parent


# ==============================================================================
# DICCIONARIOS Y CONFIGURACIONES
# ==============================================================================

# Códigos ISO 4217 que reconoce el programa.
# Ejemplo: 'USD' para dólar estadounidense, 'ARS' para peso argentino.
CODIGOS_ISO_4217_SOPORTADOS = {
    'USD': 'USD',
    'ARS': 'ARS',
    'UYU': 'UYU',
    'CLP': 'CLP',
    'BRL': 'BRL',
    'EUR': 'EUR'
}

# Traduce símbolos, abreviaturas y nombres del texto a código ISO.
# Ejemplo: 'u$s' -> 'USD', '$' -> 'ARS', 'pesos chilenos' -> 'CLP'.
MONEDA_POR_SIMBOLO_O_NOMBRE = {
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

# Factor numérico de cada multiplicador.
# Ejemplo: 'MILLONES' -> 1.000.000, 'MIL' -> 1.000, 'M' -> 1.000.000.
FACTOR_POR_MULTIPLICADOR = {
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

# Abreviaturas que multiplican un monto y que solo se aceptan junto a una
# moneda explícita (símbolo o código ISO). Ejemplos: "$1,2 M", "USD 5 K".
ABREVIATURAS_DE_MULTIPLICADOR = ['M', 'K', 'B']

# Listas ya ordenadas de mayor a menor longitud para que el reconocimiento
# pruebe primero lo más largo ("MIL MILLONES" antes que "MIL",
# "PESOS ARGENTINOS" antes que "PESOS", "U$S" antes que "$").
MULTIPLICADORES_EN_PALABRAS = sorted(
    [k for k in FACTOR_POR_MULTIPLICADOR if k not in ABREVIATURAS_DE_MULTIPLICADOR],
    key=len, reverse=True
)
MONEDAS_POR_LONGITUD = sorted(MONEDA_POR_SIMBOLO_O_NOMBRE.keys(), key=len, reverse=True)


# ==============================================================================
# EXPRESIONES REGULARES
# ==============================================================================

# Notación: solo unión (|), concatenación, clausura de Kleene (*) y
# alternativa vacía (ε). Cada constante incluye un ejemplo de lo que reconoce.

# Línea que marca el comienzo de una noticia o aviso.
# Ejemplo: "## Sube el precio de la nafta"
MARCA_DE_INICIO_DE_NOTICIA = r"##"

# --- Alfabeto numérico --------------------------------------------------------

# Un dígito decimal. Ejemplo: "7"
DIGITO_DECIMAL = r"(0|1|2|3|4|5|6|7|8|9)"

# Uno o más dígitos. Ejemplo: "2026"
SECUENCIA_DE_DIGITOS = DIGITO_DECIMAL + DIGITO_DECIMAL + r"*"

# Espacio, tabulación, salto de línea o retorno de carro. Ejemplo: " " o "\n"
ESPACIO_EN_BLANCO = r"( |\n|\t|\r)"

# Cero o más espacios en blanco. Ejemplo: "" o "   "
ESPACIOS_OPCIONALES = ESPACIO_EN_BLANCO + r"*"

# Punto o coma, usados como separador de miles o decimal.
# Ejemplo: "1.500" (mil quinientos) o "1,5" (uno y medio).
SEPARADOR_DE_MILES_O_DECIMALES = r"(\.|,)"

# Número con separadores internos; la ambigüedad se resuelve después.
# Ejemplos: "1234", "1.500", "1.234,56".
MONTO_NUMERICO = (
    SECUENCIA_DE_DIGITOS +
    r"(" + SEPARADOR_DE_MILES_O_DECIMALES + SECUENCIA_DE_DIGITOS + r")*"
)

# Símbolo que debe seguir al monto para que el reconocimiento termine ahí.
# Ejemplos: " ", ".", ",", ")", "%".
DELIMITADOR_FINAL = r"( |\n|\t|\r|\.|,|;|:|\)|\]|\"|%|!|\?|-|/)"


# --- Multiplicadores ----------------------------------------------------------

# Palabras que multiplican un monto. Hoja cruda, lo largo va antes que "MIL".
# Ejemplos: "2,5 millones", "160 mil", "3 mil millones".
MULTIPLICADOR_EN_PALABRAS = r"(MIL MILLONES|MIL MILLÓN|MIL MILLON|MILLONES|BILLONES|MILLON|MILLÓN|BILLON|BILLÓN|MIL)"

# Abreviaturas de multiplicador. Hoja cruda. Ejemplo: "M" en "$1,2 M" o "K" en "USD 5 K".
MULTIPLICADOR_ABREVIADO = r"(M|K|B)"


# --- Monedas ------------------------------------------------------------------

# Códigos ISO 4217 soportados.
CODIGO_DE_MONEDA_ISO = r"(USD|ARS|UYU|CLP|BRL|EUR)"

# Símbolos monetarios.
SIMBOLO_DE_MONEDA = r"(CLP\$|U\$S|U\$D|US\$|AR\$|\$AR|U\$|\$U|R\$|\$|€)"

NOMBRE_DE_MONEDA_COLOQUIAL = r"(PESOS ARGENTINOS|PESOS URUGUAYOS|PESO ARGENTINO|PESOS CHILENOS|PESO URUGUAYO|PESO CHILENO|DÓLARES|DOLARES|REALES|PESOS|DÓLAR|DOLAR|EUROS|PESO|REAL|EURO)"

# Ejemplos: "millones DE dólares", "mil pesos".
CONECTOR_DE = r"(DE" + ESPACIOS_OPCIONALES + r"|)"


# ==============================================================================
# ESTRUCTURAS SINTÁCTICAS DE DINERO
# Se definen sin DELIMITADOR_FINAL; se agrega una sola vez en EXPRESION_DE_MONTO.
# ==============================================================================

# Monto con código ISO y multiplicador en palabras.
# Ejemplo: "USD 100 millones".
MONTO_ISO_CON_MULTIPLICADOR = (
    r"(" + CODIGO_DE_MONEDA_ISO + ESPACIOS_OPCIONALES + MONTO_NUMERICO +
    ESPACIOS_OPCIONALES + MULTIPLICADOR_EN_PALABRAS + r")"
)

# Monto con símbolo y multiplicador en palabras.
# Ejemplo: "$ 5,4 millones".
MONTO_SIMBOLO_CON_MULTIPLICADOR = (
    r"(" + SIMBOLO_DE_MONEDA + ESPACIOS_OPCIONALES + MONTO_NUMERICO +
    ESPACIOS_OPCIONALES + MULTIPLICADOR_EN_PALABRAS + r")"
)

# Monto con código ISO y abreviatura de multiplicador.
# Ejemplo: "USD 5 K".
MONTO_ISO_CON_MULTIPLICADOR_ABREVIADO = (
    r"(" + CODIGO_DE_MONEDA_ISO + ESPACIOS_OPCIONALES + MONTO_NUMERICO +
    ESPACIOS_OPCIONALES + MULTIPLICADOR_ABREVIADO + r")"
)

# Monto con símbolo y abreviatura de multiplicador.
# Ejemplo: "$1,2 M".
MONTO_SIMBOLO_CON_MULTIPLICADOR_ABREVIADO = (
    r"(" + SIMBOLO_DE_MONEDA + ESPACIOS_OPCIONALES + MONTO_NUMERICO +
    ESPACIOS_OPCIONALES + MULTIPLICADOR_ABREVIADO + r")"
)

# Monto con multiplicador y nombre de moneda.
# Ejemplo: "2,5 millones de dólares".
MONTO_CON_MULTIPLICADOR_Y_NOMBRE_DE_MONEDA = (
    r"(" + MONTO_NUMERICO + ESPACIOS_OPCIONALES + MULTIPLICADOR_EN_PALABRAS +
    ESPACIOS_OPCIONALES + CONECTOR_DE + ESPACIOS_OPCIONALES +
    NOMBRE_DE_MONEDA_COLOQUIAL + r")"
)

# Monto con código ISO antepuesto. Ejemplo: "USD 95".
MONTO_CON_CODIGO_ISO_ANTEPUESTO = (r"(" + CODIGO_DE_MONEDA_ISO + ESPACIOS_OPCIONALES + MONTO_NUMERICO + r")")

# Monto con código ISO pospuesto. Ejemplo: "95 USD".
MONTO_CON_CODIGO_ISO_POSPUESTO = (
    r"(" + MONTO_NUMERICO + ESPACIOS_OPCIONALES + CODIGO_DE_MONEDA_ISO + r")"
)

# Monto con símbolo antepuesto. Ejemplo: "$ 1.234,56".
MONTO_CON_SIMBOLO_ANTEPUESTO = (
    r"(" + SIMBOLO_DE_MONEDA + ESPACIOS_OPCIONALES + MONTO_NUMERICO + r")"
)

# Monto con nombre de moneda sin multiplicador.
# Ejemplo: "160 mil pesos argentinos".
MONTO_CON_NOMBRE_DE_MONEDA = (
    r"(" + MONTO_NUMERICO + ESPACIOS_OPCIONALES + NOMBRE_DE_MONEDA_COLOQUIAL + r")"
)

# Monto con multiplicador suelto.
# Ejemplo: "5 millones".
MONTO_CON_MULTIPLICADOR = (
    r"(" + MONTO_NUMERICO + ESPACIOS_OPCIONALES + MULTIPLICADOR_EN_PALABRAS + r")"
)

# Ejemplos: "$ 1.150", "u$s 4.500", "2,5 millones de dólares", "$1,2 M".
EXPRESION_DE_MONTO = (
    r"(" +
    "|".join([
        MONTO_ISO_CON_MULTIPLICADOR,
        MONTO_SIMBOLO_CON_MULTIPLICADOR,
        MONTO_ISO_CON_MULTIPLICADOR_ABREVIADO,
        MONTO_SIMBOLO_CON_MULTIPLICADOR_ABREVIADO,
        MONTO_CON_MULTIPLICADOR_Y_NOMBRE_DE_MONEDA,
        MONTO_CON_CODIGO_ISO_ANTEPUESTO,
        MONTO_CON_CODIGO_ISO_POSPUESTO,
        MONTO_CON_SIMBOLO_ANTEPUESTO,
        MONTO_CON_NOMBRE_DE_MONEDA,
        MONTO_CON_MULTIPLICADOR,
    ]) +
    r")" + DELIMITADOR_FINAL
)


# 
# OBTENCIÓN DE COTIZACIONES Y CONVERSIÓN DE MONEDAS


def obtener_cotizacion(moneda, cotizacion_manual=None):
    """
    Obtiene el valor de una moneda extranjera en pesos argentinos (ARS).
    Si se pasó cotización manual por argumento, la utiliza.
    Si no, consulta la API oficial (dolarapi.com) o usa el archivo local cotizaciones.json.
    """
    if moneda == "ARS":  # ARS vale 1
        return 1.0

    # Si hay cotización manual ingresada por argumento la usamos
    if cotizacion_manual is not None:  # manual tiene prioridad
        return float(cotizacion_manual)

    # Intento de consulta en línea a la API pública
    url = "https://dolarapi.com/v1/cotizaciones"  # API online
    try:
        respuesta = requests.get(url, timeout=1)
        if respuesta.status_code == 200:
            datos = respuesta.json()
            for c in datos:  # busca la moneda pedida
                if c.get("moneda") == moneda:
                    return float(c.get("venta", c.get("compra", 1200)))
    except Exception:
        pass  # Si no hay conexión o falla la API, pasamos al archivo local

    # Modo sin conexión: lectura de cotizaciones.json guardado en el proyecto
    ruta_cotizaciones = CARPETA_BASE_DEL_PROGRAMA / "cotizaciones.json"  # plan B offline
    if ruta_cotizaciones.exists():
        try:
            with open(ruta_cotizaciones, 'r', encoding='utf-8') as f:
                lista_cotizaciones = json.load(f)
                for c in lista_cotizaciones:  # busca la moneda en el archivo
                    if c.get("moneda") == moneda:
                        return float(c.get("venta", 1200))
        except Exception:
            pass

    return None  # sin cotización


def convertir_moneda(monto, moneda_origen, moneda_destino, cotizacion_manual=None):
    """
    Convierte un monto entre cualquier par de monedas triangulando con ARS como base.
    Soporta cotización manual tanto si la moneda extranjera es origen como destino.
    """
    if not moneda_destino or moneda_origen == moneda_destino:  # nada que convertir
        return None

    # 1. Tasa de la moneda de origen respecto a ARS
    if moneda_origen == "ARS":  # origen en pesos
        tasa_origen = 1.0
    elif cotizacion_manual and moneda_destino == "ARS":  # manual si va a ARS
        tasa_origen = float(cotizacion_manual)
    else:  # busca cotización origen
        tasa_origen = obtener_cotizacion(moneda_origen, cotizacion_manual if moneda_origen != "ARS" else None)

    # 2. Tasa de la moneda de destino respecto a ARS
    if moneda_destino == "ARS":  # destino en pesos
        tasa_destino = 1.0
    elif cotizacion_manual and moneda_destino != "ARS":  # manual si sale de ARS
        tasa_destino = float(cotizacion_manual)
    else:  # busca cotización destino
        tasa_destino = obtener_cotizacion(moneda_destino)

    if not tasa_origen or not tasa_destino:  # sin tasa no convierte
        return {"error": f"No se pudo cotizar {moneda_origen} a {moneda_destino}"}

    # Conversión universal pasando por ARS:
    monto_en_pesos = monto * tasa_origen  # pasa a ARS
    monto_final = monto_en_pesos / tasa_destino  # pasa a destino

    return {
        "moneda_destino": moneda_destino,
        "monto_convertido": round(monto_final, 2)
    }


# ==============================================================================
# RESOLUCIÓN DE AMBIGÜEDAD Y PROCESAMIENTO NUMÉRICO
# ==============================================================================

def es_parte_entera_valida(parte_entera, separador_de_miles):
    """
    Verifica que la parte entera use grupos de miles bien formados.
    Ejemplo: '1.234' con separador '.' -> True; '12.34' -> False.
    """
    grupos = parte_entera.split(separador_de_miles)  # corta por el separador

    if not grupos[0].isdigit():  # primer grupo debe ser número
        return False
    if len(grupos[0]) < 1 or len(grupos[0]) > 3:  # 1 a 3 dígitos al inicio
        return False

    for grupo in grupos[1:]:  # el resto debe ser de a 3 dígitos
        if not grupo.isdigit():
            return False
        if len(grupo) != 3:
            return False

    return True


def convertir_partes_a_numero(parte_entera, parte_decimal, separador_de_miles):
    """
    Convierte dos partes ya validadas a un número decimal.
    Ejemplo: ('1.234', '56', '.') -> 1234.56.
    """
    entero_sin_miles = parte_entera.replace(separador_de_miles, "")  # saca miles
    return float(entero_sin_miles + "." + parte_decimal)  # une como decimal


def interpretar_monto_con_dos_separadores(monto_str):
    """
    Interpreta montos que combinan punto y coma.
    Ejemplos: '1.234,56' -> 1234.56; '1,234.56' -> 1234.56.
    """
    ultimo_punto = monto_str.rfind(".")  # última aparición de cada uno
    ultima_coma = monto_str.rfind(",")

    if ultimo_punto > ultima_coma:  # el último marca el decimal
        # Formato anglosajón: coma para miles, punto para decimales.
        parte_entera, parte_decimal = monto_str.rsplit(".", 1)
        separador_de_miles = ","
    else:
        # Formato latino: punto para miles, coma para decimales.
        parte_entera, parte_decimal = monto_str.rsplit(",", 1)
        separador_de_miles = "."

    if not es_parte_entera_valida(parte_entera, separador_de_miles):  # valida miles
        return None, "separador de miles inválido"

    if not parte_decimal.isdigit():  # decimal debe ser número
        return None, "parte decimal inválida"

    valor = convertir_partes_a_numero(parte_entera, parte_decimal, separador_de_miles)  # arma el float
    return valor, None


def interpretar_monto_con_un_separador(monto_str, separador):
    """
    Interpreta montos que usan un solo tipo de separador.
    Ejemplos: '1.500' -> 1500.0; '1,5' -> 1.5; '1.234.567' -> 1234567.0.
    """
    partes = monto_str.split(separador)  # corta por el separador

    if len(partes) > 2:  # varios separadores -> todos son miles
        # Varios separadores: todos son de miles.
        parte_entera = separador.join(partes[:-1])
        ultima_parte = partes[-1]

        if not es_parte_entera_valida(parte_entera, separador):  # valida miles
            return None, "separador de miles inválido"

        if not ultima_parte.isdigit():  # último grupo debe ser número
            return None, "separador de miles inválido"
        if len(ultima_parte) != 3:  # ...de 3 dígitos
            return None, "separador de miles inválido"

        numero_sin_separadores = ""  # pega todo sin separadores
        for parte in partes:
            numero_sin_separadores += parte
        return float(numero_sin_separadores), None

    parte_entera = partes[0]
    ultima_parte = partes[1]

    # '1.500' o '1,500': el último grupo tiene 3 dígitos y el entero es corto.
    if len(ultima_parte) == 3 and parte_entera != "0" and 1 <= len(parte_entera) <= 3:
        return float(parte_entera + ultima_parte), None

    # '1.5' o '1,5': el separador es decimal.
    if not parte_entera.isdigit():
        return None, "parte entera inválida"
    if not ultima_parte.isdigit():
        return None, "parte decimal inválida"

    return float(parte_entera + "." + ultima_parte), None


def interpretar_monto(texto):
    """
    Interpreta un monto y distingue separadores de miles y decimales.
    Devuelve (valor, error): si el monto es válido, error es None.
    Ejemplos:
      '1.500'    -> (1500.0, None)
      '1,5'      -> (1.5, None)
      '1.234,56' -> (1234.56, None)
      '1.234.5'  -> (None, 'separador de miles inválido')
    """
    monto_str = ""  # solo dígitos y separadores
    for caracter in texto:
        if caracter in "0123456789.,":
            monto_str += caracter

    if not monto_str:  # sin números -> error
        return None, "no contiene dígitos"

    if monto_str[0] in ".," or monto_str[-1] in ".,":  # no puede empezar/terminar en . o ,
        return None, "separador en el extremo"

    if ".." in monto_str or ",," in monto_str or ".," in monto_str or ",." in monto_str:  # dobles -> error
        return None, "separadores consecutivos"

    tiene_punto = "." in monto_str  # decide qué caso usar
    tiene_coma = "," in monto_str

    if tiene_punto and tiene_coma:  # ej: 1.234,56
        return interpretar_monto_con_dos_separadores(monto_str)

    if tiene_punto:  # ej: 1.500
        return interpretar_monto_con_un_separador(monto_str, ".")

    if tiene_coma:  # ej: 1,5
        return interpretar_monto_con_un_separador(monto_str, ",")

    if not monto_str.isdigit():  # resto inválido
        return None, "caracteres inválidos"

    return float(monto_str), None  # entero simple


def buscar_multiplicador(texto):
    """
    Devuelve el multiplicador presente en un monto ya reconocido, o None.

    Primero busca palabras ('millones', 'mil', ...) y después abreviaturas
    exactas ('M', 'K', 'B'), para no confundir la 'B' de 'BRL' con un billón.
    Ejemplo: 'USD 100 millones' -> 'MILLONES'; '$1,2 M' -> 'M'.
    """
    texto_upper = " ".join(texto.upper().split())  # normaliza espacios y mayúsculas

    for palabra in MULTIPLICADORES_EN_PALABRAS:  # busca palabra larga primero
        if f" {palabra} " in f" {texto_upper} ":
            return palabra

    ultimo_caracter = texto_upper[-1:] if texto_upper else ""
    if ultimo_caracter in ABREVIATURAS_DE_MULTIPLICADOR:
        return ultimo_caracter

    return None


def resolver_monto(texto):
    """
    Extrae el valor numérico considerando multiplicadores (millones, mil, M, etc.).
    Devuelve None si el monto no se puede interpretar.
    Ejemplo: '2,5 millones de dólares' -> 2500000.0; '$1,2 M' -> 1200000.0.
    """
    factor = 1  # por defecto no multiplica
    palabra_mult = buscar_multiplicador(texto)  # detecta MIL, MILLONES, M...
    if palabra_mult:
        factor = FACTOR_POR_MULTIPLICADOR[palabra_mult]  # factor numérico
        indice = texto.upper().rfind(palabra_mult)  # saca la palabra del texto
        if indice != -1:
            texto = texto[:indice] + texto[indice + len(palabra_mult):]

    valor, _ = interpretar_monto(texto)  # convierte el número puro
    if valor is None:  # si falla, no hay monto
        return None

    return valor * factor  # aplica el multiplicador


def reconocer_moneda(texto):
    """
    Identifica la moneda presente en un texto y retorna su código estándar ISO 4217.
    Si no encuentra ninguna moneda explícita, asume ARS (moneda local por defecto).
    """
    texto_upper = texto.upper()  # compara en mayúsculas

    for patron in MONEDAS_POR_LONGITUD:  # prueba lo largo primero ($U antes que $)
        if patron in texto_upper:
            return MONEDA_POR_SIMBOLO_O_NOMBRE[patron]

    return "ARS"  # defecto: moneda local


def formatear_monto(monto, moneda):
    """
    Normaliza la representación visual de un monto a formato estándar:
    - ARS: $6.000.000 o $1.234,56
    - USD: USD 4.500
    - Otras: CODIGO <monto>
    """
    if float(monto).is_integer():  # entero: 6000000 -> 6.000.000
        num_str = f"{int(monto):,}".replace(",", ".")
    else:  # decimal: 1234.56 -> 1.234,56
        num_str = f"{monto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    if moneda == "ARS":  # local con $
        return f"${num_str}"
    elif moneda == "USD":  # USD con código
        return f"USD {num_str}"
    else:  # resto con código
        return f"{moneda} {num_str}"


# ==============================================================================
# LECTURA Y PROCESAMIENTO DE NOTICIAS
# ==============================================================================

def leer_archivo(ruta):
    """Lee el archivo de texto plano en UTF-8."""
    with open(ruta, 'r', encoding='utf-8') as f:
        content = f.read()  # lee todo el archivo
    return content  # devuelve el texto completo


def extraer_texto(ruta=None):
    """
    Divide el archivo de entrada en bloques de noticias. Cada bloque empieza en
    una línea que comienza con '##' y termina donde empieza el próximo '##'.
    Ejemplo: '## Sube la nafta\\nEl litro pasó de $ 1.150 a $1.234,56'.
    """
    if ruta is None:
        ruta = CARPETA_BASE_DEL_PROGRAMA / "data.txt"  # archivo por defecto

    bloques_validos = []  # lista final de noticias
    bloque_actual = []  # líneas del bloque en curso

    for linea in leer_archivo(ruta).splitlines():  # recorre línea por línea
        if linea.lstrip().startswith(MARCA_DE_INICIO_DE_NOTICIA):  # nuevo bloque con ##
            texto_anterior = "\n".join(bloque_actual).strip()  # cierra el anterior
            if texto_anterior:
                bloques_validos.append(texto_anterior)
            contenido = linea.lstrip()[len(MARCA_DE_INICIO_DE_NOTICIA):]  # saca el ##
            bloque_actual = [contenido]  # empieza bloque nuevo
        else:
            bloque_actual.append(linea)  # sigue el mismo bloque

    texto_final = "\n".join(bloque_actual).strip()  # cierra el último bloque
    if texto_final:
        bloques_validos.append(texto_final)

    return bloques_validos  # devuelve todos los bloques


def detectar_montos(bloque):
    """
    Detecta los montos del bloque. Devuelve su parte: lista de (texto, ini, fin).
    """
    # Encontramos todas las apariciones de montos en el bloque. Se agrega un
    # espacio centinela para que DELIMITADOR_FINAL funcione al final del texto.
    matches = list(re.finditer(EXPRESION_DE_MONTO, bloque + " ", re.IGNORECASE))

    # El grupo 1 es el monto; el delimitador final queda fuera del reemplazo.
    montos = []  # lista de (texto, ini, fin)
    for match in matches:  # recorre en orden de lectura
        texto_capturado = match.group(1).strip()  # monto sin espacios
        ini, fin = match.span(1)  # inicio y fin del grupo 1 (fin exclusivo)
        montos.append((texto_capturado, ini, fin))

    return montos


def normalizar_montos(bloque, montos, moneda_destino=None, cotizacion_manual=None):
    """
    Normaliza y convierte los montos. Devuelve su parte del json:
    texto normalizado, texto convertido, detalle de montos y advertencias.
    """
    montos_detalle = []  # lista de montos ok
    advertencias = []  # lista de fallos
    texto_normalizado = bloque  # copia para reemplazar
    texto_convertido = bloque if moneda_destino else None  # copia para convertir

    # Procesamos los reemplazos de atrás hacia adelante para no alterar los índices de caracteres
    for texto_capturado, ini, fin in reversed(montos):
        monto_num = resolver_monto(texto_capturado)  # número + multiplicador

        if monto_num is None:  # inválido -> a advertencias, no toca el texto
            _, motivo = interpretar_monto(texto_capturado)
            advertencias.append({
                "texto_original": texto_capturado,
                "motivo": motivo
            })
            continue

        moneda_orig = reconocer_moneda(texto_capturado)  # USD, ARS...

        # 1. Monto normalizado en su moneda original
        monto_norm_str = formatear_monto(monto_num, moneda_orig)
        texto_normalizado = texto_normalizado[:ini] + monto_norm_str + texto_normalizado[fin:]

        # 2. Monto convertido si se solicitó --a
        monto_conv_num = None
        if moneda_destino:
            if moneda_orig == moneda_destino:  # misma moneda, no convierte
                monto_conv_num = monto_num
            else:
                res_conv = convertir_moneda(monto_num, moneda_orig, moneda_destino, cotizacion_manual)  # intenta convertir
                if res_conv and "monto_convertido" in res_conv:  # ok -> usa el convertido
                    monto_conv_num = res_conv["monto_convertido"]
                else:
                    monto_conv_num = monto_num  # fallo -> deja el original
                    motivo = f"no se pudo convertir {moneda_orig} a {moneda_destino}"
                    if res_conv and "error" in res_conv:  # usa el detalle real
                        motivo = res_conv["error"]
                    advertencias.append({
                        "texto_original": texto_capturado,
                        "motivo": motivo
                    })

            monto_conv_str = formatear_monto(monto_conv_num, moneda_destino)
            texto_convertido = texto_convertido[:ini] + monto_conv_str + texto_convertido[fin:]

        detalle = {  # guarda el monto para el json
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

    return {  # devuelve su parte del json
        "texto_normalizado": texto_normalizado,
        "texto_convertido": texto_convertido,
        "montos_detalle": montos_detalle,
        "advertencias": advertencias
    }


def procesar_bloque_noticia(bloque, moneda_destino=None, cotizacion_manual=None):
    """
    Procesa un bloque de noticia individual:
    - Extrae el título y los montos detectados.
    - Genera la noticia normalizada (con los precios reemplazados in-place).
    - Si se especificó --a, genera también la noticia convertida a la divisa solicitada.
    """
    lineas = bloque.splitlines()
    titulo = lineas[0].strip() if lineas else "Sin título"  # primera línea

    montos = detectar_montos(bloque)  # 1. detecta montos

    normalizados = normalizar_montos(bloque, montos, moneda_destino, cotizacion_manual)  # 2. normaliza y convierte

    if not normalizados["montos_detalle"]:  # sin montos -> advierte
        normalizados["advertencias"].append({
            "texto_original": titulo,
            "motivo": "no se detectaron montos"
        })

    resultado = {  # 3. arma el dict final
        "titulo": titulo,
        "noticia_original": bloque,
        "noticia_normalizada": normalizados["texto_normalizado"],
        "montos_detalle": normalizados["montos_detalle"],
        "advertencias": normalizados["advertencias"]
    }

    if moneda_destino:  # agrega convertida solo si se pidió --a
        resultado["noticia_convertida"] = normalizados["texto_convertido"]

    return resultado


# ==============================================================================
# PUNTO DE ENTRADA Y ARGUMENTOS CLI
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Trabajo Práctico Integrador - FTI: Tema 10 (Precios y montos de dinero)."
    )

    parser.add_argument("archivo",nargs="?",default=None,help="Archivo de noticias a procesar (por defecto usa data.txt en la carpeta del script).")
    parser.add_argument("--ruta",type=str,default=None,help="Ruta alternativa al archivo de texto.")
    parser.add_argument("--a",type=str,choices=list(CODIGOS_ISO_4217_SOPORTADOS.keys()),help="Moneda a la que se desea convertir los montos (ej: ARS, USD, EUR, CLP, etc.).")
    parser.add_argument("--cotizacion",type=float,help="Cotización manual para la conversión.")
    # por si no se quiere todo el json
    parser.add_argument("--solo-texto",action="store_true",help="Muestra únicamente las noticias procesadas con formato de texto plano.")
    args = parser.parse_args()  # lee CLI
    ruta_elegida = args.archivo or args.ruta or (CARPETA_BASE_DEL_PROGRAMA / "data.txt")


    bloques = extraer_texto(ruta_elegida)  # parte data.txt en bloques ##
    noticias_procesadas = []

    for bloque in bloques:  # procesa bloque por bloque
        resultado_bloque = procesar_bloque_noticia(
            bloque,
            moneda_destino=args.a,
            cotizacion_manual=args.cotizacion
        )
        noticias_procesadas.append(resultado_bloque)

    if crear_html:  # genera gaceta.html si está el módulo
        crear_html(noticias_procesadas, CARPETA_BASE_DEL_PROGRAMA / "gaceta.html", moneda_destino=args.a)


    # Salida por consola
    if args.solo_texto:  # modo texto plano
        for n in noticias_procesadas:
            texto_a_mostrar = n.get("noticia_convertida") or n["noticia_normalizada"]  # convertido si hay
            print(f"## {n['titulo']}\n{texto_a_mostrar}\n")

            if n["advertencias"]:  # lista advertencias del bloque
                print("Advertencias:")
                for advertencia in n["advertencias"]:
                    print(f"- {advertencia['texto_original']}: {advertencia['motivo']}")

            print("---" * 40 + "\n")
    else:  # modo JSON, un bloque por vez
        for indice, noticia in enumerate(noticias_procesadas, start=1):
            print(json.dumps(noticia, indent=4, ensure_ascii=False))
            if indice < len(noticias_procesadas):
                print("-" * 80)  # separa bloques en modo JSON
