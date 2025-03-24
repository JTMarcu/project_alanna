import pandas as pd
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from tkinter import Tk, filedialog

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
    """Check if the y_position is too low; if so, add a new page and reset y_position."""
    if y_position < LINE_HEIGHT * 2:
        c.showPage()
        c.setFont(*NORMAL_FONT)
        return PAGE_HEIGHT - TOP_MARGIN
    return y_position

def draw_text_with_bold(c, text, x, y, width):
    """
    Draw text with a simple parser for bold markers '**'. Splits the text and toggles
    the font between NORMAL_FONT and bold. Uses simpleSplit to wrap text.
    """
    # Wrap the text into lines that fit the page width
    lines = simpleSplit(text, NORMAL_FONT[0], NORMAL_FONT[1], width - LEFT_MARGIN*2)
    for line in lines:
        # Draw each line with inline bold formatting
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
    Create an ATS-friendly resume PDF from a CSV file.
    
    CSV should contain three columns: section, subsection, content.
    The sections are processed in a specified order.
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Define the order for sections to appear
    section_order = [
        "personal_info",
        "professional_summary",
        "technical_skills",
        "professional_experience",
        "certifications",
        "projects"
    ]

    # Extract key personal info elements
    try:
        name = df.loc[(df["section"] == "personal_info") & (df["subsection"] == "name"), "content"].values[0]
        target_roles = df.loc[(df["section"] == "personal_info") & (df["subsection"] == "target_roles"), "content"].values[0]
    except IndexError:
        print("Required personal_info fields (name/target_roles) are missing in the CSV.")
        return

    # Concatenate the remaining personal info fields
    personal_info = df[(df["section"] == "personal_info") & 
                       (~df["subsection"].isin(["name", "target_roles"]))]
    personal_info_string = " | ".join(personal_info["content"].tolist())

    # Extract portfolio link
    portfolio = df.loc[(df["section"] == "personal_info") & (df["subsection"] == "portfolio"), "content"].values
    portfolio_link = portfolio[0] if len(portfolio) > 0 else None

    # Set up canvas
    c = canvas.Canvas(output_path, pagesize=LETTER)
    y = PAGE_HEIGHT - TOP_MARGIN

    # Header: Name
    c.setFont(*HEADER_FONT)
    c.drawString(LEFT_MARGIN, y, name)
    y -= LINE_HEIGHT
    y = check_page_break(c, y)

    # Personal info details
    c.setFont(*NORMAL_FONT)
    c.drawString(LEFT_MARGIN, y, personal_info_string)
    y -= LINE_HEIGHT
    y = check_page_break(c, y)

    # Target roles (italic)
    c.setFont(*ITALIC_FONT)
    c.drawString(LEFT_MARGIN, y, target_roles)
    y -= int(LINE_HEIGHT * 1.25)
    y = check_page_break(c, y)

    # Process remaining sections
    for section in section_order:
        if section == "personal_info":
            continue  # Already processed
        
        group = df[df["section"] == section]
        if group.empty:
            continue

        # Section title
        c.setFont(*SUBHEADER_FONT)
        section_title = section.replace("_", " ").title()
        c.drawString(LEFT_MARGIN, y, section_title)
        y -= 8
        c.line(LEFT_MARGIN, y, PAGE_WIDTH - LEFT_MARGIN, y)
        y -= int(LINE_HEIGHT * 1.1)
        y = check_page_break(c, y)

        # Process each entry in the section
        c.setFont(*NORMAL_FONT)
        for _, row in group.iterrows():
            text = row["content"]
            y = draw_text_with_bold(c, text, LEFT_MARGIN, y, PAGE_WIDTH)
            y -= 3
            y = check_page_break(c, y)
        y -= 8
        y = check_page_break(c, y)

    # Add portfolio link at the bottom
    if portfolio_link:
        y = LINE_HEIGHT * 2  # Position near the bottom of the page
        c.setFont(*ITALIC_FONT)
        c.drawString(LEFT_MARGIN, y, f"Portfolio: {portfolio_link}")

    c.save()
    print(f"ATS resume saved to {output_path}")

if __name__ == "__main__":
    # Use tkinter to prompt for file paths
    root = Tk()
    root.withdraw()  # Hide the root window

    # Prompt for the CSV file
    csv_file = filedialog.askopenfilename(
        title="Select the CSV file",
        filetypes=[("CSV Files", "*.csv")]
    )
    if not csv_file:
        print("No CSV file selected. Exiting.")
        exit()

    # Prompt for the output PDF file
    output_file = filedialog.asksaveasfilename(
        title="Save the PDF as",
        defaultextension=".pdf",
        filetypes=[("PDF Files", "*.pdf")]
    )
    if not output_file:
        print("No output file selected. Exiting.")
        exit()

    # Generate the PDF
    create_ats_resume_pdf(csv_file, output_file)