# TP Integrador FTI — Tema 10: Precios y montos de dinero

Programa en Python que lee un archivo de texto con noticias o avisos, extrae los montos con expresiones regulares, reconoce la moneda, normaliza los valores y permite convertirlos a otra moneda.

## Requisitos

- Python 3.8 o superior.
- La biblioteca `requests` para consultar la API de cotizaciones:

```bash
pip install requests
```

## Entrada

Archivo de texto plano en UTF-8. Cada noticia o aviso es un bloque que empieza con una línea que comienza con `##`.

```text
## Sube el precio de la nafta
El litro pasó de $ 1.150 a $1.234,56 en Trelew, un aumento del 7,4%.

## Vendo auto
Fiat Uno 2010, u$s 4.500 o $ 5,4 millones. Acepto permuta.
```

## Ejecución

```bash
# Procesa un archivo
python3 main.py noticias.txt

# Si no se indica archivo, usa data.txt
python3 main.py

# Convierte los montos a dólares
python3 main.py noticias.txt --a USD

# Convierte a pesos argentinos con una cotización manual
python3 main.py noticias.txt --a ARS --cotizacion 1200

# Muestra el texto normalizado en lugar del JSON
python3 main.py noticias.txt --solo-texto

# Indica la ruta del archivo con una opción
python3 main.py --ruta noticias.txt
```

## Parámetros

- `archivo`: archivo de entrada. Si se omite, se usa `data.txt`.
- `--ruta RUTA`: ruta alternativa al archivo de entrada.
- `--a MONEDA`: moneda a la que se convierten los montos (`USD`, `ARS`, `UYU`, `CLP`, `BRL` o `EUR`).
- `--cotizacion NUMERO`: cotización manual de la moneda extranjera frente al peso argentino. Por ejemplo, `1200` significa `1 USD = 1200 ARS`.
- `--solo-texto`: muestra solo el texto normalizado, sin el JSON completo.
- `-h`, `--help`: muestra la ayuda del programa.

## Salida

Por defecto se imprime un JSON con el título, el texto original, el texto normalizado, los montos detectados y las advertencias. Si se usa `--a`, se agrega el monto convertido y la moneda de destino.

Los textos de `noticia_original`, `noticia_normalizada` y `noticia_convertida` se emiten en una sola línea: los saltos de línea del bloque de entrada se colapsan a un espacio.

Ejemplo de salida (fragmento):

```json
{
    "titulo": "Vendo auto",
    "noticia_normalizada": "Vendo auto Fiat Uno 2010, USD 4.500 o $5.400.000. Acepto permuta.",
    "montos_detalle": [
        {
            "texto_original": "u$s 4.500",
            "monto_original": 4500.0,
            "moneda_original": "USD"
        },
        {
            "texto_original": "$ 5,4 millones",
            "monto_original": 5400000.0,
            "moneda_original": "ARS"
        }
    ],
    "advertencias": []
}
```

Con `--solo-texto` se muestra el texto normalizado de cada bloque. Las advertencias por montos inválidos o conversiones fallidas aparecen debajo de cada bloque.

El programa también genera `gaceta.html` en la carpeta del script.
