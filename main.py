import re
import argparse
import json
import sys
from pathlib import Path
import requests

#la carpeta actual
BASE_DIR = Path(__file__).resolve().parent


# ==============================================================================
# DICCIONARIOS Y CONFIGURACIONES
# ==============================================================================

# Códigos de moneda estándar según ISO 4217
MONEDAS_ISO = {
    'USD': 'USD',
    'ARS': 'ARS',
    'UYU': 'UYU',
    'CLP': 'CLP',
    'BRL': 'BRL',
    'EUR': 'EUR'
}

# Mapeo de símbolos y nombres junto a sus respectivos códigos ISO 4217
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

LISTA_SIMBOLOS = ['$', 'U$S', 'U$D', 'US$', 'U$', '$U', 'AR$', '$AR', 'CLP$', 'R$', '€']

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
# EXPRESIONES REGULARES A UTILIZAR
# ==============================================================================

DIVIDIR_TXT = r"##"
# 0 o mas espacios 
DIGITOS = r"[0-9]" 
PUNTO_COMA = r"(\.|,)" 

#porcentaje en simbolo o palabra
SIGNO_PORCENTAJE = r"(%|POR CIENTO|PORCIENTO)"

# Al menos un dígito, concatenado con cero o más partes decimales/miles
MONTO = DIGITOS + r"+" + r"(" + PUNTO_COMA + DIGITOS + r"+)*"

###
#prueba
#ordeno el diccionario por longitud para que se analizen las frases mas largas primero
# re.scape saltea caracteres especiales como $ o algo asi. por que si no se rompre la ER
#me parece que esta justo no se usaba igual


patrones_monedas = [re.escape(m) for m in sorted(MAPEO_MONEDAS.keys(), key=len, reverse=True)]
MONEDA = r"(" + "|".join(patrones_monedas) + r")"

#MONEDA = r"(USD|U\$S|U\$|US\$|DÓLARES|DOLARES|ARS|\$|PESOS ARGENTINOS|PESOS URUGUAYOS|PESOS CHILENOS|PESOS|UYU|CLP|BRL|R\$|REALES|EUR|EUROS)"

###
#mas de lo mismo
patrones_monedas_iso = [re.escape(m) for m in sorted(MONEDAS_ISO.keys(), key=len, reverse=True)]
ISO_4217 = r"(" + "|".join(patrones_monedas_iso) + r")"

#ISO_4217 = r"(USD|ARS|UYU|CLP|BRL|EUR)" #se sobreescribe el diccionario? tienen mismo nombre

###
patrones_simbolos = [re.escape(s) for s in sorted(LISTA_SIMBOLOS, key=len, reverse=True)]
SIMBOLO = r"(" + "|".join(patrones_simbolos) + r")"

#SIMBOLO = r"(\$|U\$S|U\$|US\$|R\$)"


###
patrones_coloquial = [re.escape(c) for c in sorted(LISTA_COLOQUIAL, key=len, reverse=True)]
COLOQUIAL = r"(" + "|".join(patrones_coloquial) + r")"
#COLOQUIAL = r"(DÓLARES|DOLARES|PESOS ARGENTINOS|PESOS URUGUAYOS|PESOS CHILENOS|PESOS|REALES|EUROS|pesos|dólares|reales|euros|pesos argentinos|pesos uruguayos|pesos chilenos|dolares|reales)"

####
patrones_mult = [re.escape(m) for m in sorted(MULTIPLICADORES.keys(), key=len, reverse=True)]
MULTIPLICADOR = r"\b(" + "|".join(patrones_mult) + r")\b"
#MULTIPLICADOR = r"(MILLONES|MILLÓN|MILLON|MIL|M)"




ESPACIOS = r"( |\n|\t)*"
CONECTOR = r"(DE" + ESPACIOS + r"|)"

NUMERO_PORCENTAJE = DIGITOS + r"+(" + PUNTO_COMA + DIGITOS + r"+)?"
ER_PORCENTAJE = r"(" + NUMERO_PORCENTAJE + ESPACIOS + SIGNO_PORCENTAJE + r")"




# ==============================================================================
# ESTRUCTURAS REGULARES A UTILIZAR
# ==============================================================================

# Estructura ISO + MONTO "USD 1000"
ESTRUCTURA_ISO = r"(" + ISO_4217 + ESPACIOS + MONTO + r")"
ESTRUCTURA_ISO_2 = r"(" + MONTO + ESPACIOS + ISO_4217 + r")"

# ISO + MONTO + MULTIPLICADOR "USD 1000 MILLONES"
ISO_MULTIPLICADOR = r"(" + ISO_4217 + ESPACIOS + MONTO + ESPACIOS + MULTIPLICADOR + r")"

# Estructura SIMBOLO + MONTO "$ 1000"
ESTRUCTURA_SIMBOLO = r"(" + SIMBOLO + ESPACIOS + MONTO + r")"
ESTRUCTURA_SIMBOLO_2 = r"(" + MONTO + ESPACIOS + SIMBOLO + r")"

# Estructura SIMBOLO + MONTO + MULTIPLICADOR "$ 1000 MILLONES"
SIMBOLO_MULTIPLICADOR = r"(" + SIMBOLO + ESPACIOS + MONTO + ESPACIOS + MULTIPLICADOR + r")"

#Estructura MONTO + FORMA COLOQUIAL:  "1000 DOLARES" "50 MILLONES DE PESOS"
ESTRUCTURA_COLOQUIAL = r"(" + MONTO + ESPACIOS +  MULTIPLICADOR + ESPACIOS + CONECTOR + ESPACIOS + COLOQUIAL + r")"
ESTRUCTURA_COLOQUIAL_SIMPLE = r"(" + MONTO + ESPACIOS + COLOQUIAL + r")"

ESTRUCTURAS_DINERO = (
    r"(" +
    ISO_MULTIPLICADOR + r"|" +
    SIMBOLO_MULTIPLICADOR + r"|" +
    ESTRUCTURA_COLOQUIAL + r"|" +
    ESTRUCTURA_ISO + r"|" +
    ESTRUCTURA_ISO_2 + r"|" +
    ESTRUCTURA_SIMBOLO + r"|" +
    ESTRUCTURA_SIMBOLO_2 + r"|" +
    ESTRUCTURA_COLOQUIAL_SIMPLE +
    r")"
)




# si existe una cotizacion manual ingresada por parametro utiliza esa
# si no intenta conectarse a la api
# si la api no funciona uso el archivo local
def obtener_cotizacion(moneda):
    
    # consultar a la api
    url = "https://dolarapi.com/v1/cotizaciones"
    try:
        respuesta = requests.get(url, timeout=3)
        if respuesta.status_code == 200:
            datos = respuesta.json()
            # Iterar sobre la lista que devuelve la API para buscar la moneda
            for c in datos:
                if c.get("moneda") == moneda:
                    return float(c.get("venta", c.get("compra", 1200)))
    except Exception:
        pass  # si falla, se usa el archivo local

    # utilizacion del archivo local
    ruta_cotizaciones = BASE_DIR / "cotizaciones.json"
    if ruta_cotizaciones.exists():
        with open(ruta_cotizaciones, 'r', encoding='utf-8') as f:
            lista_cotizaciones = json.load(f)
            for c in lista_cotizaciones:
                if c.get("moneda") == moneda:
                    return float(c.get("venta", 1200))

    return None


def leer_archivo(ruta):
    with open(ruta, 'r', encoding='utf-8') as f:
        content = f.read().upper()
    return content


def extraer_texto(ruta= None):
    if ruta is None:
        ruta = BASE_DIR / "data.txt"
    bloques_validos = []
    content = leer_archivo(ruta)
    bloques = re.split(DIVIDIR_TXT, content)

    for b in bloques:
        bloque_limpio = b.strip()
        if bloque_limpio:
            bloques_validos.append(bloque_limpio)
            #print(bloque_limpio)
            #input("")

    return bloques_validos



def buscar_montos_en_bloques(bloques_validos):
    resultados = []
    
    for bloque in bloques_validos:
        montos_del_bloque = []
        
        # re.finditer busca directamente el patrón en el bloque
        for match in re.finditer(ESTRUCTURAS_DINERO, bloque, re.IGNORECASE):
            texto_capturado = match.group(0).strip()
            montos_del_bloque.append(texto_capturado)
            
        resultados.append(montos_del_bloque)
    return resultados

def reconocer_moneda(texto):
    texto_upper = texto.upper()
    
    patrones_ordenados = sorted(MAPEO_MONEDAS.keys(), key=len, reverse=True)
    
    for patron in patrones_ordenados:
        if patron in texto_upper:
            return MAPEO_MONEDAS[patron]
            
    return "DESCONOCIDA" 


def resolver_ambiguedad(texto):
    monto_str = re.sub(r"[^\d.,]", "", texto)

    # 1. Caso donde coexisten punto y coma (ej: "1.234,56" o "1,234.56")
    if '.' in monto_str and ',' in monto_str:
        # El separador que esté más a la derecha (mayor índice) es el decimal
        if monto_str.rfind('.') > monto_str.rfind(','):
            # Formato anglosajón: "1,234.56". Borramos la coma.
            return float(monto_str.replace(',', ''))
        else:
            # Formato latino: "1.234,56". Borramos el punto y cambiamos coma por punto.
            return float(monto_str.replace('.', '').replace(',', '.'))
    
    # 2. Caso donde solo hay punto (ej: "1.500" o "1.5")
    elif '.' in monto_str:
        partes = monto_str.split('.')
        # Si la parte después del último punto tiene exactamente 3 dígitos, es separador de miles
        if len(partes[-1]) == 3:
            return float(monto_str.replace('.', ''))
        else:
            # De lo contrario, actúa como decimal
            return float(monto_str)
            
    # 3. Caso donde solo hay coma (ej: "1,5" o "1,500")
    elif ',' in monto_str:
        partes = monto_str.split(',')
        # Aplicamos la misma regla de los 3 dígitos por si viene en formato anglosajón ("1,500")
        if len(partes[-1]) == 3:
            return float(monto_str.replace(',', ''))
        else:
            # La mayoría de las veces en español será decimal ("1,5")
            return float(monto_str.replace(',', '.'))
            
    # 4. Número entero sin separadores (ej: "1500")
    return float(monto_str)

def analizar_modificador(texto_bloque, monto_base):

    #buscar porcentajes en el texto
    match_porc = re.search(ER_PORCENTAJE, texto_bloque, re.IGNORECASE)
    if not match_porc:
        return None  #no hay nada

    texto_porc = match_porc.group(0)
    # extraer el porcentaje numerico, reuso el resolver ambiguedad. creo que funca
    porcentaje = resolver_ambiguedad(texto_porc)

    texto_upper = texto_bloque.upper()

    #palabras. capaz conviene pasarlas arriba
    palabras_descuento = ["DESCUENTO", "REBAJA", "OFF", "MENOS", "DISMINUCIÓN", "DISMINUCION"]
    palabras_aumento = ["AUMENTO", "INCREMENTO", "SUBA", "MÁS", "MAS", "RECARGO", "AVANCE"]

    es_descuento = any(palabra in texto_upper for palabra in palabras_descuento)
    es_aumento = any(palabra in texto_upper for palabra in palabras_aumento)

    if es_descuento:
        monto_final = monto_base * (1 - (porcentaje / 100))
        return {
            "tipo": "descuento",
            "porcentaje": porcentaje,
            "monto_final": round(monto_final, 2)
        }
    elif es_aumento:
        monto_final = monto_base * (1 + (porcentaje / 100))
        return {
            "tipo": "aumento",
            "porcentaje": porcentaje,
            "monto_final": round(monto_final, 2)
        }

    #si hay un porcentaje pero no se especifica descuento o aumento lo mostramos igual
    return {
        "tipo": "porcentaje_referencial",
        "porcentaje": porcentaje,
        "monto_final": monto_base
    }

def resolver_monto(texto):
    print("que recibe resolver texto", texto)
    factor = 1
    m = re.search(MULTIPLICADOR, texto, re.IGNORECASE)
    if m:
        factor = MULTIPLICADORES[m.group(1).upper()]
        texto = texto.replace(m.group(0), "", 1)
    return resolver_ambiguedad(texto) * factor


def procesar_monto_completo(texto_monto, texto_bloque, moneda_destino=None, cotizacion=None):
    monto_num = resolver_monto(texto_monto)
    moneda = reconocer_moneda(texto_monto)
    
    #calcular descuento
    modificador = analizar_modificador(texto_bloque, monto_num)
    
    #monto a convertir despues de descuento o aumento
    monto_a_convertir = modificador["monto_final"] if modificador else monto_num
    
    #realizar conversion si se especifico
    conversion = None
    if moneda_destino:
        conversion = convertir_moneda(monto_a_convertir, moneda, moneda_destino, cotizacion)
    return {
        "texto_original": texto_monto,
        "monto_original": monto_num,
        "moneda_original": moneda,
        "modificador": modificador,
        "conversion": conversion
    }


def convertir_moneda(monto, moneda_origen, moneda_destino, cotizacion_manual=None):
    # SI NO SE PIDIO QUE SE CONVIERTA O LAS MONEDAS SON IGUALES, NO HAGO NADA
    if not moneda_destino or moneda_origen == moneda_destino:
        return None

    
    # 1. PESO A PESO ES 1
    if moneda_origen == "ARS":
        tasa_origen = 1.0
    elif cotizacion_manual and moneda_destino == "ARS":
        # SI QUIERE PASAR A PESOS ARGENTINOS Y PASO LA COTIZACION SE USA ESA
        tasa_origen = cotizacion_manual
    else:
        tasa_origen = obtener_cotizacion(moneda_origen) #SINO SE OBTIENE YA SEA DE LA API O LO QUE SEA


    #OBTERNER LA TAZA DE LA MONEDA DESTINO
    if moneda_destino == "ARS":
        tasa_destino = 1.0
    elif cotizacion_manual and moneda_destino != "ARS":
        tasa_destino = cotizacion_manual
    else:
        tasa_destino = obtener_cotizacion(moneda_destino)
    if not tasa_origen or not tasa_destino:
        return {"error": f"No se pudo cotizar {moneda_origen} a {moneda_destino}"}
    monto_en_pesos = monto * tasa_origen
    monto_final = monto_en_pesos / tasa_destino
    return {
        "moneda_destino": moneda_destino,
        "monto_convertido": round(monto_final, 2)
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procesar archivo de texto.")
    
    # Agregamos el parámetro "default" para que use la ruta hardcodeada si no le pasas nada
    parser.add_argument(
        "--ruta", 
        type=str, 
        default= BASE_DIR / "data.txt",
        help="Ruta del archivo de texto a procesar (opcional)."
    )
    parser.add_argument("--a", type=str, choices=list(MONEDAS_ISO.keys()), help="Moneda a convertir")
    parser.add_argument("--cotizacion", type=float, help="Cotización manual")
    
    args = parser.parse_args()

    bloques = extraer_texto(args.ruta)
    montos = []
    for bloque in bloques:
        montos_bloque = []
        for monto in re.finditer(ESTRUCTURAS_DINERO, bloque, re.IGNORECASE):
            print(monto)
            monto_str = monto.group(0).strip()
            print(f"Procesando monto: {monto_str}")
            monto_resuelto = procesar_monto_completo(monto_str, bloque, moneda_destino=args.a, cotizacion=args.cotizacion)
            montos_bloque.append(monto_resuelto)
        montos.append(montos_bloque)

    print(json.dumps(montos, indent=4, ensure_ascii=False))