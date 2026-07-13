# Tarea periódica: procesar transcripciones pendientes

Prompt para la tarea programada de Claude (cron cada 6 h). También puede
lanzarse a mano pegando el prompt en una sesión de Claude Code en este repo.

## Programación

- Frecuencia: cada 6 horas (`17 */6 * * *`)
- Directorio de trabajo: raíz de este repo

## Prompt

Procesa las transcripciones de vídeo pendientes:

1. Lee `config.yaml` para obtener las categorías permitidas y el mapeo
   `markdown.summary_files` / `markdown.default_summary_file`. La carpeta del
   vault se indica al final de este prompt (el script lanzador la inyecta).
   Si ejecutas esto a mano, usa el valor de `VIDEOINBOX_DIR` en `.env`.
2. Lista los ficheros `*.md` de la subcarpeta `Pendientes/`. Si no hay
   ninguno, termina sin hacer nada.
3. Para cada fichero:
   - Lee el frontmatter (`fecha`, `url`, `estado`, `intentos`) y la
     transcripción completa.
   - Extrae los items relevantes (productos, obras, lugares, recetas…) y
     clasifícalos usando ÚNICAMENTE las categorías de `config.yaml`.
   - Para cada item, añade una línea al fichero de resumen que corresponda
     según el mapeo (categorías no mapeadas van a `default_summary_file`),
     bajo la cabecera `## YYYY-MM-DD` con la fecha del frontmatter (créala si
     no existe, respetando el orden y formato del fichero). Formato de línea:
     `- <icono> **<Categoría>**: <nombre> — "<descripción breve>"` seguido de
     `  [enlace al video](<url>)` en la línea siguiente.
   - Actualiza el frontmatter a `estado: procesada` y mueve el fichero a la
     subcarpeta `Procesadas/` (si el nombre colisiona, añade sufijo ` (2)`).
   - Si la transcripción no contiene nada relevante, muévelo igualmente a
     `Procesadas/` con `estado: procesada` sin escribir resúmenes.
4. No modifiques ficheros de resumen salvo para añadir entradas. No borres
   nada. Al terminar, resume cuántos ficheros procesaste y qué items
   extrajiste.
