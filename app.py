# =============================================================
#  TOWER PROGRESS DASHBOARD - FINAL CLEANED VERSION (WITH COMMENTS)
#  ONLY PHOTO SECTION CLEANED AS PER USER REQUEST
# =============================================================

import streamlit as st
import pandas as pd
from PIL import Image
import os
import zipfile
from io import BytesIO
import re  # for parsing tower names
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from datetime import datetime, timedelta

def show_full_width_table(df):
    """Render dataframe with all columns visible"""
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            col: st.column_config.Column(width="small")
            for col in df.columns
        }
    )


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UNISON_LOGO = os.path.join(BASE_DIR, "assets", "unison_logo.png")
LAKECITY_LOGO = os.path.join(BASE_DIR, "assets", "lakecity_logo.png")


def get_previous_friday():
    today = datetime.today()
    weekday = today.weekday()  # Monday=0 ... Friday=4

    # Days since last Friday
    days_since_friday = (weekday - 4) % 7

    # If today is Friday, go back 7 days
    if days_since_friday == 0:
        days_since_friday = 7

    last_friday = today - timedelta(days=days_since_friday)
    return last_friday.strftime("%d %B %Y")
def render_global_header():
    col1, col2, col3 = st.columns([2, 6, 2])

    with col1:
        if os.path.exists(LAKECITY_LOGO):
            st.image(LAKECITY_LOGO, width=160)

    with col2:
        st.markdown(
            f"""
            <div style="text-align:center;">
                <h2 style="margin-bottom:0;">Lake City Roof Gardens</h2>
                <p style="margin-top:4px; font-size:14px;">
                    Progress Dashboard | <b>Report Date:</b> {get_previous_friday()}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        if os.path.exists(UNISON_LOGO):
            st.image(UNISON_LOGO, width=130)

    st.markdown("---")






# --------------------------- PDF SUPPORT --------------------------
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# --------------------------- STREAMLIT CONFIG ----------------------
st.set_page_config(
    page_title="All Tower Progress Dashboard – Lake City Roof Gardens",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================
# PREVIEW CARD (controls Streamlit / WhatsApp preview snapshot)
# Put your banner here: assets/preview_card.png
# =============================================================
PREVIEW_CARD_PATH = os.path.join("assets", "preview_card.png")
if os.path.exists(PREVIEW_CARD_PATH):
    st.image(PREVIEW_CARD_PATH, use_container_width=True)
else:
    # Keep silent in production if you prefer:
    st.info("Add assets/preview_card.png to control the WhatsApp/Streamlit preview image.", icon="🖼️")


render_global_header()



# --------------------------- CONSTANTS -----------------------------
EXCEL_FILE = "Apartment_Progress_Weighted-Progress_App_ITowerAvg_AppView_v5.xlsx"

SHEET_LCRG = "LCRG Progress"
SHEET_APT = "Apartment Progress"
SHEET_EXT = "External Development"
SHEET_RT  = "Roof top"
SHEET_GF  = "Ground Floor"
SHEET_CA  = "Common Area"

PHOTO_DIR = r"E:\All_tower_app\uploaded_photos"
os.makedirs(PHOTO_DIR, exist_ok=True)

# Activity columns for apartment progress
ACTIVITY_COLS = [
    "MEP Work", "Ceiling", "Tile Work", "Paint Work", "Aluminum Work",
    "Wood Work", "MEP Fixtures", "MS Work", "External Plaster",
    "External Travertine", "External Paint", "Cleaning"
]

# Weightage for overall calculation
WEIGHTS = {
    "MEP Work": 0.12, "Ceiling": 0.15, "Tile Work": 0.22, "Paint Work": 0.10,
    "Aluminum Work": 0.10, "Wood Work": 0.20, "MEP Fixtures": 0.05,
    "MS Work": 0.02, "External Plaster": 0.01, "External Travertine": 0.01,
    "External Paint": 0.01, "Cleaning": 0.01
}

# =============================================================
#  HELPER FUNCTIONS
# =============================================================

def safe_percent_series(s):
    s = pd.to_numeric(s, errors="coerce").fillna(0)
    return s / 100 if s.max() > 1.5 else s

def color_progress(val):
    try:
        v = float(str(val).replace("%", ""))
    except:
        return ""

    if v < 40:
        return "background-color:#ffcccc;"   # light red
    elif v < 70:
        return "background-color:#fff3cd;"   # yellow
    return "background-color:#d4edda;"       # light green

def style_progress_table(df):
    """
    Apply progress coloring to all numeric columns
    """
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    return (
        df.style
        .map(color_progress, subset=numeric_cols)
        .format({col: "{:.0f}%" for col in numeric_cols})
    )



def compute_overall(row):
    return float(sum(row.get(col, 0) * WEIGHTS[col] for col in ACTIVITY_COLS)) * 100

def make_photo_key(tower, apt):
    t = str(tower).strip()
    prefix = re.split(r"[\s-]+", t)[0]
    try:
        apt_str = str(int(float(apt)))
    except:
        apt_str = str(apt).strip()
    return f"{prefix}-{apt_str}"

def ensure_apt_folder_from_zip(key):
    apt_dir = os.path.join(PHOTO_DIR, key)
    if os.path.isdir(apt_dir):
        existing = [f for f in os.listdir(apt_dir)
                    if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        if existing:
            return apt_dir

    for fname in os.listdir(PHOTO_DIR):
        if fname.lower().endswith(".zip") and fname.startswith(key):
            try:
                with zipfile.ZipFile(os.path.join(PHOTO_DIR, fname), "r") as zf:
                    os.makedirs(apt_dir, exist_ok=True)
                    for member in zf.namelist():
                        if member.lower().endswith((".jpg", ".jpeg", ".png")):
                            with zf.open(member) as imgf:
                                try:
                                    img = Image.open(imgf)
                                    img.load()
                                except:
                                    continue
                                img.save(os.path.join(apt_dir, os.path.basename(member)))
            except:
                pass
            break
    return apt_dir

def save_photos(tower, apartment_no, files):
    key = make_photo_key(tower, apartment_no)
    apt_dir = os.path.join(PHOTO_DIR, key)
    os.makedirs(apt_dir, exist_ok=True)

    for f in files:
        name = f.name.lower()

        if name.endswith(".zip"):
            try:
                with zipfile.ZipFile(BytesIO(f.read()), "r") as zf:
                    for m in zf.namelist():
                        if m.lower().endswith((".jpg", ".jpeg", ".png")):
                            with zf.open(m) as imgf:
                                try:
                                    img = Image.open(imgf)
                                    img.load()
                                except:
                                    continue
                                img.save(os.path.join(apt_dir, os.path.basename(m)))
            except Exception as e:
                st.warning(f"Zip error: {e}")

        elif name.endswith((".jpg", ".jpeg", ".png")):
            try:
                img = Image.open(f)
                img.load()
                img.save(os.path.join(apt_dir, f.name))
            except:
                st.warning(f"Cannot save {f.name}")

def get_apartment_photos(tower, apartment_no):
    key = make_photo_key(tower, apartment_no)
    apt_dir = ensure_apt_folder_from_zip(key)
    if not os.path.isdir(apt_dir):
        return key, apt_dir, []
    files = [os.path.join(apt_dir, f) for f in os.listdir(apt_dir)
             if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    files.sort()
    return key, apt_dir, files

def show_photos(tower, apt_no):
    key, apt_dir, files = get_apartment_photos(tower, apt_no)
    st.caption(f"Folder: {apt_dir}")
    if not files:
        st.info("No photos found.")
        return
    col1, col2 = st.columns(2)
    for i, path in enumerate(files):
        try:
            img = Image.open(path)
            if img.width > img.height:
                img = img.rotate(90, expand=True)
            img = img.resize((450, 650))
        except:
            continue
        (col1 if i % 2 == 0 else col2).image(img, caption=os.path.basename(path))
# =============================================================
# GENERIC SECTION PHOTO HELPERS (GF / CA / External)
# =============================================================
def get_section_photo_dir(section, tower):
    path = os.path.join(PHOTO_DIR, section, str(tower).strip())
    os.makedirs(path, exist_ok=True)
    return path


def save_section_photos(section, tower, files):
    path = get_section_photo_dir(section, tower)

    for f in files:
        name = f.name.lower()

        if name.endswith(".zip"):
            try:
                with zipfile.ZipFile(BytesIO(f.read()), "r") as zf:
                    for m in zf.namelist():
                        if m.lower().endswith((".jpg", ".jpeg", ".png")):
                            img = Image.open(zf.open(m))
                            img.save(os.path.join(path, os.path.basename(m)))
            except Exception as e:
                st.error(f"ZIP error: {e}")

        elif name.endswith((".jpg", ".jpeg", ".png")):
            img = Image.open(f)
            img.save(os.path.join(path, f.name))


def show_section_photos(section, tower):
    path = get_section_photo_dir(section, tower)
    files = sorted(
        f for f in os.listdir(path)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )

    st.caption(f"📁 {path}")
    st.caption(f"🖼 Images: {len(files)}")

    if not files:
        st.info("No photos uploaded yet.")
        return

    col1, col2 = st.columns(2)
    for i, fname in enumerate(files):
        img = Image.open(os.path.join(path, fname))
        if img.width > img.height:
            img = img.rotate(90, expand=True)
        img = img.resize((450, 650))
        (col1 if i % 2 == 0 else col2).image(img, caption=fname)
# =============================================================
# GENERIC PDF GENERATOR (NON-APARTMENT SECTIONS)
# =============================================================
def generate_section_pdf(title, tower, progress_text, table_df, photo_path=None):
    buffer = BytesIO()

    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors

    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    y = height - 50
    # ----- Header Logos -----
    logo_y = height - 55

    # LAKE CITY → LEFT
    if os.path.exists(LAKECITY_LOGO):
        c.drawImage(
            LAKECITY_LOGO,
            40,
            logo_y,
            width=110,
            height=40,
            preserveAspectRatio=True,
            mask="auto"
        )

    # UNISON → RIGHT
    if os.path.exists(UNISON_LOGO):
        c.drawImage(
            UNISON_LOGO,
            width - 140,
            logo_y,
            width=90,
            height=40,
            preserveAspectRatio=True,
            mask="auto"
        )

    # ----- Footer -----
    footer_y = 30
    c.setFont("Helvetica", 9)

    # Left: Prepared by
    c.drawString(
        40,
        footer_y,
        "Prepared by: Muneeb Butt"
    )

    # Center: Friday date
    c.drawCentredString(
        width / 2,
        footer_y,
        f"Date: {get_previous_friday()}"
    )

    # Right: Page number
    c.drawRightString(
        width - 40,
        footer_y,
        f"Page {c.getPageNumber()}"
    )



   # ----- Title (CLEARLY BELOW LOGOS) -----
    y = height - 110

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, y, title)
    y -= 30


    # ----- Meta -----
    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Tower: {tower}")
    y -= 18
    c.drawString(40, y, f"Progress: {progress_text}")
    y -= 25

    # ----- Section Title -----
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Progress Details")

    # IMPORTANT: move cursor WELL BELOW the heading
    y -= 35


    # ---------------------------------------------------------
    # Identify REAL activity columns only
    # ---------------------------------------------------------
    exclude_cols = {
        "Tower", "Area", "Progress %",
        "Activity", "SortOrder", "Floor"
    }

    activity_cols = [
        col for col in table_df.columns
        if (
            col not in exclude_cols
            and not col.lower().startswith("unnamed")
            and pd.api.types.is_numeric_dtype(table_df[col])
        )
    ]

    # Safety check
    if table_df.empty or not activity_cols:
        c.setFont("Helvetica", 10)
        c.drawString(40, y, "No activity data available.")
    else:
        row = table_df.iloc[0]

        # ----- Build table data -----
        table_data = [["Activity", "Progress %"]]
        for act in activity_cols:
            val = float(row.get(act, 0))
            display_val = val * 100 if val <= 1 else val
            table_data.append([act, f"{display_val:.2f}%"])


        # ----- Create table -----
        tbl = Table(
            table_data,
            colWidths=[320, 140]
        )

        tbl.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))

        # ----- Draw table -----
        tbl.wrapOn(c, width, height)
        tbl_height = len(table_data) * 18

        # Draw table BELOW the section heading
        tbl.drawOn(c, 40, y - tbl_height)

        # Move cursor down after table
        y = y - tbl_height - 30


    # ----- Photo -----
    if photo_path:
        try:
            img = ImageReader(photo_path)
            c.drawImage(img, 40, 40, width=240, preserveAspectRatio=True)
        except:
            pass

    c.save()
    buffer.seek(0)
    return buffer



# =============================================================
#  PDF GENERATION FUNCTION — ADDED BACK
# =============================================================

def generate_apartment_pdf(row, floor_overall, tower_overall, table_df, photo_path):
    try:
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)

        x_margin = 50
        y_start = 800

        c.setFont("Helvetica-Bold", 16)
        c.drawString(x_margin, y_start, "Apartment Progress Report – Lake City Roof Gardens")

        c.setFont("Helvetica", 12)
        c.drawString(x_margin, y_start - 30, f"Apartment: {int(row['Apartment No'])}")
        c.drawString(x_margin, y_start - 50, f"Tower: {row['Tower']}")
        c.drawString(x_margin, y_start - 70, f"Floor: {int(row['Floor'])}")

        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_margin, y_start - 110, "Overall Progress Summary:")

        c.setFont("Helvetica", 11)
        c.drawString(x_margin, y_start - 130, f"Apartment Progress: {compute_overall(row):.2f}%")
        c.drawString(x_margin, y_start - 150, f"Floor Progress: {floor_overall:.2f}%")
        c.drawString(x_margin, y_start - 170, f"Tower Progress: {tower_overall:.2f}%")

        if photo_path:
            try:
                img = Image.open(photo_path)
                img.thumbnail((350, 350))
                img_reader = ImageReader(img)
                c.drawImage(img_reader, x_margin, y_start - 500, width=300, height=300)
            except:
                pass

        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_margin, y_start - 540, "Activity Progress")

        c.setFont("Helvetica", 10)
        table_y = y_start - 560

        for idx, row_data in table_df.iterrows():
            act = row_data["Activity"]
            aptv = f"{row_data['Apt %']:.2f}"
            flv  = f"{row_data['Floor %']:.2f}"
            twv  = f"{row_data['Tower %']:.2f}"

            c.drawString(
                x_margin, table_y,
                f"{act:30} Apt:{aptv}%  Floor:{flv}%  Tower:{twv}%"
            )

            table_y -= 14
            if table_y < 80:
                c.showPage()
                c.setFont("Helvetica", 10)
                table_y = 800

        c.showPage()
        c.save()
        pdf_data = buffer.getvalue()
        buffer.close()
        return pdf_data

    except Exception as e:
        st.error(f"PDF generation error: {e}")
        return None
# =============================================================
# INITIALIZE PHOTO DIRECTORY STRUCTURE (ONE-TIME SAFE)
# =============================================================

def init_photo_folders(base_dir):
    structure = {
        "Apartment": [],  # apartment folders created dynamically
        "Tower": ["I", "L1", "L2"],
        "Floor": ["I-Floor-01", "L1-Floor-03"],  # samples only
        "Rooftop": ["I", "L1", "L2"],
        "GroundFloor": ["I", "L1", "L2"],
        "CommonArea": ["I", "L1", "L2"],
        "External": ["I", "L1", "L2"],
    }

    for section, subfolders in structure.items():
        section_path = os.path.join(base_dir, section)
        os.makedirs(section_path, exist_ok=True)

        for sub in subfolders:
            os.makedirs(os.path.join(section_path, sub), exist_ok=True)


# 🔹 CALL IT ONCE
init_photo_folders(PHOTO_DIR)

# =============================================================
#  DATA LOADERS (unchanged)
# =============================================================

def load_apartment_progress():
    df = pd.read_excel(EXCEL_FILE, SHEET_APT)
    df.columns = df.columns.str.strip()

    if "Unnamed: 0" in df.columns:
        df.drop(columns=["Unnamed: 0"], inplace=True)

    df = df[pd.to_numeric(df["Apartment No"], errors="coerce").notna()]
    df["Apartment No"] = df["Apartment No"].astype(int)

    df["Floor"] = (
        df["Floor"].astype(str)
        .str.extract(r"(\d+)", expand=False)
        .astype(float).fillna(0).astype(int)
    )

    df["Tower"] = df["Tower"].astype(str).str.strip()

    for col in ACTIVITY_COLS:
        df[col] = safe_percent_series(df[col]) if col in df else 0

    return df.reset_index(drop=True)

def load_ext(df):
    df.columns = df.columns.str.strip()
    df["Progress %"] = pd.to_numeric(df.get("Progress %", 0), errors="coerce").fillna(0)
    df["Tower"] = df.get("Tower", "").astype(str).str.strip()
    if "Activity" not in df.columns:
        df["Activity"] = df[df.columns[0]].astype(str)
    return df.reset_index(drop=True)

def load_lcrg():
    df = pd.read_excel(EXCEL_FILE, SHEET_LCRG)
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.str.contains("Unnamed", case=False)]
    return df

df_ext = load_ext(pd.read_excel(EXCEL_FILE, SHEET_EXT))
df_rt  = load_ext(pd.read_excel(EXCEL_FILE, SHEET_RT))
df_gf  = load_ext(pd.read_excel(EXCEL_FILE, SHEET_GF))
df_ca  = load_ext(pd.read_excel(EXCEL_FILE, SHEET_CA))
df_apt = load_apartment_progress()
df_lcrg = load_lcrg()

tower_list = sorted(df_apt["Tower"].unique())
floor_list = sorted(df_apt["Floor"].unique())
apt_list   = sorted(df_apt["Apartment No"].unique())

# =============================================================
#  SIDEBAR FILTERS
# =============================================================

with st.sidebar.expander("🏢 Filters", expanded=True):
    tower_filter = st.selectbox("Tower", ["All"] + tower_list)
    floor_filter = st.selectbox("Floor", ["All"] + floor_list)
    apt_filter   = st.selectbox("Apartment", ["All"] + apt_list)

with st.sidebar.expander("🔍 Activity Search", expanded=False):
    activity_filter = st.text_input("Search Activity")
# =============================================================
#  📤 SHARE DASHBOARD ON WHATSAPP
# =============================================================

st.sidebar.markdown("---")

st.sidebar.markdown(
    """
    <a href="https://wa.me/?text=🏗️%20All%20Tower%20Progress%20Dashboard%20-%20Lake%20City%20Roof%20Gardens%0A%0ALive%20Tower,%20Floor%20%26%20Apartment-wise%20Progress%20Monitoring%0Ahttps://alltowerapp-x3ees3svpm6xchmrsqe3hc.streamlit.app/"
       target="_blank"
       style="text-decoration:none;">
       <button style="
           background:#25D366;
           color:white;
           padding:10px 14px;
           border:none;
           border-radius:6px;
           font-size:14px;
           width:100%;
           cursor:pointer;">
           📤 Share Dashboard on WhatsApp
       </button>
    </a>
    """,
    unsafe_allow_html=True
)


# Auto-select relevant view
view_options = [
    "🏁 LCRG Progress",
    "🏙 Tower Summary",
    "🏬 Floor Summary",
    "🏢 Apartment Progress",
    "🌳 External Development",
    "⬆️ Rooftop",
    "🧱 Ground Floor",
    "🏛 Common Area",
    "📷 Photo Viewer"
]
default_view = "🏁 LCRG Progress"

view_mode = st.radio(
    "Select View",
    view_options,
    index=view_options.index(default_view),
    horizontal=True
)
# =============================================================
# 🏁 LCRG OVERALL PROGRESS (LANDING PAGE)
# =============================================================
if view_mode == "🏁 LCRG Progress":

    st.header("🏁 LCRG Progress Dashboard")

    df = df_lcrg.copy()
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.str.contains("Unnamed", case=False)]

    # ---------------------------------------------------------
    # REMOVE WEIGHTAGE ROW (DISPLAY ONLY)
    # ---------------------------------------------------------
    df = df[~df["Area"].str.contains("Weight", case=False, na=False)]

    # ---------------------------------------------------------
    # CLEAN FINAL PROGRESS %
    # ---------------------------------------------------------
    df["Progress %"] = (
        df["Progress %"]
        .astype(str)
        .str.replace("%", "", regex=False)
        .astype(float)*100
    )

    # ---------------------------------------------------------
    # KPI — OVERALL LCRG
    # ---------------------------------------------------------
    overall_val = df[df["Area"].str.contains("LCRG", case=False)]["Progress %"].mean()
    st.metric("🌍 LCRG Overall Progress", f"{overall_val:.2f}%")

    # ---------------------------------------------------------
    # COLUMNS STORED AS DECIMALS → CONVERT TO %
    # ---------------------------------------------------------
    percent_cols = [
        "Apartment Progress",
        "External development",
        "Ground Floor",
        "Roof Top",
        "Common Area",
        "Cleaning"
    ]

    for col in percent_cols:
        if col in df.columns:
            df[col] = df[col] * 100

    # ---------------------------------------------------------
    # COLOR LOGIC
    # ---------------------------------------------------------
    def color_progress(val):
        try:
            val = float(val)
        except:
            return ""
        if val < 40:
            return "background-color:#ffcccc;"
        elif val < 70:
            return "background-color:#fff7b3;"
        return "background-color:#ccffcc;"

    # ---------------------------------------------------------
    # HIGHLIGHT LCRG ROW
    # ---------------------------------------------------------
    def highlight_lcrg(row):
        if "LCRG" in str(row["Area"]):
            return ["background-color:#e8f0fe; font-weight:bold;"] * len(row)
        return [""] * len(row)

    # ---------------------------------------------------------
    # DISPLAY TABLE
    # ---------------------------------------------------------
    display_cols = [
        "Tower",
        "Area",
        "Apartment Progress",
        "External development",
        "Ground Floor",
        "Roof Top",
        "Common Area",
        "Cleaning",
        "Progress %"
    ]

    st.dataframe(
        df[display_cols]
            .style
            .apply(highlight_lcrg, axis=1)
            .map(color_progress, subset=["Progress %"])
            .format(
                {c: "{:.2f}%" for c in percent_cols}
                | {"Progress %": "{:.2f}%"}
            ),
        use_container_width=True
    )
# =============================================================
#  1) TOWER SUMMARY
# =============================================================
if view_mode == "🏙 Tower Summary":
    st.header("🏙 Tower Summary-Apartments")

    # Compute mean of activities per tower
    df_tower = df_apt.groupby("Tower")[ACTIVITY_COLS].mean()

    # Weighted overall % × 1.09 boost (capped at 100%)
    df_tower["Overall %"] = df_tower.apply(
        lambda r: min(compute_overall(r) * 1.13, 100),
        axis=1
    )

    # Convert decimals to %
    df_tower_display = df_tower.copy()
    for col in ACTIVITY_COLS:
        df_tower_display[col] = df_tower_display[col] * 100

    # -------- LCRG Overall Progress (I=40%, L1=30%, L2=30%) ----------
    P_I  = df_tower["Overall %"].get("I", 0)
    P_L1 = df_tower["Overall %"].get("L1", 0)
    P_L2 = df_tower["Overall %"].get("L2", 0)

    lcrg_overall = (P_I * 0.40) + (P_L1 * 0.30) + (P_L2 * 0.30)
    st.metric("🌎 LCRG Overall Progress", f"{lcrg_overall:.2f}%")

    # -------- Specific tower view -----------
    if tower_filter != "All":
        st.subheader(f"🏢 {tower_filter} Tower Progress")

        st.metric(
            "Overall Tower Progress",
            f"{df_tower.loc[tower_filter]['Overall %']:.2f}%"
        )

        st.dataframe(
            df_tower_display.loc[[tower_filter]]
                .style.map(color_progress, subset=ACTIVITY_COLS + ["Overall %"])
                .format("{:.2f}"),
            use_container_width=True
        )

    # -------- All towers view -----------
    else:
        st.subheader("🏢 Tower-wise Progress Overview")
        st.dataframe(
            df_tower_display
                .style.map(color_progress, subset=ACTIVITY_COLS + ["Overall %"])
                .format("{:.2f}"),
            use_container_width=True
        )

# =============================================================
#  2) FLOOR SUMMARY
# =============================================================
elif view_mode == "🏬 Floor Summary":
    st.header("🏬 Floor Summary-Apartments")

    df_floor = df_apt.groupby(["Tower", "Floor"])[ACTIVITY_COLS].mean().reset_index()
    df_floor["Overall %"] = df_floor.apply(lambda r: compute_overall(r), axis=1)

    # Apply filters
    if tower_filter != "All":
        df_floor = df_floor[df_floor["Tower"] == tower_filter]
    if floor_filter != "All":
        df_floor = df_floor[df_floor["Floor"] == floor_filter]

    if df_floor.empty:
        st.warning("No floor data found.")
    else:
        df_floor_display = df_floor.copy()
        for col in ACTIVITY_COLS:
            df_floor_display[col] = df_floor_display[col] * 100

        # Show floor metric if tower + floor selected
        if tower_filter != "All" and floor_filter != "All":
            sel = df_floor.iloc[0]
            st.metric("Floor Progress", f"{sel['Overall %']:.2f}%")

        st.dataframe(
            df_floor_display.set_index(["Tower", "Floor"])
                .style.map(color_progress, subset=ACTIVITY_COLS + ["Overall %"])
                .format("{:.2f}"),
            use_container_width=True
        )

        # Summary if only tower selected
        if tower_filter != "All" and floor_filter == "All":
            st.subheader("📊 Floor Progress Overview")
            for _, r in df_floor.iterrows():
                st.metric(
                    f"{r['Tower']} - Floor {r['Floor']}",
                    f"{r['Overall %']:.2f}%"
                )

# =============================================================
#  3) APARTMENT PROGRESS (WITH CLEAN PHOTO SECTION)
# =============================================================
elif view_mode == "🏢 Apartment Progress":
    st.header("🏢 Apartment Progress")

    # Apply filters
    df_view = df_apt.copy()
    if tower_filter != "All":
        df_view = df_view[df_view["Tower"] == tower_filter]
    if floor_filter != "All":
        df_view = df_view[df_view["Floor"] == floor_filter]
    if apt_filter != "All":
        df_view = df_view[df_view["Apartment No"] == apt_filter]

    if df_view.empty:
        st.warning("No apartment matches these filters.")
    else:
        row = df_view.iloc[0]

        apt_no = int(row["Apartment No"])
        tower_name = row["Tower"]
        floor_no = int(row["Floor"])

        # ---------------- HEADER ----------------
        st.markdown(
            f"""
            <h2 style='margin-bottom:0px;'>
                Apartment {apt_no} — <span style="color:#444;">{tower_name} | Floor {floor_no}</span>
            </h2>
            <p style='margin-top:0px; color:#777;'>Detailed apartment-wise progress analysis</p>
            """,
            unsafe_allow_html=True
        )

        # ---------------- METRICS ----------------
        apt_overall = compute_overall(row)

        df_floor_scope = df_apt[
            (df_apt["Tower"] == tower_name) &
            (df_apt["Floor"] == floor_no)
        ]
        df_tower_scope = df_apt[df_apt["Tower"] == tower_name]

        floor_overall = compute_overall(df_floor_scope[ACTIVITY_COLS].mean())

        # Tower boosted ×1.09 (same as Tower Summary)
        tower_overall = compute_overall(df_tower_scope[ACTIVITY_COLS].mean())
        tower_overall = min(tower_overall * 1.13, 100)

        c1, c2, c3 = st.columns(3)
        c1.metric("Apartment Progress", f"{apt_overall:.2f}%")
        c2.metric("Floor Progress", f"{floor_overall:.2f}%")
        c3.metric("Tower Progress", f"{tower_overall:.2f}%")

        # ---------------- ACTIVITY TABLE ----------------
        rows = []
        for act in ACTIVITY_COLS:
            rows.append([
                act,
                float(row[act] * 100),
                float(df_floor_scope[act].mean() * 100),
                float(df_tower_scope[act].mean() * 100)
            ])

        table_df = pd.DataFrame(rows, columns=["Activity", "Apt %", "Floor %", "Tower %"])

        # Safe numeric formatting
        for col in ["Apt %", "Floor %", "Tower %"]:
            table_df[col] = pd.to_numeric(table_df[col], errors="coerce").fillna(0)

        st.dataframe(
            table_df.style
                .map(color_progress, subset=["Apt %", "Floor %", "Tower %"])
                .format({
                    "Apt %": "{:.2f}",
                    "Floor %": "{:.2f}",
                    "Tower %": "{:.2f}",
                })
                .set_table_styles([
                    {"selector": "th", "props": [("font-size", "16px"), ("padding", "8px")]},
                    {"selector": "td", "props": [("padding", "8px"), ("font-size", "15px")]}
                ]),
            use_container_width=True
        )

        # =============================================================
        #  CLEAN FINAL PHOTO SECTION (FIXED)
        # =============================================================
        st.subheader("Apartment Photos")

        key, apt_dir, files = get_apartment_photos(tower_name, apt_no)
        st.caption(f"Photo key: {key} | Folder: {apt_dir}")

        # Show photos (portrait mode)
        if files:
            col1, col2 = st.columns(2)
            for i, path in enumerate(files):
                try:
                    img = Image.open(path)
                    if img.width > img.height:
                        img = img.rotate(90, expand=True)
                    img = img.resize((450, 650))
                except:
                    continue

                (col1 if i % 2 == 0 else col2).image(
                    img, caption=os.path.basename(path)
                )

            first_photo_path = files[0]

        else:
            st.info("No photos found for this apartment.")
            first_photo_path = None

        # ---------------- Upload Photos ----------------
        uploaded = st.file_uploader(
            "Upload Images or ZIP",
            type=["jpg", "jpeg", "png", "zip"],
            accept_multiple_files=True,
            key=f"apt_upload_{tower_name}_{apt_no}"   # unique key
        )

        if uploaded:
            save_photos(tower_name, apt_no, uploaded)
            st.success("Photos saved.")

            # Reload first photo
            key, apt_dir, files = get_apartment_photos(tower_name, apt_no)
            if files:
                first_photo_path = files[0]

        # ---------------- PDF EXPORT ----------------
        st.markdown("---")
        if REPORTLAB_AVAILABLE:
            pdf_bytes = generate_apartment_pdf(
                row, floor_overall, tower_overall, table_df, first_photo_path
            )
            if pdf_bytes is not None:
                file_key = make_photo_key(tower_name, apt_no)
                st.download_button(
                    label="📄 Download Apartment PDF Report",
                    data=pdf_bytes,
                    file_name=f"{file_key}_report.pdf",
                    mime="application/pdf"
                )
        else:
            st.info("PDF engine not available on this system.")
   
# =============================================================
# 4) EXTERNAL DEVELOPMENT (Child → Summary → KPI)
# =============================================================
elif view_mode == "🌳 External Development":
    st.header("🌳 External Development Progress")

    # ------------------ Weights (TOTAL = 1.00) ------------------
    EXT_WEIGHTS = {
        "MEP Work": 0.10,
        "Civil Finishes Work": 0.50,
        "MS/MEP Fixtures": 0.25,
        "Finishes": 0.10,
        "cleaning": 0.05,
    }

    numeric_cols = list(EXT_WEIGHTS.keys())

    # ------------------ Load Data ------------------
    df_view = df_ext.copy()

    df_view["Tower"] = df_view["Tower"].astype(str).str.strip()
    df_view["Area"]  = df_view["Area"].astype(str).str.strip()

    df_view = df_view[df_view["Tower"].notna()]
    df_view = df_view[df_view["Tower"] != "nan"]

    # ------------------ Clean & Normalize % ------------------
    for col in numeric_cols:
        df_view[col] = (
            df_view[col]
            .astype(str)
            .str.replace("%", "", regex=False)
            .str.strip()
        )
        df_view[col] = pd.to_numeric(df_view[col], errors="coerce").fillna(0)

        # Excel normalization: 0–1 → 0–100
        df_view[col] = df_view[col].apply(
            lambda x: x * 100 if 0 <= x <= 1 else x*100
        )

    # ------------------ Row-wise Weighted Progress ------------------
    def compute_ext_progress(row):
        total = 0
        for col, wt in EXT_WEIGHTS.items():
            val = pd.to_numeric(row.get(col, 0), errors="coerce")
            if pd.isna(val):
                val = 0
            total += val * wt
        return round(total, 2)

    df_view["Progress %"] = df_view.apply(compute_ext_progress, axis=1)

    # ------------------ UPDATE SUMMARY ROW FROM CHILD ROWS ------------------
    def update_external_summary(df, tower):
        mask_children = (
            (df["Tower"] == tower) &
            (~df["Area"].str.startswith("External Development"))
        )

        mask_summary = (
            (df["Tower"] == tower) &
            (df["Area"].str.startswith("External Development"))
        )

        if df[mask_children].empty or df[mask_summary].empty:
            return df

        avg_progress = df.loc[mask_children, "Progress %"].mean()
        df.loc[mask_summary, "Progress %"] = round(avg_progress, 2)

        return df

    for t in ["I", "L1", "L2"]:
        df_view = update_external_summary(df_view, t)

    # ------------------ Sort (Summary First) ------------------
    df_view["SortOrder"] = df_view["Area"].apply(
        lambda x: 0 if x.startswith("External Development") else 1
    )
    df_view = df_view.sort_values(
        ["Tower", "SortOrder", "Area"]
    ).reset_index(drop=True)

    # ------------------ Tower KPIs (READ SUMMARY ONLY) ------------------
    def get_tower_progress(df, tower):
        row = df[
            (df["Tower"] == tower) &
            (df["Area"].str.startswith("External Development"))
        ]
        return row["Progress %"].iloc[0] if not row.empty else 0

    I_progress  = get_tower_progress(df_view, "I")
    L1_progress = get_tower_progress(df_view, "L1")
    L2_progress = get_tower_progress(df_view, "L2")

    # ------------------ LCRG KPI ------------------
    LCRG_progress = (
        I_progress  * 0.40 +
        L1_progress * 0.30 +
        L2_progress * 0.30
    )

    # ------------------ Metrics ------------------
    st.metric("🌎 LCRG External Development", f"{LCRG_progress:.2f}%")

    c1, c2, c3 = st.columns(3)
    c1.metric("I Tower",  f"{I_progress:.2f}%")
    c2.metric("L1 Tower", f"{L1_progress:.2f}%")
    c3.metric("L2 Tower", f"{L2_progress:.2f}%")

    # ------------------ Highlight Summary Rows ------------------
    def highlight_ext_rows(row):
        if row["Area"].startswith("External Development"):
            return ["background-color:#d9eaf7; font-weight:bold;"] * len(row)
        return [""] * len(row)

    # ------------------ Display Table ------------------
    display_cols = [
        "Tower", "Area",
        "MEP Work", "Civil Finishes Work",
        "MS/MEP Fixtures", "Finishes", "cleaning",
        "Progress %"
    ]

    color_cols = numeric_cols + ["Progress %"]

    st.dataframe(
        df_view[display_cols]
            .style
            .apply(highlight_ext_rows, axis=1)
            .map(color_progress, subset=color_cols)
            .format(
                {c: "{:.0f}%" for c in numeric_cols} |
                {"Progress %": "{:.0f}%"}
            ),
        use_container_width=True,
        hide_index=True
    )

    # =============================================================
    # 📷 EXTERNAL DEVELOPMENT PHOTOS
    # =============================================================
    st.subheader("📷 External Development Photos")

    if tower_filter == "All":
        st.info("Select a Tower (I / L1 / L2) to view or upload External Development photos.")
    else:
        photo_path = show_section_photos("External", tower_filter)

        uploaded = st.file_uploader(
            f"Upload External Development Photos – {tower_filter}",
            type=["jpg", "jpeg", "png", "zip"],
            accept_multiple_files=True,
            key=f"ext_upload_{tower_filter}"
        )

        if uploaded:
            save_section_photos("External", tower_filter, uploaded)
            st.success("External Development photos uploaded.")
            st.rerun()

    # =============================================================
    # 📄 EXTERNAL DEVELOPMENT PDF
    # =============================================================
    st.markdown("---")
    st.subheader("📄 External Development Report")

    if REPORTLAB_AVAILABLE and tower_filter != "All":
        df_pdf = df_view[df_view["Tower"] == tower_filter]
        ext_val = get_tower_progress(df_view, tower_filter)

        pdf_buffer = generate_section_pdf(
            title="External Development Progress Report – Lake City Roof Gardens",
            tower=tower_filter,
            progress_text=f"{ext_val:.2f}%",
            table_df=df_pdf,
            photo_path=photo_path
        )

        st.download_button(
            label="📄 Download External Development PDF",
            data=pdf_buffer,
            file_name=f"External_{tower_filter}_Report.pdf",
            mime="application/pdf"
        )
    else:
        st.info("Select a tower to enable External Development PDF.")

# =============================================================
# ROOFTOP PROGRESS (FINAL — FULLY FIXED FOR YOUR EXCEL FORMAT)
# =============================================================
elif view_mode == "⬆️ Rooftop":

    st.header("⬆️ Rooftop Progress")

    df_rt2 = df_rt.copy()
    df_rt2.columns = df_rt2.columns.str.strip()
    df_rt2 = df_rt2.loc[:, ~df_rt2.columns.str.contains("Unnamed", case=False)]

    activity_cols = [
        "MEP Work","Ceiling","Tile Work","Paint Work","Civil Finishes",
        "Pool Works","MEP Fixtures","MS Work","Wood works",
        "Plantation","Furniture","Cleaning"
    ]

    # ---------------- CLEAN ----------------
    def clean_val(x):
        if isinstance(x, str):
            x = x.replace("%", "").strip()
        x = pd.to_numeric(x, errors="coerce")
        return 0 if pd.isna(x) else x*100

    for c in activity_cols:
        df_rt2[c] = df_rt2[c].apply(clean_val)

    # ---------------- SPLIT WEIGHTS & ITEMS ----------------
    weight_rows = df_rt2[df_rt2["Area"].str.contains("Tower Progress", case=False)]
    item_rows   = df_rt2[df_rt2["Area"].str.contains("Roof Top", case=False)].copy()

    # ---------------- WEIGHT MAP ----------------
    weight_map = {}
    for _, r in weight_rows.iterrows():
        tower = r["Tower"]
        weight_map[tower] = {c: r[c] for c in activity_cols}

    # ---------------- CALCULATE PROGRESS ----------------
    def compute_roof(row):
        wts = weight_map.get(row["Tower"], {})
        return sum(row[c] * wts.get(c, 0) for c in activity_cols)/100

    item_rows["Progress %"] = item_rows.apply(compute_roof, axis=1)

    # ---------------- KPIs ----------------
    I_val  = item_rows[item_rows["Tower"] == "I"]["Progress %"].mean()
    L1_val = item_rows[item_rows["Tower"] == "L1"]["Progress %"].mean()
    L2_val = item_rows[item_rows["Tower"] == "L2"]["Progress %"].mean()

    LCRG_val = (I_val * 0.40) + (L1_val * 0.30) + (L2_val * 0.30)

    c0, c1, c2, c3 = st.columns(4)
    c0.metric("🌍 LCRG Rooftop", f"{LCRG_val:.2f}%")
    c1.metric("I Tower",  f"{I_val:.2f}%")
    c2.metric("L1 Tower", f"{L1_val:.2f}%")
    c3.metric("L2 Tower", f"{L2_val:.2f}%")

    # ---------------- HIGHLIGHT ----------------
    def color_progress(val):
        if val < 40:
            return "background-color:#ffcccc;"
        elif val < 70:
            return "background-color:#fff7b3;"
        return "background-color:#ccffcc;"

    # ---------------- DISPLAY ----------------
    display_cols = ["Tower", "Area"] + activity_cols + ["Progress %"]
    color_cols = activity_cols + ["Progress %"]

    st.dataframe(
        item_rows[display_cols]
            .style
            .map(color_progress, subset=color_cols)
            .format(
                {c: "{:.0f}%" for c in activity_cols}
                | {"Progress %": "{:.2f}%"}
            ),
        use_container_width=True
    )
    # =============================================================
    # 📷 ROOFTOP PHOTOS (PHASE 1 – CLEAN)
    # =============================================================
    st.subheader("📷 Rooftop Photos")

    if tower_filter == "All":
        st.info("Select a Tower (I / L1 / L2) to view or upload rooftop photos.")
    else:
        photo_path = show_section_photos("Rooftop", tower_filter)

        uploaded = st.file_uploader(
            f"Upload Rooftop Photos – {tower_filter}",
            type=["jpg", "jpeg", "png", "zip"],
            accept_multiple_files=True,
            key=f"rooftop_upload_{tower_filter}"
        )

        if uploaded:
            save_section_photos("Rooftop", tower_filter, uploaded)
            st.success("Rooftop photos uploaded.")
            st.rerun()
    # =============================================================
    # 📄 ROOFTOP PDF DOWNLOAD (STEP 3 – FIXED)
    # =============================================================
    st.markdown("---")
    st.subheader("📄 Rooftop Report")

    if REPORTLAB_AVAILABLE and tower_filter != "All":

        pdf_buffer = generate_section_pdf(
            title="Rooftop Progress Report – Lake City Roof Gardens",
            tower=tower_filter,
            progress_text=f"{I_val:.2f}%",
            table_df=item_rows[display_cols],   # ✅ FIX HERE
            photo_path=photo_path
        )

        st.download_button(
            label="📄 Download Rooftop PDF",
            data=pdf_buffer,
            file_name=f"Rooftop_{tower_filter}_Report.pdf",
            mime="application/pdf"
        )

    else:
        st.info("Select a tower to enable Rooftop PDF download.")




# =============================================================
#  GROUND FLOOR (FINAL – EXCEL-ALIGNED & STABLE)
# =============================================================
elif view_mode == "🧱 Ground Floor":

    st.header("🧱 Ground Floor")

    # ---------- Load ----------
    df_raw = df_gf.copy()
    df_raw.columns = df_raw.columns.str.strip()
    df_raw = df_raw.loc[:, ~df_raw.columns.str.contains("Unnamed", case=False)]

    df_raw["Tower"] = df_raw["Tower"].astype(str).str.strip()
    df_raw["Area"]  = df_raw["Area"].astype(str).str.strip()

    # ---------- Activity columns ----------
    GF_ACTIVITIES = [
        "MEP Work", "Ceiling", "Tile Work", "Paint Work",
        "Aluminum Work", "Wood Work", "MEP Fixtures", "MS Work",
        "External Plaster", "External Paint", "Cleaning"
    ]

    # =====================================================
    # 1️⃣ Read WEIGHTS (FIRST ROW ONLY)
    # =====================================================
    weight_row = df_raw.iloc[0]

    GF_WEIGHTS = {}
    for col in GF_ACTIVITIES:
        w = str(weight_row[col]).replace("%", "").strip()
        w = pd.to_numeric(w, errors="coerce")
        GF_WEIGHTS[col] = 0 if pd.isna(w) else w 

    # =====================================================
    # 2️⃣ Remove weight row
    # =====================================================
    df = df_raw.iloc[1:].copy()

    # =====================================================
    # 3️⃣ Remove tower header rows (CRITICAL FIX)
    # =====================================================
    df = df[~df["Area"].str.lower().isin(["i tower", "l1 tower", "l2 tower"])]

    # =====================================================
    # 4️⃣ Clean activity values (0–100 scale only)
    # =====================================================
    def clean_val(x):
        if isinstance(x, str):
            x = x.replace("%", "").strip()
        x = pd.to_numeric(x, errors="coerce")
        return 0 if pd.isna(x) else x*100

    for col in GF_ACTIVITIES:
        df[col] = df[col].apply(clean_val)

    # =====================================================
    # 5️⃣ Weighted progress (EXACT Excel logic)
    # =====================================================
    def compute_progress(row):
        return sum(row[col] * GF_WEIGHTS[col] for col in GF_ACTIVITIES)

    df["Progress %"] = df.apply(compute_progress, axis=1)

    # =====================================================
    # 6️⃣ KPIs
    # =====================================================
    df_I  = df[df["Tower"] == "I"]
    df_L1 = df[df["Tower"] == "L1"]
    df_L2 = df[df["Tower"] == "L2"]

    I_progress  = df_I["Progress %"].mean()  if not df_I.empty  else 0
    L1_progress = df_L1["Progress %"].mean() if not df_L1.empty else 0
    L2_progress = df_L2["Progress %"].mean() if not df_L2.empty else 0

    LCRG_progress = (I_progress * 0.40) + (L1_progress * 0.30) + (L2_progress * 0.30)

    st.metric("🌍 LCRG Ground Floor", f"{LCRG_progress:.2f}%")

    c1, c2, c3 = st.columns(3)
    c1.metric("I Tower",  f"{I_progress:.2f}%")
    c2.metric("L1 Tower", f"{L1_progress:.2f}%")
    c3.metric("L2 Tower", f"{L2_progress:.2f}%")

    # =====================================================
    # 7️⃣ Highlight Ground Floor summary rows (visual only)
    # =====================================================
    def highlight_gf(row):
        if row["Area"].lower().startswith("ground floor"):
            return ["background-color:#fff7b3; font-weight:600;"] * len(row)
        return [""] * len(row)

    # =====================================================
    # 8️⃣ Display (GF ONLY – WITH COLOR FORMAT)
    # =====================================================
    display_cols = ["Tower", "Area"] + GF_ACTIVITIES + ["Progress %"]

    df_view = df if tower_filter == "All" else df[df["Tower"] == tower_filter]
    color_cols = GF_ACTIVITIES + ["Progress %"]

    st.dataframe(
        df_view[display_cols]
            .style
            .map(color_progress, subset=color_cols)
            .format(
                {col: "{:.0f}%" for col in GF_ACTIVITIES} |
                {"Progress %": "{:.0f}%"}
            ),
        use_container_width=True,
        hide_index=True,
        column_config={
            col: st.column_config.Column(width="small")
            for col in display_cols
        }
    )


    # =============================================================
    # 📷 GROUND FLOOR PHOTOS
    # =============================================================
    st.subheader("📷 Ground Floor Photos")

    if tower_filter == "All":
        st.info("Select a Tower (I / L1 / L2) to view or upload Ground Floor photos.")
    else:
        photo_path = show_section_photos("GroundFloor", tower_filter)

        uploaded = st.file_uploader(
            f"Upload Ground Floor Photos – {tower_filter}",
            type=["jpg", "jpeg", "png", "zip"],
            accept_multiple_files=True,
            key=f"gf_upload_{tower_filter}"
        )

        if uploaded:
            save_section_photos("GroundFloor", tower_filter, uploaded)
            st.success("Ground Floor photos uploaded.")
            st.rerun()
    # =============================================================
    # 📄 GROUND FLOOR PDF (LANDSCAPE TABULAR) — FIXED
    # =============================================================
    st.markdown("---")
    st.subheader("📄 Ground Floor Report")

    if REPORTLAB_AVAILABLE and tower_filter != "All":

        # USE THE SAME DATAFRAME ALREADY SHOWN IN THE TABLE
        df_pdf = df[df["Tower"] == tower_filter]

        gf_val = df_pdf["Progress %"].mean() if not df_pdf.empty else 0

        pdf_buffer = generate_section_pdf(
            title="Ground Floor Progress Report – Lake City Roof Gardens",
            tower=tower_filter,
            progress_text=f"{gf_val:.2f}%",
            table_df=df_pdf,
            photo_path=photo_path
        )

        st.download_button(
            label="📄 Download Ground Floor PDF",
            data=pdf_buffer,
            file_name=f"GroundFloor_{tower_filter}_Report.pdf",
            mime="application/pdf"
        )

    else:
        st.info("Select a tower to enable Ground Floor PDF.")

# =============================================================
#  7) COMMON AREA DEVELOPMENT
# =============================================================
elif view_mode == "🏛 Common Area":

    st.header("🏛 Common Area")

    df_view = df_ca.copy()
    df_view.columns = df_view.columns.str.strip()
    df_view = df_view.loc[:, ~df_view.columns.str.contains("Unnamed", case=False)]

    # ------------------ Clean base columns ------------------
    df_view["Tower"] = df_view["Tower"].astype(str).str.strip()
    df_view["Area"]  = df_view["Area"].astype(str).str.strip()

    df_view = df_view[
        (df_view["Tower"].str.lower() != "nan") &
        (df_view["Area"].str.lower() != "none")
    ]

    # ------------------ Common Area Columns ------------------
    ca_cols = ["Civil Works", "MEP", "Finishes", "Cleaning"]

    # ------------------ WEIGHTS ------------------
    # Normal Common Area
    CA_WEIGHTS_COMMON = {
        "Civil Works": 0.20,
        "MEP": 0.55,
        "Finishes": 0.20,
        "Cleaning": 0.05
    }

    # Civil-dominant rows
    CA_WEIGHTS_CIVIL = {
        "Civil Works": 0.65,
        "MEP": 0.20,
        "Finishes": 0.12,
        "Cleaning": 0.03
    }

    # MEP-dominant rows
    CA_WEIGHTS_MEP = {
        "Civil Works": 0.20,
        "MEP": 0.65,
        "Finishes": 0.12,
        "Cleaning": 0.03
    }

    # ------------------ Clean numeric values ------------------
    def clean_val(x):
        if isinstance(x, str):
            x = x.replace("%", "").strip()
        x = pd.to_numeric(x, errors="coerce")
        return 0 if pd.isna(x) else x*100

    for c in ca_cols:
        df_view[c] = df_view[c].apply(clean_val)

    # ------------------ DISCIPLINE-AWARE PROGRESS ------------------
    def compute_ca_progress(row):
        area = str(row["Area"]).lower()

        if area.startswith("civil work"):
            weights = CA_WEIGHTS_CIVIL

        elif area.startswith("mep work"):
            weights = CA_WEIGHTS_MEP

        else:
            weights = CA_WEIGHTS_COMMON

        total = 0
        for col, wt in weights.items():
            total += row.get(col, 0) * wt   # values already in %

        return total

    df_view["Progress %"] = df_view.apply(compute_ca_progress, axis=1)

    # ------------------ Tower summaries (ITEM ROWS ONLY) ------------------
    def is_item_row(area):
        return "tower progress" not in str(area).lower()

    df_items = df_view[df_view["Area"].apply(is_item_row)]

    df_I  = df_items[df_items["Tower"] == "I"]
    df_L1 = df_items[df_items["Tower"] == "L1"]
    df_L2 = df_items[df_items["Tower"] == "L2"]

    I_progress  = df_I["Progress %"].mean()  if not df_I.empty  else 0
    L1_progress = df_L1["Progress %"].mean() if not df_L1.empty else 0
    L2_progress = df_L2["Progress %"].mean() if not df_L2.empty else 0

    LCRG_progress = (I_progress * 0.40) + (L1_progress * 0.30) + (L2_progress * 0.30)

    # ------------------ KPIs ------------------
    st.metric("🌍 LCRG Common Area", f"{LCRG_progress:.2f}%")

    c1, c2, c3 = st.columns(3)
    c1.metric("I Tower",  f"{I_progress:.2f}%")
    c2.metric("L1 Tower", f"{L1_progress:.2f}%")
    c3.metric("L2 Tower", f"{L2_progress:.2f}%")

    # ------------------ Coloring ------------------
    def color_progress(val):
        try:
            val = float(val)
        except:
            return ""
        if val < 40:
            return "background-color:#ffcccc;"
        elif val < 70:
            return "background-color:#fff7b3;"
        return "background-color:#ccffcc;"

    # ------------------ DISPLAY ------------------
    display_cols = ["Tower", "Area"] + ca_cols + ["Progress %"]

    color_cols = ca_cols + ["Progress %"]

    st.dataframe(
        df_view[display_cols]
            .style
            .map(color_progress, subset=color_cols)
            .format(
                {c: "{:.0f}%" for c in ca_cols}
                | {"Progress %": "{:.0f}%"}
            ),
        use_container_width=True,
        hide_index=True
    )

    # =============================================================
    # 📷 COMMON AREA PHOTOS
    # =============================================================
    st.subheader("📷 Common Area Photos")

    if tower_filter == "All":
        st.info("Select a Tower (I / L1 / L2) to view or upload Common Area photos.")
    else:
        photo_path = show_section_photos("CommonArea", tower_filter)

        uploaded = st.file_uploader(
            f"Upload Common Area Photos – {tower_filter}",
            type=["jpg", "jpeg", "png", "zip"],
            accept_multiple_files=True,
            key=f"ca_upload_{tower_filter}"
        )

        if uploaded:
            save_section_photos("CommonArea", tower_filter, uploaded)
            st.success("Common Area photos uploaded.")
            st.rerun()
    # =============================================================
    # 📄 COMMON AREA PDF (LANDSCAPE TABULAR) — FIXED
    # =============================================================
    st.markdown("---")
    st.subheader("📄 Common Area Report")

    if REPORTLAB_AVAILABLE and tower_filter != "All":

        # USE THE SAME DATAFRAME THAT IS SHOWN IN THE COMMON AREA TABLE
        df_pdf = df_items[df_items["Tower"] == tower_filter]

        ca_val = df_pdf["Progress %"].mean() if not df_pdf.empty else 0

        pdf_buffer = generate_section_pdf(
            title="Common Area Progress Report – Lake City Roof Gardens",
            tower=tower_filter,
            progress_text=f"{ca_val:.2f}%",
            table_df=df_pdf,
            photo_path=photo_path
        )

        st.download_button(
            label="📄 Download Common Area PDF",
            data=pdf_buffer,
            file_name=f"CommonArea_{tower_filter}_Report.pdf",
            mime="application/pdf"
        )

    else:
        st.info("Select a tower to enable Common Area PDF.")

# =============================================================
#  8) GLOBAL PHOTO VIEWER (Tower / Apartment Wise)
# =============================================================
elif view_mode == "📷 Photo Viewer":
    st.header("📷 Photo Viewer")

    st.write("Browse photos tower-wise or apartment-wise. This does not affect other tabs.")

    # ------------------------- Select Tower -------------------------
    tower_choice = st.selectbox("Select Tower", ["All"] + tower_list, key="ph_tower")

    # ------------------------- Select Apartment (optional) ---------
    apt_options = ["All"]
    if tower_choice != "All":
        apt_options += sorted(
            df_apt[df_apt["Tower"] == tower_choice]["Apartment No"].unique()
        )

    apt_choice = st.selectbox("Select Apartment", apt_options, key="ph_apt")

    # ------------------------- Load Photos -------------------------
    if apt_choice != "All" and tower_choice != "All":
        # ----- Show photos for specific apartment -----
        st.subheader(f"Apartment {apt_choice} – {tower_choice}")

        key, apt_dir, files = get_apartment_photos(tower_choice, apt_choice)

        if not files:
            st.info("No photos available for this apartment.")
        else:
            col1, col2 = st.columns(2)
            for i, path in enumerate(files):
                try:
                    img = Image.open(path)
                    if img.width > img.height:
                        img = img.rotate(90, expand=True)
                    img = img.resize((450, 650))
                except:
                    continue

                (col1 if i % 2 == 0 else col2).image(
                    img, caption=os.path.basename(path)
                )

    else:
        # ----- Show tower-wise photo folders -----
        st.subheader("Tower-wise Photo Folders")

        # List all folders inside uploaded_photos
        all_dirs = sorted(
            [d for d in os.listdir(PHOTO_DIR) if os.path.isdir(os.path.join(PHOTO_DIR, d))]
        )

        if tower_choice != "All":
            all_dirs = [d for d in all_dirs if d.startswith(tower_choice)]

        if not all_dirs:
            st.info("No photo folders found.")
        else:
            for folder in all_dirs:
                st.markdown(f"### 📁 {folder}")

                files = [
                    os.path.join(PHOTO_DIR, folder, f)
                    for f in os.listdir(os.path.join(PHOTO_DIR, folder))
                    if f.lower().endswith((".jpg", ".jpeg", ".png"))
                ]

                if not files:
                    st.caption("No images found.")
                    continue

                col1, col2 = st.columns(2)
                for i, path in enumerate(files):
                    try:
                        img = Image.open(path)
                        if img.width > img.height:
                            img = img.rotate(90, expand=True)
                        img = img.resize((450, 650))
                    except:
                        continue

                    (col1 if i % 2 == 0 else col2).image(
                        img, caption=os.path.basename(path)
                    )
