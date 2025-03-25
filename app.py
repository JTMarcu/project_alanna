# app.py
import os
import sys
import openai
import pandas as pd
import subprocess
from dotenv import load_dotenv
import tkinter as tk
from tkinter import messagebox

def get_job_description_from_dialog() -> str:
    """
    Opens a Tkinter window with a large text box for the user
    to paste or type the job description. Returns the result.
    """
    job_desc_container = []

    def on_ok():
        desc = text_box.get("1.0", "end-1c").strip()
        job_desc_container.append(desc)
        root.destroy()

    def on_cancel():
        root.destroy()

    root = tk.Tk()
    root.title("Job Description")

    label = tk.Label(root, text="Paste or type the job description below:")
    label.pack(padx=10, pady=5)

    text_box = tk.Text(root, wrap="word", width=80, height=20)
    text_box.pack(padx=10, pady=5)

    button_frame = tk.Frame(root)
    button_frame.pack(padx=10, pady=5)

    ok_button = tk.Button(button_frame, text="OK", command=on_ok)
    ok_button.pack(side="left", padx=5)

    cancel_button = tk.Button(button_frame, text="Cancel", command=on_cancel)
    cancel_button.pack(side="left", padx=5)

    root.mainloop()

    return job_desc_container[0] if job_desc_container else ""

def call_llm_to_shorten_resume(job_desc: str, full_resume_data: str) -> str:
    """
    Calls OpenAI ChatCompletion to produce a single-page (~400–500 words) CSV resume
    and a concise cover letter (<=200 words).

    Key requirements now include:
      - Keep professional_summary mostly intact.
      - Always keep personal_info, including 'portfolio'.
      - Must keep the 'certifications' section with its content.
      - 3 professional_experience (2 bullets each, 2 sentences).
      - 3-4 relevant projects (1 bullet, 2 sentences).
    """

    prompt = f"""
You are a specialized AI that creates a thorough, ATS-friendly resume for a job applicant.

=== CRITICAL REQUIREMENTS ===

1) The final resume should be ~400–500 words (a single printed page), plus a cover letter up to 200 words.
2) personal_info:
   - Must include (subsection=name, target_roles, location, phone, email, etc.) 
   - Do NOT remove 'personal_info,portfolio,JTMarcu.GitHub.io'.
3) professional_summary:
   - Use the existing summary from the CSV with minimal changes. 
   - You may lightly adapt it to match the job, but do NOT remove or heavily paraphrase it.
4) certifications:
   - Must be included in the final CSV. 
   - Do not omit or rename the 'certifications' section. Keep its full content.
5) professional_experience:
   - Exactly 3 subsections: data_bi_consultant, data_freelance, retail_costco.
   - Each has 1 bold heading + EXACT 2 bullet points (each bullet = 2 sentences).
6) projects:
   - Keep 3-4 relevant ones, each with 1 bold heading + 1 bullet of 2 sentences.
   - Skip less relevant projects if needed.
7) Summaries for other sections (technical_skills, etc.) are allowed but do not remove them fully.
8) End with a cover letter (<=200 words) starting with "Dear ".

=== CSV FORMAT ===
section,subsection,content

Example row:
professional_experience,data_freelance,"**Data & Full-Stack Developer**\\n- First bullet (2 sentences). Another sentence.\\n- Second bullet (2 sentences). Another sentence."

=== JOB DESCRIPTION ===
{job_desc}

=== FULL RESUME DATA (CSV) ===
{full_resume_data}

YOUR TASK:
- Generate a valid CSV with (section,subsection,content).
- Keep personal_info (including portfolio).
- Keep professional_summary mostly intact.
- Always include certifications section exactly as in the CSV or lightly adjusted if you need to add relevant phrasing. But do not remove any lines.
- 3 pro experiences (2 bullets each, 2 sentences).
- 3-4 relevant projects (1 bullet, 2 sentences).
- Then a cover letter up to 200 words, starting with "Dear ".
- ~400–500 words total for the resume text.
    """

    import openai
    from tkinter import messagebox

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful resume-optimizing assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=3000
        )
        return response.choices[0].message.content

    except Exception as e:
        messagebox.showerror("OpenAI Error", f"OpenAI API call failed: {e}")
        return ""


def parse_response_for_csv_and_letter(full_text: str):
    """
    Splits the LLM's combined output into:
      - CSV portion (section,subsection,content lines)
      - Cover letter portion (beginning with "Dear ")
    """
    csv_marker = "section,subsection,content"
    letter_marker = "Dear "

    csv_part = ""
    letter_part = ""

    if csv_marker in full_text:
        start_idx = full_text.index(csv_marker)
        csv_part = full_text[start_idx:]
        if letter_marker in csv_part:
            letter_idx = csv_part.index(letter_marker)
            letter_part = csv_part[letter_idx:].strip()
            csv_part = csv_part[:letter_idx].strip()
        else:
            letter_part = "Could not parse letter. 'Dear ' not found in output."
    else:
        csv_part = "Could not parse CSV. 'section,subsection,content' not found."
        letter_part = full_text

    return csv_part, letter_part

def main():
    load_dotenv()

    openai.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("HUGGING_CHAT_API_KEY")
    if not openai.api_key:
        tk.messagebox.showerror("Error", "No OpenAI API key found in environment.")
        sys.exit(1)

    # We'll assume your master CSV is named resume_data_master.csv
    csv_file = "resume_data_master.csv"
    if not os.path.isfile(csv_file):
        tk.messagebox.showerror("Error", f"{csv_file} not found in directory.")
        sys.exit(1)

    df_master = pd.read_csv(csv_file)
    if df_master.empty:
        tk.messagebox.showerror("Error", "The master CSV is empty.")
        sys.exit(1)

    # Get job description from a Tkinter dialog
    job_description = get_job_description_from_dialog()
    if not job_description:
        tk.messagebox.showinfo("Info", "No job description entered. Exiting.")
        sys.exit(0)

    # Convert entire master CSV to text
    master_csv_text = df_master.to_csv(index=False)

    # 1) Call the LLM
    raw_output = call_llm_to_shorten_resume(job_description, master_csv_text)

    # 2) Parse out CSV & letter
    short_csv, cover_letter = parse_response_for_csv_and_letter(raw_output)

    # -- Fallback injection for personal_info if the AI omits them --
    essential_personal_info = {
        "name": "Jonathan Marcu",
        "target_roles": "Applied Scientist | Machine Learning Engineer | Data Scientist | Data Analyst | BI Consultant",
        "location": "San Diego, CA",
        "phone": "(619) 483-5543",
        "email": "JonMarcu@live.com",
        "linkedin": "linkedin.com/in/jon-marcu",
        "github": "github.com/JTMarcu"
        # add or remove as desired
    }

    # Ensure 'personal_info,name,' is present, etc.
    for key, val in essential_personal_info.items():
        snippet = f"personal_info,{key},"
        if snippet not in short_csv:
            short_csv += f'\npersonal_info,{key},"{val}"'

    # 3) Save them
    tailored_csv_path = "tailored_resume.csv"
    cover_letter_path = "cover_letter.txt"
    pdf_path = "tailored_resume.pdf"

    with open(tailored_csv_path, "w", encoding="utf-8") as f:
        f.write(short_csv)

    with open(cover_letter_path, "w", encoding="utf-8") as f:
        f.write(cover_letter)

    # 4) Call resume.py to make PDF
    try:
        subprocess.run(["python", "resume.py", tailored_csv_path, pdf_path], check=True)
        msg = (
            f"Successfully generated:\n\n"
            f" - {pdf_path}\n"
            f" - {cover_letter_path}\n\n"
            f"Raw LLM output:\n\n"
            f"{raw_output}"
        )
        tk.messagebox.showinfo("Success", msg)

    except subprocess.CalledProcessError as e:
        tk.messagebox.showerror("Error Generating PDF", f"resume.py failed: {e}")

if __name__ == "__main__":
    main()
