# ==============================================================================
# V3 · ¿Cómo se comportan las ventas en el tiempo y qué se espera?  (Pregunta 3)
# Visual de Python en Power BI
#
# Campos a arrastrar al visual:
#   Row ID, Order Date (como fecha, NO jerarquía), Sales (No resumir)
#
# Librerías: pandas, numpy, matplotlib
#
# Método (transparente, sin librerías de series de tiempo):
#   1. Ventas mensuales por fecha de pedido.
#   2. Crecimiento interanual g = ventas del último año / ventas del año previo.
#   3. Estacionalidad: peso promedio de cada mes dentro de su año (suma = 1).
#   4. Pronóstico de un mes futuro = (ventas del último año × g^años) × peso del mes.
#   5. Bandas de incertidumbre (80 % y 95 %) con el error logarítmico del
#      ajuste, corregido por los parámetros estimados.
#
# LIMITACIÓN: solo hay 24 meses (2 ciclos estacionales). El pronóstico es
# indicativo y las bandas son anchas; así se muestra a propósito.
# Un chequeo cruzado con Holt-Winters (statsmodels) dio un resultado similar.
# ==============================================================================
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

AZUL, NARANJA, GRIS, OSCURO = "#1F6F8B", "#E07A5F", "#8D99AE", "#2B2D42"
HORIZONTE = 6                      # meses a pronosticar
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

df = dataset.copy()
df["Order Date"] = pd.to_datetime(df["Order Date"])
mensual = df.set_index("Order Date")["Sales"].resample("MS").sum()

# Años calendario completos (12 meses con datos)
conteo = mensual.groupby(mensual.index.year).size()
anios = [a for a, c in conteo.items() if c == 12]


def mensaje(texto):
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.axis("off")
    ax.text(0.5, 0.5, texto, ha="center", va="center", fontsize=13, color=OSCURO)
    plt.show()


if len(anios) < 2:
    mensaje("El pronóstico necesita al menos 2 años completos.\n"
            "Quite los filtros de fecha de este visual.")
elif (mensual[mensual.index.year.isin(anios[-2:])] <= 0).any():
    mensaje("Con el filtro actual hay meses sin ventas.\n"
            "El pronóstico no es confiable con una serie tan escasa.")
else:
    anios = anios[-2:]
    a1, a2 = anios
    hist = mensual[mensual.index.year.isin(anios)]
    tot = hist.groupby(hist.index.year).sum()
    g = tot[a2] / tot[a1]

    # --- Estacionalidad: peso del mes dentro de su año, promediado ------------
    pesos = pd.DataFrame({a: hist[hist.index.year == a].to_numpy() / tot[a] for a in anios},
                         index=range(1, 13)).mean(axis=1)
    pesos = pesos / pesos.sum()

    # --- Ajuste dentro de la muestra y dispersión del error (log) -------------
    ajuste = np.array([tot[d.year] * pesos[d.month] for d in hist.index])
    resid = np.log(hist.to_numpy()) - np.log(ajuste)
    gl = max(1, len(hist) - (11 + len(anios)))
    sd = float(np.sqrt((resid ** 2).sum() / gl))

    # --- Pronóstico -----------------------------------------------------------
    futuro = pd.date_range(mensual.index[-1] + pd.offsets.MonthBegin(1), periods=HORIZONTE, freq="MS")
    fc = np.array([tot[a2] * g ** (d.year - a2) * pesos[d.month] for d in futuro])
    z80, z95 = 1.2816, 1.96
    lo80, hi80 = fc * np.exp(-z80 * sd), fc * np.exp(z80 * sd)
    lo95, hi95 = fc * np.exp(-z95 * sd), fc * np.exp(z95 * sd)

    # --- Referencia: mismos meses del año anterior ----------------------------
    previo = np.array([mensual.get(d - pd.DateOffset(years=1), np.nan) for d in futuro])
    var_fc = fc.sum() / np.nansum(previo) - 1 if np.isfinite(previo).any() else np.nan

    # --- Tendencia lineal de la serie observada -------------------------------
    t = np.arange(len(mensual))
    pend, ord_ = np.polyfit(t, mensual.to_numpy(), 1)
    tendencia = ord_ + pend * t

    # --- Figura ---------------------------------------------------------------
    # Proporción ≈ 2.4:1 (cuadro de ~900 x 380 px): Power BI escala la imagen manteniéndola.
    fig, ax = plt.subplots(figsize=(13, 5.5))
    ax.axvspan(futuro[0] - pd.Timedelta(days=15), futuro[-1] + pd.Timedelta(days=15),
               color=NARANJA, alpha=0.06, zorder=0)
    ax.fill_between(futuro, lo95, hi95, color=NARANJA, alpha=0.15, label="Banda 95 %", lw=0)
    ax.fill_between(futuro, lo80, hi80, color=NARANJA, alpha=0.30, label="Banda 80 %", lw=0)
    ax.plot(mensual.index, tendencia, color=GRIS, ls=":", lw=2,
            label=f"Tendencia lineal (+{pend:,.0f} $/mes)")
    ax.plot(mensual.index, mensual.to_numpy(), color=AZUL, lw=2.6, marker="o", ms=5,
            label="Ventas mensuales")
    ax.plot([mensual.index[-1], *futuro], [mensual.iloc[-1], *fc], color=NARANJA, lw=2.6,
            ls="--", marker="o", ms=5, label="Pronóstico")

    # Pico de cada año (el mes de mayores ventas)
    for anio, serie in mensual.groupby(mensual.index.year):
        d = serie.idxmax()
        ax.annotate(f"Pico {MESES[d.month - 1]}", (d, serie.max()), xytext=(0, 12),
                    textcoords="offset points", ha="center", fontsize=9, color=AZUL,
                    fontweight="bold")

    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v / 1000:,.0f}k"))
    todas = mensual.index.append(futuro)
    marcas = todas[::3]
    ax.set_xticks(marcas)
    ax.set_xticklabels([f"{MESES[d.month - 1]} {str(d.year)[2:]}" for d in marcas], fontsize=10)
    ax.set_ylim(0, max(hi95.max(), mensual.max()) * 1.12)
    ax.set_ylabel("Ventas del mes")
    ax.grid(axis="x", visible=False)
    ax.grid(axis="y", color="#e5e5e5")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("Ventas mensuales y pronóstico de los próximos 6 meses",
                 loc="left", fontsize=13, fontweight="bold", color=OSCURO)

    cuadro = (f"{a2} vs {a1}: {g - 1:+.1%}\n"
              f"Pronóstico {MESES[futuro[0].month - 1]}–{MESES[futuro[-1].month - 1]} {futuro[-1].year}: "
              f"${fc.sum() / 1000:,.0f}k")
    if np.isfinite(var_fc):
        cuadro += f" ({var_fc:+.0%} vs mismo período previo)"
    ax.text(0.01, 0.97, cuadro, transform=ax.transAxes, va="top", fontsize=10.5, color=OSCURO,
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#dddddd"))
    ax.legend(loc="upper left", bbox_to_anchor=(0.01, 0.80), frameon=False, fontsize=9.5)
    # El método y la advertencia de pocos meses de historia van en un cuadro de texto del dashboard.
    plt.tight_layout()
    plt.show()
