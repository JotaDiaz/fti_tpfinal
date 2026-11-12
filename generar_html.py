"""
generar_html.py
Módulo independiente encargado del renderizado visual de la Gaceta.
"""

def crear_html(noticias_procesadas, ruta_salida, moneda_destino=None):
    """
    Toma la lista de noticias procesadas y escribe el archivo HTML con estilo de periódico antiguo.
    """
    articulos_html = ""

    for n in noticias_procesadas:
        texto = n.get("noticia_convertida") or n["noticia_normalizada"]

        if "Precio Final:" in texto:
            partes = texto.split("Precio Final:")
            cuerpo = partes[0]
            precio_final = f"<div class='caja-precio-final'><strong>PRECIO FINAL:</strong> {partes[1].strip()}</div>"
        else:
            cuerpo = texto
            precio_final = ""

        articulos_html += f"""
        <article class="noticia">
            <h3>{n['titulo']}</h3>
            <p>{cuerpo}</p>
            {precio_final}
        </article>
        """

    leyenda_moneda = f"Edición convertida a {moneda_destino}" if moneda_destino else "Valores de plaza y cotizaciones corrientes"

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <title>La Gaceta Mercantil — FTI</title>
    <style>
        .texture-paper{{
            position: absolute;
            top: 0;
            bottom: 0;
            left: 0;
            right: 0;
            mix-blend-mode: multiply;
            opacity:0.7;
            background-repeat: repeat;
            pointer-events: none;
            background-image: url("texture-paper.jpg");
            z-index:100;
        
        }}
        body {{
            background-color: #f1e2d5;
            color: #1c1309;
            font-family: "Georgia", "Garamond", "Times New Roman", serif;
            line-height: 1.6;
            margin: 0;
            padding: 30px;
            
        }}
        .contenedor {{
            position: relative;
            overflow: hidden;
            max-width: 900px;
            margin: 0 auto;
            background-color: #ebd4b5;
            padding: 40px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
            border: 1px solid #dcd1b4;
        }}
        header {{
            text-align: center;
            border-top: 4px double #2b1d0e;
            border-bottom: 4px double #2b1d0e;
            padding: 15px 0;
            margin-bottom: 25px;
        }}
        h1 {{
            font-size: 38px;
            text-transform: uppercase;
            letter-spacing: 4px;
            margin: 0;
            font-weight: 900;
        }}
        .subtitulo {{
            font-style: italic;
            font-size: 13px;
            margin-top: 8px;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}
        .columnas {{
            column-count: 2;
            column-gap: 35px;
            column-rule: 1px solid #c8b99c;
        }}
        .noticia {{
            break-inside: avoid;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 1px dashed #bba98b;
        }}
        h3 {{
            font-size: 17px;
            text-transform: uppercase;
            margin: 0 0 8px 0;
            border-bottom: 1px solid #2b1d0e;
            padding-bottom: 3px;
        }}
        p {{
            font-size: 14px;
            text-align: justify;
            margin: 0;
        }}
        .caja-precio-final {{
            margin-top: 10px;
            padding: 4px 8px;
            background-color: #eee1c0;
            border: 1px solid #9c8362;
            font-size: 13px;
            display: inline-block;
        }}
        footer {{
            text-align: center;
            font-size: 12px;
            margin-top: 35px;
            border-top: 1px solid #2b1d0e;
            padding-top: 10px;
            font-style: italic;
        }}
        @media print {{
            body {{ background-color: #fff; padding: 0; }}
            .contenedor {{ box-shadow: none; border: none; padding: 0; max-width: 100%; }}
        }}
    </style>
</head>
<body>
    <div class="contenedor">
        <div class="texture-paper"></div>
        <header>
            <h1>La Gaceta Mercantil</h1>
            <div class="subtitulo">Registro de Precios y Avisos — {leyenda_moneda}</div>
        </header>
        <main class="columnas">
            {articulos_html}
        </main>
        <footer>
            Fundamentos Teóricos de Informática — Trabajo Práctico Integrador
        </footer>
    </div>

</body>
</html>"""

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(html_content)