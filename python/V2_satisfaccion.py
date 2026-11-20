# ==============================================================================
# V2 · ¿Hay diferencias significativas en la satisfacción por región o categoría?
#      (Pregunta 2)
# Visual de Python en Power BI
#
# Campos a arrastrar al visual (Delivery Days en "No resumir"):
#   Row ID, Order ID, Region, Category, Delivery Days
#
# Librerías: pandas, numpy, matplotlib, seaborn, scipy.stats
#
# SUPUESTO CLAVE: el dataset NO trae una columna de satisfacción. Se usa como
# proxy el tiempo de entrega (Delivery Days = Ship Date - Order Date): a menos
# días, mayor satisfacción esperada. Está documentado en la guía.
#
# Decisiones estadísticas:
#  - Unidad de análisis = PEDIDO (no línea): los días de entrega son del pedido,
#    y varias líneas comparten pedido. Analizar líneas infla la muestra
#    (pseudo-replicación) y puede dar falsos "significativos".
#  - Prueba principal: Kruskal-Wallis (Diseño Experimental, Tema 8.1). Se eligió
#    porque el supuesto de normalidad de los errores del ANOVA no se cumple
#    (Shapiro-Wilk p < 0.001; los días son enteros de 0 a 8).
#  - Se muestra también el ANOVA de una vía (Tema 2.2) como confirmación: ambas
#    pruebas llegan a la misma conclusión.
#  - Se reporta el tamaño del efecto ε² porque un p-valor solo dice si hay
#    diferencia, no si importa.
#  - Si p < 0.05 se agregan comparaciones por pares con U de Mann-Whitney
#    (Tema 8.3), ajustadas por comparaciones múltiples (Holm).
# ==============================================================================
import itertools

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

AZUL, NARANJA, GRIS, OSCURO = "#1F6F8B", "#E07A5F", "#8D99AE", "#2B2D42"
ALFA = 0.05

df = dataset.copy()


def pruebas(datos, col):
    """Kruskal-Wallis + ε² (+ Mann-Whitney/Holm si es significativo)."""
    grupos = [g["Delivery Days"].to_numpy() for _, g in datos.groupby(col)]
    H, p = stats.kruskal(*grupos)
    F, p_anova = stats.f_oneway(*grupos)              # confirmación con ANOVA de una vía
    n, k = len(datos), len(grupos)
    eps2 = max(0.0, (H - k + 1) / (n - k))
    pares = []
    if p < ALFA:
        niveles = sorted(datos[col].unique())
        crudos = []
        for a, b in itertools.combinations(niveles, 2):
            pv = stats.mannwhitneyu(datos.loc[datos[col] == a, "Delivery Days"],
                                    datos.loc[datos[col] == b, "Delivery Days"]).pvalue
            crudos.append((a, b, pv))
        crudos.sort(key=lambda t: t[2])
        m = len(crudos)
        ajust, previo = [], 0.0
        for i, (a, b, pv) in enumerate(crudos):           # corrección de Holm
            previo = max(previo, min(1.0, pv * (m - i)))
            ajust.append((a, b, previo))
        pares = [(a, b, pv) for a, b, pv in ajust if pv < ALFA]
    return H, p, eps2, n, pares, F, p_anova


def panel(ax, datos, col, titulo, orden=None):
    H, p, eps2, n, pares, F, p_anova = pruebas(datos, col)
    orden = orden or sorted(datos[col].unique())
    sns.violinplot(data=datos, x=col, y="Delivery Days", order=orden, hue=col,
                   hue_order=orden, palette=[AZUL] * len(orden), cut=0, inner=None,
                   linewidth=0.8, saturation=1, legend=False, ax=ax)
    for poly in ax.collections:
        poly.set_alpha(0.28)
    # media e IC 95% (t de Student) sobre la media de días
    for i, nivel in enumerate(orden):
        v = datos.loc[datos[col] == nivel, "Delivery Days"]
        media = v.mean()
        ic = stats.t.ppf(0.975, len(v) - 1) * v.std(ddof=1) / np.sqrt(len(v))
        ax.errorbar(i, media, yerr=ic, fmt="o", color=NARANJA, ecolor=NARANJA,
                    elinewidth=2.4, capsize=5, markersize=8, zorder=5)
        ax.text(i + 0.12, media, f"{media:.2f}", color=NARANJA, fontsize=10,
                fontweight="bold", va="center")
    ax.set_title(titulo, loc="left", fontsize=13, fontweight="bold", color=OSCURO)
    ax.set_xlabel("")
    ax.set_ylabel("Días de entrega por pedido")
    ax.set_ylim(-0.5, 11.8)          # espacio arriba para el texto de la prueba
    ax.set_yticks(range(0, 9))
    ax.spines[["top", "right"]].set_visible(False)

    veredicto = "Diferencia significativa" if p < ALFA else "Sin diferencias significativas"
    color = NARANJA if p < ALFA else AZUL
    ax.text(0.01, 0.97, veredicto, transform=ax.transAxes, fontsize=11.5,
            fontweight="bold", color=color, va="top")
    ax.text(0.01, 0.90,
            f"Kruskal-Wallis: H = {H:.2f}, p = {p:.3f}  ·  Tamaño del efecto ε² = {eps2:.4f}\n"
            f"ANOVA (confirmación): F = {F:.2f}, p = {p_anova:.3f}  ·  n = {n:,} pedidos",
            transform=ax.transAxes, fontsize=9, color="#444444", va="top")
    if pares:
        ax.text(0.01, 0.79, "Pares distintos (Holm): " +
                "; ".join(f"{a}–{b} (p={pv:.3f})" for a, b, pv in pares),
                transform=ax.transAxes, fontsize=8.5, color="#444444", va="top")


def comparable(datos, col):
    """Hay con qué comparar: al menos 2 grupos, con 2+ pedidos cada uno y 30+ en total."""
    tam = datos[col].value_counts()
    return len(datos) >= 30 and len(tam) >= 2 and tam.min() >= 2


def sin_comparacion(ax, texto):
    ax.axis("off")
    ax.text(0.5, 0.5, texto, ha="center", va="center", fontsize=12, color=OSCURO)


sns.set_style("whitegrid")
# Región: 1 fila por pedido. Categoría: 1 fila por pedido y categoría.
por_pedido = df.drop_duplicates(["Order ID"])
por_pedido_cat = df.drop_duplicates(["Order ID", "Category"])
ok_reg = comparable(por_pedido, "Region")
ok_cat = comparable(por_pedido_cat, "Category")

# Proporción 2:1 (cuadro de ~740 x 370 px): Power BI escala la imagen manteniéndola.
# La explicación del proxy (menos días = mejor servicio) va en un cuadro de texto del dashboard.
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5.5), sharey=ok_reg and ok_cat)
if ok_reg:
    panel(ax1, por_pedido, "Region", "Por región")
else:
    sin_comparacion(ax1, "Por región\n\nCon una sola región seleccionada\nno hay con qué comparar")
if ok_cat:
    panel(ax2, por_pedido_cat, "Category", "Por categoría")
    ax2.set_ylabel("" if ok_reg else "Días de entrega por pedido")
else:
    sin_comparacion(ax2, "Por categoría\n\nCon una sola categoría seleccionada\nno hay con qué comparar")
plt.tight_layout()
plt.show()
