# resume.py
import sys
import pandas as pd
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

# Layout constants
LEFT_MARGIN = 50
TOP_MARGIN = 50
LINE_HEIGHT = 14
PAGE_WIDTH, PAGE_HEIGHT = LETTER

# Font settings
HEADER_FONT = ("Helvetica-Bold", 12)
SUBHEADER_FONT = ("Helvetica-Bold", 10)
NORMAL_FONT = ("Helvetica", 8)
ITALIC_FONT = ("Helvetica-Oblique", 8)

def check_page_break(c, y_position):
    """
    If the y_position is too low, start a new page and reset the position.
    """
    if y_position < LINE_HEIGHT * 2:
        c.showPage()
        c.setFont(*NORMAL_FONT)
        return PAGE_HEIGHT - TOP_MARGIN
    return y_position

def draw_text_with_bold(c, text, x, y, width):
    """
    Draw text with inline bold markers **like this**.
    We'll split on '**' and toggle between normal/bold fonts.
    """
    lines = simpleSplit(text, NORMAL_FONT[0], NORMAL_FONT[1], width - LEFT_MARGIN * 2)
    for line in lines:
        x_pos = LEFT_MARGIN
        segments = line.split('**')
        bold = False
        for segment in segments:
            font = ("Helvetica-Bold", NORMAL_FONT[1]) if bold else NORMAL_FONT
            c.setFont(*font)
            c.drawString(x_pos, y, segment)
            seg_width = c.stringWidth(segment, font[0], font[1])
            x_pos += seg_width
            bold = not bold
        y -= LINE_HEIGHT
        y = check_page_break(c, y)
    return y

def create_ats_resume_pdf(csv_path, output_path):
    """
    Reads a CSV with columns: section, subsection, content
    Generates an ATS-friendly PDF resume following the specified section order.
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Section order
    section_order = [
        "personal_info",
        "professional_summary",
        "technical_skills",
        "professional_experience",
        "certifications",
        "projects"
    ]

    # Grab personal info
    try:
        name = df.loc[
            (df["section"] == "personal_info") & (df["subsection"] == "name"),
            "content"
        ].values[0]
        target_roles = df.loc[
            (df["section"] == "personal_info") & (df["subsection"] == "target_roles"),
            "content"
        ].values[0]
    except IndexError:
        print("Error: Required fields (name, target_roles) not found in personal_info section.")
        return

    personal_info = df[
        (df["section"] == "personal_info") &
        (~df["subsection"].isin(["name", "target_roles"]))
    ]
    personal_info_string = " | ".join(personal_info["content"].tolist())

    # Optional portfolio link
    portfolio = df.loc[
        (df["section"] == "personal_info") & (df["subsection"] == "portfolio"),
        "content"
    ].values
    portfolio_link = portfolio[0] if len(portfolio) > 0 else None

    # Setup canvas
    c = canvas.Canvas(output_path, pagesize=LETTER)
    y = PAGE_HEIGHT - TOP_MARGIN

    # Print Name
    c.setFont(*HEADER_FONT)
    c.drawString(LEFT_MARGIN, y, name)
    y -= LINE_HEIGHT
    y = check_page_break(c, y)

    # Print personal info
    c.setFont(*NORMAL_FONT)
    c.drawString(LEFT_MARGIN, y, personal_info_string)
    y -= LINE_HEIGHT
    y = check_page_break(c, y)

    # Print target roles
    c.setFont(*ITALIC_FONT)
    c.drawString(LEFT_MARGIN, y, target_roles)
    y -= int(LINE_HEIGHT * 1.25)
    y = check_page_break(c, y)

    # Process the rest
    for section in section_order:
        if section == "personal_info":
            continue

        group = df[df["section"] == section]
        if group.empty:
            continue

        # Section title
        c.setFont(*SUBHEADER_FONT)
        title = section.replace("_", " ").title()
        c.drawString(LEFT_MARGIN, y, title)
        y -= 8
        c.line(LEFT_MARGIN, y, PAGE_WIDTH - LEFT_MARGIN, y)
        y -= int(LINE_HEIGHT * 1.1)
        y = check_page_break(c, y)

        # Each row's text
        c.setFont(*NORMAL_FONT)
        for _, row in group.iterrows():
            text = row["content"]
            y = draw_text_with_bold(c, text, LEFT_MARGIN, y, PAGE_WIDTH)
            y -= 3
            y = check_page_break(c, y)
        y -= 8
        y = check_page_break(c, y)

    # If there's a portfolio link, put it at bottom
    if portfolio_link:
        y = LINE_HEIGHT * 2
        c.setFont(*ITALIC_FONT)
        c.drawString(LEFT_MARGIN, y, f"Portfolio: {portfolio_link}")

    c.save()
    print(f"ATS resume saved to {output_path}")

if __name__ == "__main__":
    # We expect: python resume.py <csv_file> <pdf_output>
    if len(sys.argv) < 3:
        print("Usage: python resume.py <csv_file> <pdf_output>")
        sys.exit(1)

    csv_file = sys.argv[1]
    pdf_file = sys.argv[2]

    create_ats_resume_pdf(csv_file, pdf_file)
