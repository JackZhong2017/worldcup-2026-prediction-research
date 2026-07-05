# Investigación de Predicción del Mundial 2026

[![GitHub stars](https://img.shields.io/github/stars/JackZhong2017/worldcup-2026-prediction-research?style=flat-square)](https://github.com/JackZhong2017/worldcup-2026-prediction-research/stargazers)
[![License](https://img.shields.io/github/license/JackZhong2017/worldcup-2026-prediction-research?style=flat-square)](./LICENSE)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=flat-square)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat-square)](https://nextjs.org/)
[![NestJS](https://img.shields.io/badge/NestJS-11-E0234E?style=flat-square)](https://nestjs.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square)](https://www.postgresql.org/)

> 🇨🇳 **中文版：[README.md](README.md)** | 🇬🇧 **English: [README.en.md](README.en.md)**

Una plataforma de investigación para medir la calibración y calidad estadística de los mercados de predicción de fútbol, centrada en el Mundial 2026. Cada partido se trata como una observación. La plataforma compara las probabilidades implícitas del mercado de Polymarket con modelos estadísticos construidos a partir de datos xG de StatsBomb, y evalúa si un modelo fusionado puede ser validado científicamente como predictivo.

**Sin recomendaciones de apuestas, sin estrategias de staking, sin dimensionamiento de posiciones.** Es una herramienta de investigación pura — preferiría informar honestamente que un modelo fue rechazado antes que hacer predicciones no científicas.

---

## Inicio Rápido

```bash
git clone https://github.com/JackZhong2017/worldcup-2026-prediction-research.git
cd worldcup-2026-prediction-research
cp .env.example .env
# Edita .env y añade tu token de API de football-data.org
docker compose up -d postgres redis
pnpm install
pnpm db:generate
pnpm dev
```

Verifica que la API esté funcionando:

```bash
curl 'http://localhost:3001/api/v1/providers/polymarket/events?limit=5'
```

---

## Qué Responde

No "quién va a ganar", sino preguntas más fundamentales: **¿Están realmente bien calibrados los mercados de predicción? ¿Pueden los modelos estadísticos proporcionar información incremental?**

**Calidad del Mercado**
- ¿Qué tan precisas son las probabilidades implícitas de marcador exacto de Polymarket?
- ¿Sobreestima o subestima sistemáticamente el mercado ciertos resultados?
- ¿Está razonablemente valorada la cola de "otro marcador"?

**Validación de Modelos Estadísticos**
- ¿Puede un modelo Poisson independiente basado en xG superar al mercado?
- ¿La fusión por pool de opinión logarítmica supera a cualquiera de las fuentes por sí sola?
- Evaluación rigurosamente fuera de muestra con divisiones cronológicas — sin sesgo de anticipación

**Investigación Reproducible**
- Cada experimento registra su instantánea de datos, versión de código, parámetros y semilla aleatoria
- 88 distribuciones CLOB reconstruidas antes del inicio para partidos del Mundial 2026
- Todos los artefactos intermedios (instantáneas, informes, evaluaciones) son completamente auditables

---

## Fuentes de Datos

| Fuente | Qué Proporciona |
|---|---|
| **Polymarket** | Instantáneas de probabilidad de marcador exacto en tiempo real; historial de precios CLOB por lotes para 88 eventos cerrados del Mundial |
| **StatsBomb Open Data** | xG a nivel de evento de 262 partidos internacionales, convertidos en indicadores de fuerza ofensiva/defensiva |
| **football-data.org** | Calendario de partidos, estado en vivo, resultados finales — usado para emparejamiento entre proveedores y liquidación post-partido |

---

## Cómo Funciona

```
Adaptadores → Objetos de Dominio → Almacenamiento Inmutable (PostgreSQL) → Métricas de API → Experimentos Estadísticos (Python) → Consumo de Informes
                                                    ↑                              ↑
                                          Instantáneas Polymarket            Datos xG de StatsBomb
```

### Tres Módulos Principales

| Módulo | Stack | Responsabilidad |
|---|---|---|
| **API** (`apps/api`) | NestJS 11 | Recolección de datos, normalización, fusión de predicciones, cálculo de métricas |
| **Dashboard** (`apps/web`) | Next.js 15 | Panel de investigación: explorador de partidos, curvas de calibración, calidad del mercado |
| **Worker** (`apps/worker`) | Python 3.11 | Cálculo estadístico: backtesting, optimización de parámetros, experimentos de fusión, reconstrucción CLOB |

---

## Base Científica

### Fusión por Pool de Opinión Logarítmica

Las distribuciones de mercado y estadística se combinan mediante una **media geométrica ponderada** (pool de opinión logarítmica). Se elige la media geométrica sobre la aritmética porque evita que una fuente domine únicamente por escala numérica. El peso de fusión se congela antes de cualquier evaluación fuera de muestra para prevenir el sobreajuste.

### Distribución de Poisson de Marcadores

El modelo estadístico construye **tasas de Poisson independientes** a partir de xG ofensivo, xG defensivo recibido, promedios de liga y ventaja local antes del inicio. Estas generan una cuadrícula completa de 0–10 goles. La cola de "otro marcador" de Polymarket se expande proporcionalmente según el modelo estadístico en las celdas no listadas.

### Puerta de Validación del Modelo

La API tiene dos estados de salida. El predeterminado es **`RESEARCH_OUTPUT_NOT_VALIDATED`**. La salida se actualiza a **`MODEL_PREDICTION`** solo cuando se superan los cinco umbrales en una cohorte congelada fuera de muestra:

| Umbral | Criterio |
|---|---|
| **① Tamaño de Muestra** | ≥ 200 partidos completados fuera de muestra |
| **② Brier Score** | ≤ 0.85 (límite superior del bootstrap al 95%, 2000 remuestreos) |
| **③ Pérdida Logarítmica** | ≤ 3.20 (límite superior del bootstrap al 95%) |
| **④ Error de Calibración** | ≤ 0.05 (ECE de etiqueta superior — solo el marcador exacto más probable por partido) |
| **⑤ Pérdida Logarítmica Incremental** | ≤ -0.01 (modelo fusionado vs. solo mercado, bootstrap emparejado al 95%) |

Todos los umbrales usan **límites superiores de confianza bootstrap al 95%**, no estimaciones puntuales — esto evita que el ruido estadístico produzca falsos positivos. Las ventanas de entrenamiento/validación/prueba son estrictamente cronológicas y nunca se superponen. La ventana de prueba final se evalúa exactamente una vez. La API nunca confía en un backtest incluido en una solicitud de predicción — requiere un informe de evaluación almacenado en el servidor con `isOutOfSample=true` y `admitted=true`.

### Error de Calibración Esperado de Etiqueta Superior

Aplanar las 121 celdas de marcador (0–10 × 0–10) en una muestra de calibración haría que el error pareciera artificialmente pequeño debido a las numerosas clases negativas cercanas a cero. Este proyecto usa solo el **marcador exacto más probable por partido** para la evaluación de calibración.

---

## Estructura del Repositorio

```
├── apps/
│   ├── api/         # API backend NestJS (puerto 3001)
│   ├── web/         # Panel de investigación Next.js
│   └── worker/      # Worker estadístico Python (11 comandos CLI)
├── packages/
│   ├── domain/      # Tipos de dominio independientes del proveedor
│   └── database/    # Esquema ORM Prisma y migraciones
├── data/
│   ├── processed/   # Datos xG internacionales de StatsBomb (262 partidos)
│   ├── snapshots/   # Instantáneas del mercado Polymarket
│   ├── reports/     # Informes de marcadores fusionados y líneas base estadísticas
│   ├── backfill/    # 88 reconstrucciones históricas CLOB del Mundial 2026
│   ├── manifests/   # Manifiestos de muestras activas
│   └── evaluations/ # Observaciones liquidadas
├── docs/            # Documentación de arquitectura, hoja de ruta y validación
├── docker-compose.yml
└── pnpm-workspace.yaml
```

---

## Instalación

### Requisitos Previos

- Node.js 22+, pnpm 10+
- Python 3.11+
- Docker (PostgreSQL 16 + Redis 7)

### Configuración Completa

```bash
# 1. Clonar el repositorio
git clone https://github.com/JackZhong2017/worldcup-2026-prediction-research.git
cd worldcup-2026-prediction-research

# 2. Configurar entorno
cp .env.example .env
# Editar .env y establecer FOOTBALL_DATA_API_TOKEN (registro gratuito en football-data.org)

# 3. Iniciar servicios
docker compose up -d postgres redis

# 4. Instalar dependencias
pnpm install
pnpm db:generate

# 5. Iniciar desarrollo
pnpm dev
```

### Configuración del Worker Python

```bash
cd apps/worker
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

---

## Ejemplos de Uso

### Explorar Datos del Mercado

```bash
# Listar eventos deportivos de Polymarket
curl 'http://localhost:3001/api/v1/providers/polymarket/events?limit=5'

# Consultar partidos de fútbol (requiere token API)
curl 'http://localhost:3001/api/v1/providers/football-data/matches?dateFrom=2026-07-04&dateTo=2026-07-05'

# Obtener libro de órdenes para un mercado específico
curl 'http://localhost:3001/api/v1/providers/polymarket/orderbook/TOKEN_ID'
```

### Emparejamiento de Partidos entre Proveedores

La identidad entre proveedores (partido de football-data ↔ evento de Polymarket) siempre debe ser **revisada manualmente** antes de su persistencia:

```bash
curl -X POST 'http://localhost:3001/api/v1/imports/preview' \
  -H 'content-type: application/json' \
  -d '{"footballDataMatchId": 537376, "polymarketEventId": "650891"}'
```

### Ejecutar Experimentos Estadísticos

```bash
cd apps/worker
source .venv/bin/activate

sprp-collect-statsbomb       # Recolectar datos xG de 262 partidos internacionales
sprp-backtest                # Prueba de línea base estadística cronológica 80/20
sprp-optimize                # Búsqueda en cuadrícula de parámetros 60/20/20
sprp-collect-polymarket 650891  # Instantánea de un evento de marcador exacto
sprp-fuse-current            # Cuadrículas completas de mercado/estadístico/fusionado
sprp-settle 537376           # Evaluación post-partido (idempotente)
sprp-batch                   # Descubrir, emparejar, capturar y fusionar eventos próximos
sprp-settle-batch            # Liquidar todos los elementos finalizados en el manifiesto activo
sprp-backfill                # Reconstruir distribuciones CLOB previas al inicio
sprp-recent-experiment       # Experimento causal de fusión en formato torneo
```

### Ejecutar un Análisis de Predicción

```bash
curl -X POST 'http://localhost:3001/api/v1/analysis/predict' \
  -H 'content-type: application/json' \
  -d '{
    "matchId": "537376",
    "homeAttack": 1.2, "homeDefense": 0.8,
    "awayAttack": 0.9, "awayDefense": 1.1,
    "homeAdvantage": 0.3,
    "marketDistribution": [...]
  }'
```

---

## Resultados Experimentales Actuales

Usando 88 partidos liquidados del Mundial 2026 con distribuciones CLOB reconstruidas antes del inicio:

| Métrica | Solo Mercado | Modelo Estadístico |
|---|---|---|
| **Pérdida Logarítmica** | 2.443 ✅ | 2.665 ❌ |
| **Partidos** | 88 Mundial 2026 | 262 internacionales |
| **Resultado de Validación** | Línea base | Rechazado — 0% de peso estadístico seleccionado |

> **Actualmente no hay ningún modelo admitido.** El modelo estadístico no logró demostrar valor incremental sobre el mercado y permanece como candidato de investigación rechazado. Se necesita una cohorte fuera de muestra más grande (≥ 200 partidos) para la reevaluación.

Ver [docs/model-validation.md](docs/model-validation.md) para más detalles.

---

## Principios de Arquitectura

1. **Solo añadir, inmutable** — Las instantáneas de mercado nunca se modifican; las correcciones de resultados son auditables
2. **Aislamiento de identidad entre proveedores** — El emparejamiento de partidos requiere revisión manual obligatoria
3. **Procedencia de métricas** — Cada métrica registra su instantánea de entrada, versión de implementación, parámetros y marca de tiempo
4. **Divisiones cronológicas** — Sin sesgo de anticipación; las ventanas de entrenamiento/validación/prueba nunca se superponen
5. **Inferencia bootstrap** — El error de calibración y la pérdida usan intervalos de confianza bootstrap, no estimaciones puntuales
6. **Evaluación única** — La ventana final fuera de muestra se evalúa exactamente una vez

Ver [docs/architecture.md](docs/architecture.md).

---

## Hoja de Ruta

- **M0 Fundación** ✅ — Monorepo, servicios locales, contrato de dominio, esquema de base de datos, primitivas de métricas
- **M1 Pipeline de Muestra Única** ✅ — Recolección, instantánea, fusión, liquidación, informes
- **M2 Evaluación Histórica** ✅ — Pipeline por lotes, reconstrucción CLOB, optimización de parámetros
- **M3 Banco de Trabajo de Investigación** 🚧 — Agrupación personalizada, experimentos de regresión/Bayesianos, exportación de gráficos, revisión de patrones

Explícitamente fuera del alcance: cobertura de múltiples proveedores, trading en tiempo real, recomendaciones de apuestas.

Ver [docs/roadmap.md](docs/roadmap.md).

---

## Notas Importantes

- Este proyecto **no proporciona recomendaciones de predicción** — toda la salida se etiqueta como `RESEARCH_OUTPUT_NOT_VALIDATED` hasta que se supere la puerta de validación del modelo
- Los datos abiertos de StatsBomb deben ser atribuidos cuando se publique o comparta investigación basada en ellos
- El nivel gratuito de football-data.org tiene límites de velocidad (10 solicitudes/minuto); las operaciones por lotes incluyen retrasos incorporados
- Todos los datos experimentales son solo para fines de investigación y no constituyen asesoramiento de inversión o trading
- El modelo estadístico **actualmente no está admitido** — ningún peso de fusión puede desplegarse como validado sin pasar una cohorte fuera de muestra posterior preespecificada

---

## Licencia

MIT © 2026 JackZhong2017 — Libre para usar, modificar y distribuir comercialmente con aviso de copyright preservado.
