# ==============================================================================
# V1 · ¿Qué variables presentan mayor correlación con el beneficio?  (Pregunta 1)
# Visual de Python en Power BI
#
# Campos a arrastrar al visual (los numéricos en "No resumir"):
#   Row ID, Sales, Quantity, Unit Price, Delivery Days, Profit,
#   Sub-Category, Category, Region, Segment, Ship Mode
#
# Librerías: pandas, numpy, matplotlib, seaborn
#
# Decisiones:
#  - Se usa Spearman (por rangos) y no Pearson porque Profit tiene valores
#    extremos (de -6 600 a +8 400) que distorsionarían una correlación lineal.
#  - Las variables categóricas no tienen "correlación" en sentido estricto:
#    se mide su asociación con la razón de correlación η (0 a 1), calculada
#    sobre los rangos de Profit para que sea comparable con Spearman.
# ==============================================================================
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

AZUL, NARANJA, GRIS, OSCURO = "#1F6F8B", "#E07A5F", "#8D99AE", "#2B2D42"

df = dataset.copy()

NUMERICAS = {
    "Sales": "Ventas",
    "Quantity": "Cantidad",
    "Unit Price": "Precio unitario",
    "Delivery Days": "Días de entrega",
    "Profit": "Beneficio",
}
CATEGORICAS = {
    "Sub-Category": "Subcategoría",
    "Category": "Categoría",
    "Region": "Región",
    "Segment": "Segmento",
    "Ship Mode": "Modo de envío",
}

if len(df) < 30:
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.axis("off")
    ax.text(0.5, 0.5, "Muy pocos registros con el filtro actual\n(se requieren al menos 30)",
            ha="center", va="center", fontsize=13, color=OSCURO)
    plt.show()
else:
    # ---- 1. Matriz de correlación (Spearman) entre variables numéricas --------
    corr = df[list(NUMERICAS)].corr(method="spearman").rename(index=NUMERICAS, columns=NUMERICAS)

    # ---- 2. Intensidad de asociación con Profit -------------------------------
    rangos_profit = df["Profit"].rank()
    sst = ((rangos_profit - rangos_profit.mean()) ** 2).sum()

    filas = []
    for col, nombre in NUMERICAS.items():
        if col == "Profit":
            continue
        rho = df["Profit"].corr(df[col], method="spearman")
        if pd.notna(rho):
            filas.append((nombre, abs(rho), "Numérica (|ρ| Spearman)", rho))
    for col, nombre in CATEGORICAS.items():
        medias = rangos_profit.groupby(df[col]).agg(["mean", "size"])
        ssb = (medias["size"] * (medias["mean"] - rangos_profit.mean()) ** 2).sum()
        eta = float(np.sqrt(ssb / sst)) if sst > 0 else np.nan
        if pd.notna(eta):
            filas.append((nombre, eta, "Categórica (η)", np.nan))

    asoc = pd.DataFrame(filas, columns=["variable", "fuerza", "tipo", "signo"])
    asoc = asoc.sort_values("fuerza", ascending=True)      # barh: el mayor queda arriba

    # ---- 3. Figura ------------------------------------------------------------
    sns.set_style("white")
    # Proporción ≈ 2:1 (cuadro de ~740 x 370 px). Power BI escala la imagen manteniendo
    # esta proporción, así que debe parecerse a la del cuadro del visual.
    fig = plt.figure(figsize=(11, 5.5))
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.1], wspace=0.62,
                          left=0.15, right=0.98, top=0.92, bottom=0.14)

    # Panel izquierdo: heatmap triangular
    ax1 = fig.add_subplot(gs[0, 0])
    mascara = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(corr, mask=mascara, annot=False, cmap="RdBu_r",
                vmin=-1, vmax=1, center=0, square=True, linewidths=1.2,
                linecolor="white", cbar_kws={"shrink": 0.7, "pad": 0.04, "label": "ρ de Spearman"},
                ax=ax1)
    # Anotaciones manuales: texto blanco sobre colores oscuros para que se lea
    for i in range(corr.shape[0]):
        for j in range(i + 1):
            v = corr.iloc[i, j]
            ax1.text(j + 0.5, i + 0.5, f"{v:.2f}", ha="center", va="center", fontsize=11,
                     color="white" if abs(v) > 0.45 else OSCURO)
    ax1.set_title("Correlación (Spearman)", loc="left", pad=12,
                  fontsize=13, fontweight="bold", color=OSCURO)
    ax1.tick_params(axis="x", rotation=35, labelsize=10)
    ax1.tick_params(axis="y", rotation=0, labelsize=10)
    for lbl in list(ax1.get_xticklabels()) + list(ax1.get_yticklabels()):
        if lbl.get_text() == "Beneficio":
            lbl.set_fontweight("bold")
            lbl.set_color(NARANJA)

    # Panel derecho: ranking de asociación con Profit
    ax2 = fig.add_subplot(gs[0, 1])
    colores = [AZUL if t.startswith("Numérica") else GRIS for t in asoc["tipo"]]
    barras = ax2.barh(asoc["variable"], asoc["fuerza"], color=colores, height=0.62)
    for barra, (_, fila) in zip(barras, asoc.iterrows()):
        txt = f"{fila['fuerza']:.2f}"
        if pd.notna(fila["signo"]):
            txt += "  (+)" if fila["signo"] > 0 else "  (−)"
        ax2.text(barra.get_width() + 0.01, barra.get_y() + barra.get_height() / 2,
                 txt, va="center", fontsize=10, color=OSCURO)
    ax2.set_xlim(0, max(0.8, asoc["fuerza"].max() + 0.15))
    ax2.set_xlabel("Asociación con el beneficio (0 = ninguna, 1 = perfecta)",
                   fontsize=9.5, color=OSCURO)
    ax2.set_title("¿Qué se asocia más con el beneficio?", loc="left",
                  fontsize=13, fontweight="bold", color=OSCURO)
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.tick_params(axis="y", labelsize=10.5)
    ax2.axvline(0.1, color="#cccccc", lw=0.8, ls="--", zorder=0)
    ax2.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=AZUL),
                        plt.Rectangle((0, 0), 1, 1, color=GRIS)],
               labels=["Numérica: |ρ| de Spearman", "Categórica: η (razón de correlación)"],
               loc="lower right", frameon=False, fontsize=9)

    plt.show()
