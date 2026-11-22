# Fuentes de rutas — investigación y estado de conectores

Documento de referencia. **No inventamos APIs** ni asumimos que una web pública autoriza la copia masiva.

## España

### 1. Red General de Vías Pecuarias (RGVP) — MITECO

| Campo | Valor |
|---|---|
| URL | https://www.miteco.gob.es/es/cartografia-y-sig/ide/descargas/biodiversidad/vias_pecuarias.html |
| Cobertura | Nacional (vías clasificadas; homogeneización CCAA). **No** es un inventario de senderos ciclistas. |
| Formato | Shapefile (~34,5 MB); también GeoJSON/KMZ en catálogo IEPNB |
| Actualización citada | 31/12/2024 |
| Licencia / reutilización | Uso libre y gratuito citando: «Fuente: © Ministerio para la Transición Ecológica y el Reto Demográfico». Condiciones generales de reutilización del sector público (no desnaturalizar, citar fuente y fecha, no sugerir patrocinio). |
| Conector | **Activo en la app**: muestra de ~180 tramos (cañadas, cordeles, veredas, coladas) en `assets/routes/vias_pecuarias_rgvp.geojson`, extraída del GeoJSON oficial RGVP 2024 (WGS84). Script: `scripts/extract_rgvp_sample.py`. No es la cobertura completa (~52k tramos). |
| Notas | Distinguir trazado publicado, permiso de circulación y estado físico. No inferir aptitud ciclista. |

### 2. Red de Caminos Naturales — MAPA

| Campo | Valor |
|---|---|
| URL | https://www.mapa.gob.es/es/cartografia-y-sig/ide/descargas/desarrollo-rural/red-caminos-naturales |
| Cobertura | Red de Caminos Naturales (no todo el territorio senderista) |
| Formato | A verificar en la página de descargas IDE |
| Licencia | A verificar antes de importación masiva |
| Conector | `mapa_caminos_naturales` — **pendiente** |

### 3. Vías Verdes — Fundación de los Ferrocarriles Españoles

| Campo | Valor |
|---|---|
| URL | https://viasverdes.com/itinerarios/ |
| Cobertura | Itinerarios de Vías Verdes publicados por la FFE |
| Formato | Web de itinerarios; **sin API abierta verificada** |
| Licencia | No asumir permiso de scraping/copia |
| Conector | `vias_verdes_ffe` — **pendiente** (hace falta permiso o datos abiertos autorizados) |

### 4. CNIG y cartografía autonómica/municipal

Complementar cuando proceda, citando licencia de cada conjunto. Un dataset municipal **no** se presenta como cobertura nacional.

---

## Portugal

### 5. Ecopistas — IP Património

| Campo | Valor |
|---|---|
| URL | https://ippatrimonio.pt/ecopistas |
| Cobertura | Plano Nacional de Ecopistas (promoción institucional) |
| Formato verificado | Página informativa; **sin GeoJSON/SHP abierto verificado** en la consulta realizada |
| Licencia | Sin condiciones de descarga abierta documentadas aquí |
| Conector | `ip_ecopistas_demo` — **demo** (muestra ilustrativa marcada `is_demo=true`) |
| Necesita | Permiso escrito o conjunto en dados.gov.pt / open data con geometrías |

### 6. Cyclin’Portugal

| Campo | Valor |
|---|---|
| URL | https://www.cyclinportugal.pt/pt/infraestruturas/redes-de-percursos |
| Conector | `cyclin_portugal` — **pendiente** |

### 7. FCMP (senderos homologados)

| Campo | Valor |
|---|---|
| Conector | `fcmp_senderos` — **pendiente** (investigar licencia y disponibilidad) |

### 8. dados.gov.pt y datos municipales

Investigar conjuntos concretos con geometría y licencia clara. No generalizar un municipio a todo el país.

---

## Carga en la app (sin depender del backend)

La app móvil prioriza:

1. **Catálogo ciclovías** en `assets/routes/ciclovias_catalogo.json` — vías verdes, ecopistas y rutas bici de referencia por CCAA / Portugal (geometrías esquemáticas; script `scripts/build_ciclovias_catalogo.py`). No sustituyen tracks oficiales.
2. **GeoJSON embebido** en `assets/routes/fuentes_locales.json` (muestras con atribución).
3. **Pack OSM** `osm_iberia.json` (+ refuerzo opcional `fetch_osm_bike_ccaa.py`).
4. **OpenStreetMap vía Overpass** al acercar el mapa (relaciones `route=hiking|foot|bicycle|mtb`). Licencia ODbL. No son necesariamente datos oficiales.

El backend sigue disponible para cuenta/favoritos/comentarios; el mapa no necesita importar ahí para mostrar estas capas.

---

## Principios de calidad

1. Conservar fuente, `external_id`, licencia, atribución y fecha.
2. Reimportar sin duplicados (clave `source_id` + `external_id`).
3. No fusionar por similitud de nombre.
4. Campos ausentes → «desconocido» (nunca inventar desnivel, dificultad o permisos).
5. Distinguir en UI: información oficial de fuente vs avisos comunitarios.
6. Antiguos ferrocarriles ≠ ruta transitable automática.
