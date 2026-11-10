import re
import argparse
import json
import sys

ISO_4217 = {
    'USD': 'USD',
    'ARS': 'ARS',
    'UYU': 'UYU',
    'CLP': 'CLP',
    'BRL': 'BRL',
    'EUR': 'EUR'

}

MAPEO_MONEDAS = {
    'USD': 'USD',
    'U$S': 'USD',
    'U$': 'USD',
    'US$': 'USD', 
    'DÓLARES': 'USD', 
    'ARS': 'ARS',
    '$': 'ARS', 
    'PESOS ARGENTINOS': 'ARS', 
    'PESOS': 'ARS',
    'UYU': 'UYU',
    'PESOS URUGUAYOS': 'UYU',
    'CLP': 'CLP', 
    'PESOS CHILENOS': 'CLP',
    'BRL': 'BRL', 
    'R$': 'BRL',
    'REALES': 'BRL',
    'EUR': 'EUR',
    'EUROS': 'EUR'
}

MULTIPLICADORES = {
    'MIL': 1000, 
    'MILLON': 1000000, 
    'MILLÓN': 1000000, 
    'MILLONES': 1000000, 
    'M': 1000000
}


# EXPRESIONES REGULARES A UTILIZAR
DIVIDIR_TXT = r"##"
# 0 o mas espacios 
DIGITOS = r"(0|1|2|3|4|5|6|7|8|9)" 
PUNTO_COMA = r"(\.|,)" 
# Al menos un dígito, concatenado con cero o más partes decimales/miles
MONTO = DIGITOS + r"+" + r"(" + PUNTO_COMA + DIGITOS + r"+)*"

MONEDA = r"(USD|U\$S|U\$|US\$|DÓLARES|DOLARES|ARS|\$|PESOS ARGENTINOS|PESOS URUGUAYOS|PESOS CHILENOS|PESOS|UYU|CLP|BRL|R\$|REALES|EUR|EUROS)"
ISO_4217 = r"(USD|ARS|UYU|CLP|BRL|EUR)"
SIMBOLO = r"(\$|U\$S|U\$|US\$|R\$)"
COLOQUIAL = r"(DÓLARES|DOLARES|PESOS ARGENTINOS|PESOS URUGUAYOS|PESOS CHILENOS|PESOS|REALES|EUROS|pesos|dólares|reales|euros|pesos argentinos|pesos uruguayos|pesos chilenos|dolares|reales)"
MULTIPLICADOR = r"(MILLONES|MILLÓN|MILLON|MIL|M)"


ESPACIOS = r"( |\n|\t)*"
CONECTOR = r"(DE" + ESPACIOS + r"|)"

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
def leer_archivo(ruta):
    with open(ruta, 'r', encoding='utf-8') as f:
        content = f.read().upper()
    return content


def extraer_texto(ruta= None):
    if ruta is None:
        ruta = '/home/joaquin/Documentos/facultad/FTI/tp_final/data.txt'
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


def resolver_monto(texto):
    print("que recibe resolver texto", texto)
    factor = 1
    m = re.search(MULTIPLICADOR, texto, re.IGNORECASE)
    if m:
        factor = MULTIPLICADORES[m.group(1).upper()]
        texto = texto.replace(m.group(0), "", 1)
    return resolver_ambiguedad(texto) * factor

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procesar archivo de texto.")
    
    # Agregamos el parámetro "default" para que use la ruta hardcodeada si no le pasas nada
    parser.add_argument(
        "--ruta", 
        type=str, 
        default="/home/joaquin/Documentos/facultad/FTI/tp_final/data.txt",
        help="Ruta del archivo de texto a procesar (opcional)."
    )
    
    args = parser.parse_args()

    bloques = extraer_texto(args.ruta)
    montos = []
    for bloque in bloques:
        montos_bloque = []
        for monto in re.finditer(ESTRUCTURAS_DINERO, bloque, re.IGNORECASE):
            print(monto)
            monto_str = monto.group(0).strip()
            print(f"Procesando monto: {monto_str}")
            monto_resuelto = resolver_monto(monto_str)
            montos_bloque.append(monto_resuelto)
        montos.append(montos_bloque)

    print(json.dumps(montos, indent=4, ensure_ascii=False))