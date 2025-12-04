import streamlit as st
from PIL import Image
import pandas as pd
import altair as alt
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
import re

# ---------- PAGE CONFIG (must be first Streamlit call) ----------
icon = Image.open("favicon.png")

st.set_page_config(
    page_title="I-Tower LCRG Progress Dashboard",
    page_icon=icon,
    layout="wide",
)

# ---------- SOCIAL / OG TAGS ----------
st.markdown(
    """
<head>
    <meta property="og:title" content="I-TOWER LCRG Progress Dashboard" />
    <meta property="og:description" content="Live Construction Progress – Lake City Roof Gardens" />
    <meta property="og:image" content="https://raw.githubusercontent.com/Muneebbutt78/tower-progress-app/main/whatsapp_banner.png" />
    <meta property="og:url" content="https://tower-progress-app-cazgj3dwlu4qufudesz7af.streamlit.app/" />
    <meta property="og:type" content="website" />
</head>
""",
    unsafe_allow_html=True,
)

# ---------- OPTIONAL PDF (REPORTLAB) ----------
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# ----------------- CONFIG -----------------
EXCEL_FILE = "Apartment_Progress_Weighted-Progress_App_ITowerAvg_AppView_v5.xlsx"
SHEET_NAME = "Apartment Progress"

ACTIVITY_COLS = [
    "MEP Work",
    "Ceiling",
    "Tile Work",
    "Paint Work",
    "Aluminum Work",
    "Wood Work",
    "MEP Fixtures",
    "MS Work",
    "External Plaster",
    "External Travertine",
    "External Paint",
    "Cleaning",
]

# Weights (sum = 1.0)
WEIGHTS = {
    "MEP Work": 0.12,
    "Ceiling": 0.15,
    "Tile Work": 0.22,
    "Paint Work": 0.10,
    "Aluminum Work": 0.10,
    "Wood Work": 0.20,
    "MEP Fixtures": 0.05,
    "MS Work": 0.02,
    "External Plaster": 0.01,
    "External Travertine": 0.01,
    "External Paint": 0.01,
    "Cleaning": 0.01,
}

PDF_TITLE = "Apartment Progress Report ( I Tower)– Lake City Roof Gardens"
PDF_FOOTER = "Prepared by Muneeb Shehzad Butt – Project Manager"

BASE_DIR = Path(__file__).parent
LAKECITY_LOGO = BASE_DIR / "assets" / "lakecity_logo.png"
UNISON_LOGO = BASE_DIR / "assets" / "unison_logo.png"


# ------------------------------------------------------------
# ---------------------- UTILITIES ---------------------------
# ------------------------------------------------------------
def clamp01(x: float) -> float:
    """Clamp a numeric value to [0, 1]."""
    return max(0.0, min(float(x), 1.0))


def compute_overall(row_like: pd.Series) -> float:
    """Weighted overall progress for a single apartment (0–1)."""
    return sum(row_like[col] * WEIGHTS[col] for col in ACTIVITY_COLS)


def compute_overall_from_means(means: pd.Series) -> float:
    """Weighted overall progress using mean values (0–1)."""
    return sum(means[col] * WEIGHTS[col] for col in ACTIVITY_COLS)


def color_progress(val):
    """Cell background color based on percentage value (0–100)."""
    if pd.isna(val):
        return ""
    if val < 40:
        return "background-color: #ffcccc"  # light red
    elif val < 70:
        return "background-color: #fff7b3"  # light yellow
    else:
        return "background-color: #ccffcc"  # light green


def normalize_activity_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure all activity columns are stored as 0–1 inside the app.

    - If column max <= 1.01 → assume already 0–1, do nothing.
    - If column max > 1.01 and <= 100.1 → assume 0–100 %, divide by 100.
    """
    for col in ACTIVITY_COLS:
        if col not in df.columns:
            continue
        col_max = df[col].max()
        if pd.isna(col_max):
            continue

        if col_max <= 1.01:
            # Already 0–1 fractions; no change
            continue
        elif col_max <= 100.1:
            # Looks like percentages; convert to 0–1
            df[col] = df[col] / 100.0

    return df


# ---------- PDF Generators (no Vs columns, no icons) ----------
def make_pdf_apartment(
    apt_no,
    floor_value,
    apt_overall,
    floor_overall,
    tower_overall,
    table_df: pd.DataFrame,
) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, PDF_TITLE)

    y -= 30
    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"View: Apartment #{apt_no} (Floor {floor_value})")

    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Apartment Total Progress: {apt_overall * 100:.1f}%")
    y -= 15
    c.drawString(40, y, f"Floor Progress: {floor_overall * 100:.1f}%")
    y -= 15
    c.drawString(40, y, f"I-Tower Overall Progress: {tower_overall * 100:.1f}%")

    y -= 25
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Activity-wise Comparison (Apartment / Floor / I-Tower)")

    y -= 20
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y, "Activity")
    c.drawString(210, y, "Apt %")
    c.drawString(270, y, "Floor %")
    c.drawString(340, y, "Tower %")

    c.setFont("Helvetica", 9)
    y -= 15

    for _, r in table_df.iterrows():
        if y < 60:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica-Bold", 10)
            c.drawString(40, y, "Activity-wise Comparison (cont.)")
            y -= 25
            c.setFont("Helvetica-Bold", 9)
            c.drawString(40, y, "Activity")
            c.drawString(210, y, "Apt %")
            c.drawString(270, y, "Floor %")
            c.drawString(340, y, "Tower %")
            y -= 15
            c.setFont("Helvetica", 9)

        c.drawString(40, y, str(r["Activity"])[:28])
        c.drawString(210, y, f"{r['Apartment Progress (%)']:.1f}")
        c.drawString(270, y, f"{r['Floor Progress (%)']:.1f}")
        c.drawString(340, y, f"{r['I-Tower Progress (%)']:.1f}")
        y -= 14

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(40, 35, PDF_FOOTER)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def make_pdf_floor(
    floor_value,
    floor_overall,
    tower_overall,
    table_df: pd.DataFrame,
) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, PDF_TITLE)

    y -= 30
    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"View: Floor {floor_value} Summary")

    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Floor Progress: {floor_overall * 100:.1f}%")
    y -= 15
    c.drawString(40, y, f"I-Tower Overall Progress: {tower_overall * 100:.1f}%")

    y -= 25
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Activity-wise Comparison (Floor / I-Tower)")

    y -= 20
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y, "Activity")
    c.drawString(240, y, "Floor %")
    c.drawString(310, y, "Tower %")

    c.setFont("Helvetica", 9)
    y -= 15

    for _, r in table_df.iterrows():
        if y < 60:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica-Bold", 10)
            c.drawString(40, y, "Activity-wise Comparison (cont.)")
            y -= 25
            c.setFont("Helvetica-Bold", 9)
            c.drawString(40, y, "Activity")
            c.drawString(240, y, "Floor %")
            c.drawString(310, y, "Tower %")
            y -= 15
            c.setFont("Helvetica", 9)

        c.drawString(40, y, str(r["Activity"])[:30])
        c.drawString(240, y, f"{r['Floor Progress (%)']:.1f}")
        c.drawString(310, y, f"{r['I-Tower Progress (%)']:.1f}")
        y -= 14

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(40, 35, PDF_FOOTER)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def make_pdf_tower(tower_overall, table_df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, PDF_TITLE)

    y -= 30
    c.setFont("Helvetica", 11)
    c.drawString(40, y, "View: I-Tower Summary")

    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"I-Tower Overall Progress: {tower_overall * 100:.1f}%")

    y -= 25
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Activity-wise I-Tower Progress")

    y -= 20
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y, "Activity")
    c.drawString(260, y, "Tower %")

    c.setFont("Helvetica", 9)
    y -= 15

    for _, r in table_df.iterrows():
        if y < 60:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica-Bold", 10)
            c.drawString(40, y, "Activity-wise I-Tower Progress (cont.)")
            y -= 25
            c.setFont("Helvetica-Bold", 9)
            c.drawString(40, y, "Activity")
            c.drawString(260, y, "Tower %")
            y -= 15
            c.setFont("Helvetica", 9)

        c.drawString(40, y, str(r["Activity"])[:32])
        c.drawString(260, y, f"{r['I-Tower Progress (%)']:.1f}")
        y -= 14

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(40, 35, PDF_FOOTER)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# ------------- PHOTOS (ZIP) -------------
@st.cache_data
def load_photos_zip(zip_bytes: bytes):
    """
    Read a ZIP of images and assign them to apartments.

    Each .jpg/.jpeg/.png file whose name contains a 3+ digit number
    is mapped to that apartment number.
    """
    if not zip_bytes:
        return {}

    apt_images = {}

    with ZipFile(BytesIO(zip_bytes)) as z:
        for name in z.namelist():
            lower = name.lower()
            if not (
                lower.endswith(".jpg")
                or lower.endswith(".jpeg")
                or lower.endswith(".png")
            ):
                continue

            m = re.search(r"(\d{3,})", name)
            if not m:
                continue

            apt_no = int(m.group(1))

            try:
                data = z.read(name)
            except KeyError:
                continue

            apt_images.setdefault(apt_no, []).append(data)

    return apt_images


# ----------------- LOGOS HEADER -----------------
col_logo_left, col_spacer, col_logo_right = st.columns([1, 6, 1])
with col_logo_left:
    if LAKECITY_LOGO.exists():
        st.image(str(LAKECITY_LOGO), width=120)
    else:
        st.write("**Lake City Roof Gardens**")
with col_logo_right:
    if UNISON_LOGO.exists():
        st.image(str(UNISON_LOGO), width=120)
    else:
        st.write("**UNISON**")


# ----------------- DATA LOADING (ERROR-FRIENDLY) -----------------
@st.cache_data
def load_data(uploaded_file=None):
    """
    Load data from uploaded Excel or default EXCEL_FILE.
    All activity columns are normalized to 0–1 internally.
    """
    try:
        if uploaded_file is not None:
            df = pd.read_excel(uploaded_file, sheet_name=SHEET_NAME, engine="openpyxl")
        else:
            excel_path = Path(EXCEL_FILE)
            if not excel_path.exists():
                st.error(
                    "❌ No Excel file found.\n\n"
                    "Please either:\n"
                    "1) Upload a progress Excel file from the sidebar, **OR**\n"
                    f"2) Place a file named **{EXCEL_FILE}** in the same folder as `app.py`."
                )
                st.stop()
            df = pd.read_excel(excel_path, sheet_name=SHEET_NAME, engine="openpyxl")
    except Exception as e:
        st.error(f"❌ Error reading Excel file: {e}")
        st.stop()

    required_cols = ["Apartment No", "Floor"] + ACTIVITY_COLS
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(
            "❌ Required columns are missing in the Excel file.\n\n"
            f"Missing columns: {', '.join(missing)}"
        )
        st.stop()

    # Keep only numeric apartment numbers
    df = df[pd.to_numeric(df["Apartment No"], errors="coerce").notna()].copy()
    df["Apartment No"] = df["Apartment No"].astype(int)

    # Normalize activity columns to 0–1
    df = normalize_activity_columns(df)

    return df


# ----------------- SIDEBAR -----------------
st.sidebar.title("🔧 Controls")

# File uploads intentionally disabled for now:
# uploaded_excel = st.sidebar.file_uploader("Upload progress Excel (optional)", type=["xlsx"])
# photos_zip_file = st.sidebar.file_uploader("Upload Apartment Photos ZIP (optional)", type=["zip"])
# if photos_zip_file is not None:
#     photos_dict = load_photos_zip(photos_zip_file.getvalue())
# else:
#     photos_dict = {}

uploaded_excel = None
photos_dict = {}

df = load_data(uploaded_excel)

if df.empty:
    st.error("No data found in Excel file.")
    st.stop()

min_apt = int(df["Apartment No"].min())
max_apt = int(df["Apartment No"].max())
tower_means = df[ACTIVITY_COLS].mean()
tower_overall = compute_overall_from_means(tower_means)

apt_no = st.sidebar.number_input(
    "Select Apartment No",
    min_value=min_apt,
    max_value=max_apt,
    value=min_apt,
    step=1,
)

if st.sidebar.button("Go to first apartment 🏠"):
    apt_no = min_apt

st.sidebar.markdown("---")
st.sidebar.info(
    f"Use the box to jump to any apartment between **{min_apt}** and **{max_apt}**."
)

# ----------------- PAGE TITLE -----------------
st.markdown(
    """
<h1 style='display:flex;align-items:center;gap:10px;'>
🏗️ I-Tower Apartment Progress Dashboard
</h1>
""",
    unsafe_allow_html=True,
)

# ----------------- TABS -----------------
tab_apt, tab_floor, tab_tower = st.tabs(
    ["🏢 Apartment View", "🏬 Floor View", "🏙️ Tower Summary"]
)

# ----------------- APARTMENT VIEW -----------------
with tab_apt:
    row = df[df["Apartment No"] == apt_no]
    if row.empty:
        st.error("Apartment not found in data.")
    else:
        row = row.iloc[0]
        floor_value = row["Floor"]
        floor_df = df[df["Floor"] == floor_value]
        floor_means = floor_df[ACTIVITY_COLS].mean()

        apt_overall = compute_overall(row)
        floor_overall = compute_overall_from_means(floor_means)

        apt_overall_bar = clamp01(apt_overall)
        floor_overall_bar = clamp01(floor_overall)
        tower_overall_bar = clamp01(tower_overall)

        c1, c2, c3, c4 = st.columns([1, 1.2, 1.2, 1.2])
        with c1:
            st.metric("Apartment No", f"{int(row['Apartment No'])}")
            st.write(f"Floor: **{floor_value}**")
            if photos_dict:
                if int(row["Apartment No"]) in photos_dict:
                    st.success("📷 Photos available for this apartment.")
                else:
                    st.info("No photos for this apartment in uploaded ZIP.")
        with c2:
            st.metric("Apartment Progress", f"{apt_overall * 100:.1f}%")
            st.progress(apt_overall_bar)
        with c3:
            st.metric("Floor Progress", f"{floor_overall * 100:.1f}%")
            st.progress(floor_overall_bar)
        with c4:
            st.metric("I-Tower Progress", f"{tower_overall * 100:.1f}%")
            st.progress(tower_overall_bar)

        st.markdown("---")
        st.subheader("📋 Activity-wise Comparison (Apartment / Floor / I-Tower)")

        table = []
        for act in ACTIVITY_COLS:
            apt_pct = float(row[act]) * 100
            floor_pct = float(floor_means[act]) * 100
            tower_pct = float(tower_means[act]) * 100
            table.append(
                {
                    "Activity": act,
                    "Apartment Progress (%)": round(apt_pct, 1),
                    "Floor Progress (%)": round(floor_pct, 1),
                    "I-Tower Progress (%)": round(tower_pct, 1),
                }
            )

        table_df = pd.DataFrame(table)

        table_df_styled = (
            table_df.style.format(
                {
                    "Apartment Progress (%)": "{:.1f}",
                    "Floor Progress (%)": "{:.1f}",
                    "I-Tower Progress (%)": "{:.1f}",
                }
            ).map(
                color_progress,
                subset=[
                    "Apartment Progress (%)",
                    "Floor Progress (%)",
                    "I-Tower Progress (%)",
                ],
            )
        )

        st.dataframe(table_df_styled, use_container_width=True)

        # Optional bar chart
        show_chart = st.checkbox(
            "Show graphical comparison (bar chart) 📈", key="apt_chart"
        )
        if show_chart:
            chart_df = table_df.melt(
                id_vars="Activity",
                value_vars=[
                    "Apartment Progress (%)",
                    "Floor Progress (%)",
                    "I-Tower Progress (%)",
                ],
                var_name="Type",
                value_name="Progress (%)",
            )
            chart = (
                alt.Chart(chart_df)
                .mark_bar()
                .encode(
                    x=alt.X("Activity:N", sort=None),
                    y="Progress (%):Q",
                    color="Type:N",
                    column="Type:N",
                    tooltip=["Activity", "Type", "Progress (%)"],
                )
                .properties(height=250)
            )
            st.altair_chart(chart, use_container_width=True)

        # Photos panel
        st.markdown("### 📷 Apartment Photos")
        if not photos_dict:
            st.info(
                "Upload a ZIP file with apartment photos in the sidebar to view images."
            )
        else:
            imgs = photos_dict.get(int(row["Apartment No"]), [])
            if not imgs:
                st.warning(
                    f"No photos found in ZIP for apartment {int(row['Apartment No'])}.\n"
                    f"Make sure filenames contain the apartment number, e.g. "
                    f"`{int(row['Apartment No'])}_kitchen.jpg`."
                )
            else:
                col1, col2 = st.columns(2)
                for i, img_bytes in enumerate(imgs):
                    try:
                        img = Image.open(BytesIO(img_bytes))
                    except Exception:
                        continue
                    if i % 2 == 0:
                        with col1:
                            st.image(img, use_container_width=True)
                    else:
                        with col2:
                            st.image(img, use_container_width=True)

        # Apartment PDF download
        if REPORTLAB_AVAILABLE:
            pdf_bytes = make_pdf_apartment(
                apt_no=int(row["Apartment No"]),
                floor_value=floor_value,
                apt_overall=apt_overall,
                floor_overall=floor_overall,
                tower_overall=tower_overall,
                table_df=table_df,
            )
            st.download_button(
                "📂 Download Apartment PDF Report",
                data=pdf_bytes,
                file_name=f"Apartment_{int(row['Apartment No'])}_Report.pdf",
                mime="application/pdf",
            )
        else:
            st.info(
                "To enable PDF download, install reportlab: `pip install reportlab`."
            )

# ----------------- FLOOR VIEW -----------------
with tab_floor:
    st.subheader("🏬 Floor Search & Progress")

    default_floor_str = ""
    try:
        default_floor_str = str(
            df[df["Apartment No"] == apt_no].iloc[0]["Floor"]
        )
    except Exception:
        pass

    floor_query = st.text_input(
        "Enter Floor (e.g., 1, 2, 3):", value=default_floor_str
    ).strip()

    if floor_query == "":
        st.info("Please enter a floor number to view its progress.")
    else:
        floor_df_view = df[df["Floor"].astype(str) == floor_query]
        if floor_df_view.empty:
            st.error(f"No data found for Floor '{floor_query}'.")
        else:
            floor_means_view = floor_df_view[ACTIVITY_COLS].mean()
            floor_overall_view = compute_overall_from_means(floor_means_view)
            floor_overall_bar = clamp01(floor_overall_view)
            tower_overall_bar = clamp01(tower_overall)

            c1, c2, c3 = st.columns([1.2, 1.2, 1.2])
            with c1:
                st.metric("Floor", floor_query)
                st.write(f"Apartments: {len(floor_df_view)}")
            with c2:
                st.metric("Floor Progress", f"{floor_overall_view * 100:.1f}%")
                st.progress(floor_overall_bar)
            with c3:
                st.metric("I-Tower Progress", f"{tower_overall * 100:.1f}%")
                st.progress(tower_overall_bar)

            st.markdown("---")
            st.subheader("📋 Activity-wise Floor vs I-Tower Comparison")

            table_floor = []
            for act in ACTIVITY_COLS:
                floor_pct = float(floor_means_view[act]) * 100
                tower_pct = float(tower_means[act]) * 100
                table_floor.append(
                    {
                        "Activity": act,
                        "Floor Progress (%)": round(floor_pct, 1),
                        "I-Tower Progress (%)": round(tower_pct, 1),
                    }
                )

            table_floor_df = pd.DataFrame(table_floor)

            table_floor_styled = (
                table_floor_df.style.format(
                    {
                        "Floor Progress (%)": "{:.1f}",
                        "I-Tower Progress (%)": "{:.1f}",
                    }
                ).map(
                    color_progress,
                    subset=[
                        "Floor Progress (%)",
                        "I-Tower Progress (%)",
                    ],
                )
            )

            st.dataframe(table_floor_styled, use_container_width=True)

            # Floor PDF download
            if REPORTLAB_AVAILABLE:
                pdf_bytes_floor = make_pdf_floor(
                    floor_value=floor_query,
                    floor_overall=floor_overall_view,
                    tower_overall=tower_overall,
                    table_df=table_floor_df,
                )
                st.download_button(
                    "📂 Download Floor PDF Report",
                    data=pdf_bytes_floor,
                    file_name=f"Floor_{floor_query}_Report.pdf",
                    mime="application/pdf",
                )
            else:
                st.info(
                    "To enable PDF download, install reportlab: `pip install reportlab`."
                )

# ----------------- TOWER SUMMARY -----------------
with tab_tower:
    st.subheader("🏙️ I-Tower Summary & Search")

    tower_search = st.text_input(
        "Search Activity (optional, e.g., 'Paint', 'MEP'):"
    ).strip()

    table_tower = []
    for act in ACTIVITY_COLS:
        tower_pct = float(tower_means[act]) * 100
        table_tower.append(
            {
                "Activity": act,
                "I-Tower Progress (%)": round(tower_pct, 1),
            }
        )

    table_tower_df = pd.DataFrame(table_tower)

    if tower_search:
        mask = table_tower_df["Activity"].str.contains(
            tower_search, case=False, na=False
        )
        table_tower_df = table_tower_df[mask]

    c1, _ = st.columns([1.2, 1.2])
    with c1:
        st.metric("I-Tower Overall Progress", f"{tower_overall * 100:.1f}%")

    st.markdown("---")
    st.subheader("📋 I-Tower Activity Progress")

    table_tower_styled = (
        table_tower_df.style.format(
            {"I-Tower Progress (%)": "{:.1f}"}
        ).map(color_progress, subset=["I-Tower Progress (%)"])
    )

    st.dataframe(table_tower_styled, use_container_width=True)

    # Tower PDF download
    if REPORTLAB_AVAILABLE:
        pdf_bytes_tower = make_pdf_tower(
            tower_overall=tower_overall,
            table_df=table_tower_df,
        )
        st.download_button(
            "📂 Download Tower PDF Report",
            data=pdf_bytes_tower,
            file_name="ITower_Summary_Report.pdf",
            mime="application/pdf",
        )
    else:
        st.info(
            "To enable PDF download, install reportlab: `pip install reportlab`."
        )
